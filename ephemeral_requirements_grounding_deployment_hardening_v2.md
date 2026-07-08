# EphemerAl Requirements v2: Grounding Correctness and Deployment Hardening

## Purpose

This document is intended to be used in a fresh coding context together with the current EphemerAl repository. It turns prior technical review findings into implementable requirements with enough detail that a capable coding model can make the changes without relying on prior chat history.

EphemerAl is a local/privacy-oriented Streamlit app for document Q&A against a local Ollama backend and Apache Tika parser. The goal of these changes is **not** to add product scope. The goal is to make the existing product more truthful, safer, and easier to operate by fixing cases where:

- the UI implies a file was available to the assistant when the model did not receive its content;
- New Chat does not clear all conversation-scoped content caches despite the README privacy claim;
- app-side context budgeting can drift from the actual Ollama `num_ctx` runtime configuration;
- large/OCR document parsing is defeated by an overly short timeout;
- the app's local time can be wrong inside Docker;
- dead/supply-chain dependencies remain for no useful behavior;
- deployment docs and privacy/logging behavior are internally inconsistent.

Use the current repo as source of truth. Validate every current file before editing. If the repo has changed and a requirement below no longer matches the code, report that before modifying anything.

---

## What changed in v2

This v2 document incorporates review feedback on the prior requirements file:

1. Optional PR F now specifies Tika's behavior-preserving `/rmeta/text` JSON endpoint instead of `/tika` text extraction.
2. Oversized-file validation now acknowledges that the normal Streamlit UI rejects files over the configured upload limit before app code sees them.
3. Non-vision image requirements now cover both upload-time notes and the historical-message/model-flip path in the API payload conversion loop.
4. PR A now warns implementers not to broadly reorder the submit handler just to fix a transient first-render inconsistency.
5. PR E now includes the exact Docker command sequence needed when temporarily changing logging drivers, and explains that `docker compose restart` is insufficient.
6. PR A now explicitly ties New Chat cache clearing to the README privacy claim and forbids unavailable-attachment notes from using `--- filename ---` block markers that export parsing treats as document context.

---

## Global constraints

Follow these constraints for all PRs:

1. **Do not expand product scope.** No accounts, databases, cloud calls, persistent history, auth system, RAG index, or new model features.
2. **Preserve local/offline privacy posture.** Do not add app-level logging of prompts, uploads, extracted document text, model outputs, or chat history.
3. **Preserve Streamlit 1.56 behavior.** Do not refactor the UI broadly. Do not touch `theme.css`, clipboard iframe logic, Streamlit compatibility checks, or CSS unless specifically required by a listed acceptance criterion.
4. **Keep changes small and separately reviewable.** Prefer the PR sequence below. Do not bundle all changes into one large PR unless explicitly instructed.
5. **Treat `AGENTS.md` as important but not infallible.** Update it when a dependency or deployment invariant changes.
6. **Do not remove fallback/compatibility code unless this document explicitly says to.**
7. **Do not modify the system prompt in this work.** The changes below are app/deployment behavior changes, not prompt redesign.
8. **Do not blindly auto-fix with Ruff.** Use `ruff check .` as validation; review any lint-driven changes manually.
9. **Do not convert optional PRs into required work.** PR F is deliberately optional and should not be implemented unless explicitly requested.

---

## Recommended PR sequence

Implement in this order:

1. **PR A: Attachment grounding correctness and New Chat cache reset** — highest product-safety value.
2. **PR B: Context-source cleanup and retargeting docs** — removes the `LLM_CONTEXT_TOKENS` compose foot-gun.
3. **PR C: Tika timeout and timezone deployment hardening** — one config default plus one compose/docs fix.
4. **PR D: Remove dead mobile device detection dependency** — supply-chain simplification.
5. **PR E: Logging/troubleshooting consistency** — resolve docs/config contradiction without weakening privacy defaults unless the owner explicitly chooses that.
6. **Optional PR F: Replace `tika` PyPI client with behavior-preserving direct HTTP** — useful simplification, but more behavior-touching than PRs A-D.

---

# PR A — Attachment grounding correctness and New Chat cache reset

## Problem

Current behavior can show a user that an attachment was uploaded while the model receives either only a filename marker or a generic `DEFAULT_UPLOAD_PROMPT` such as `Please analyze the uploaded files.` The user sees transient `st.info`/`st.error` notices, but those notices are not part of the model-facing content and disappear on rerun.

This creates the worst failure mode for a document-Q&A app: the assistant may answer as if it read a document that was not actually supplied to the model.

Current repo areas to inspect before editing:

- `ephemeral_app.py`
  - upload handling around `prompt_in`, `user_text`, `files`, `parts`, `doc_entries`, `tika_ok`, `parse_with_tika`, `skipped_docs`, image support, and API payload conversion;
  - `reset_chat_session()`;
  - `render_content()`, which hides text parts marked `_synthetic`.
- `ephemeral/export.py`
  - `_extract_export_info()` treats `_synthetic` text specially and parses synthetic document context only when it sees document block markers such as `--- filename ---`.
- `tests/test_export.py`
- `tests/test_ui_static_contracts.py`

## Functional requirements

### A1. Add model-facing hidden synthetic notes for unavailable attachments

Whenever an uploaded file produces no usable content for the model, the stored user message must contain a hidden synthetic text part explaining that the attachment is unavailable and instructing the model not to guess.

The synthetic part must have at least:

```python
{
    "type": "text",
    "_synthetic": True,
    "text": "...",
}
```

Prefer adding metadata so duplicate notes can be detected later:

```python
{
    "type": "text",
    "_synthetic": True,
    "_attachment_unavailable": {
        "name": filename,
        "kind": "document",  # or "image"
        "reason_code": "tika_unavailable",
    },
    "text": "...",
}
```

Suggested helper shape:

```python
def make_attachment_unavailable_part(filename: str, kind: str, reason: str, reason_code: str) -> dict:
    ...
```

The text should be clear and model-facing. Use wording close to this:

```text
[Attachment unavailable: The user attached "<filename>" (<kind>), but its contents were not available to you because <reason>. Do not guess or invent the attachment contents. Tell the user you could not read or see this attachment.]
```

Required `<kind>` values:

- `document`
- `image`

Required `<reason>` cases:

1. File exceeds `MAX_UPLOAD_BYTES` / 50 MB app limit.
2. Document-like upload while Tika is unavailable (`tika_ok` is false).
3. `parse_with_tika(...)` raises.
4. `parse_with_tika(...)` returns empty or whitespace-only extracted text.
5. Image upload when `vision_supported` is false.
6. Document was dropped from `doc_entries` to fit the context budget (`skipped_docs`).
7. Historical image messages are skipped during API payload conversion because current `vision_supported` is false, such as after an operator swaps to a non-vision model mid-session.

The note must be part of the same user message content list so it is sent to the model in both the current request and later conversation history.

### A1 formatting wall: synthetic unavailable notes must not look like document context

Synthetic unavailable-attachment notes must **never** contain a line matching the document-context block format:

```regex
^---\s*(.+?)\s*---\s*$
```

They also must not start with `CONTEXT_PREFIX`.

Reason: `ephemeral/export.py::_extract_export_info()` scans synthetic parts for `--- filename ---` document blocks. A synthetic unavailable note that mimics that block format could be misinterpreted as extracted document context and could leak into copied/exported attachment lists.

The suggested bracketed note wording above is safe. Keep it that way.

Do **not** write synthetic notes to disk. Do **not** add visible assistant messages for these notes unless separately requested. The purpose of the synthetic note is to correct model behavior while keeping the UI behavior mostly stable.

### A2. Preserve existing visible attachment UX

Keep the visible attachment card/badge behavior unless a file is over the 50 MB app limit and is rejected before attachment parts are created.

Do not remove the existing user-facing `st.info` / `st.error` messages. The synthetic notes are an additional model-safety layer, not a replacement for user-facing notices.

### A3. Prevent `DEFAULT_UPLOAD_PROMPT` from becoming a hallucination trigger

Currently, if the user uploads files without typing text, the app substitutes `DEFAULT_UPLOAD_PROMPT` before it knows whether any file content will be available to the model.

After this PR:

- If the user typed actual text, preserve and send that text.
- If the user uploaded files but typed no text, send `DEFAULT_UPLOAD_PROMPT` only when at least one uploaded file produced model-available content:
  - document context was successfully extracted and kept; or
  - an image is included and `vision_supported` is true.
- If the user uploaded files but typed no text and **zero** attachments are available to the model, do **not** send `DEFAULT_UPLOAD_PROMPT` by itself. The model-facing message should contain the attachment markers and/or hidden synthetic notes sufficient for the assistant to say it cannot read/see the attachment.

Implementation notes:

1. Track `raw_user_text` separately from any app-generated default prompt. Avoid using a single variable that loses whether text was typed by the user or auto-filled by the app.
2. The current submit handler renders the user's bubble before file parsing completes. At that point the app cannot yet know whether `DEFAULT_UPLOAD_PROMPT` will be appropriate under the new conditional logic. Do **not** broadly reorder the submit handler to fix this transient first-render mismatch. Render the raw typed text at that moment, which may be empty for attachment-only sends. Treat the post-`st.rerun()` history render as the authoritative final display.
3. When building `content_for_llm`, do not drop a single synthetic note just because the content list length is one. If there are any parts, and those parts are required for model correctness, store/send the list. The current pattern `parts if len(parts) > 1 else user_text` is not sufficient for cases where the only model-facing content is a synthetic unavailable note.

### A4. Non-vision image handling must not silently drop images

When the conversation payload is built for the OpenAI-compatible API:

- Image parts should still be sent as image data only if `vision_supported` is true.
- If `vision_supported` is false, the model must receive a synthetic text note for each unavailable image instead of silently receiving only `📷 *filename*` or `(Attachment omitted.)`.

Implementation requirement:

1. Add the synthetic image-unavailable note during upload processing when `image_count > 0 and not vision_supported`, so new stored message history accurately reflects what the model can and cannot access.
2. Also update the history-to-API payload conversion loop so that if it skips an existing historical `image` or `image_url` part because `vision_supported` is false, it emits a short synthetic text note for that image **unless an equivalent unavailable-image note for the same filename already exists in that message**.
3. Use metadata such as `_attachment_unavailable` / `reason_code` to avoid duplicate notes.

This second conversion-loop requirement covers the remaining silent-drop path where vision support changes mid-session after historical image messages were stored.

### A5. Context-budget dropped documents must be disclosed to the model

The existing ghost-doc cleanup removes markers for documents dropped from `doc_entries` because the prompt is too large. Preserve that cleanup, but also add a hidden synthetic note for each dropped document explaining that it was omitted to fit the model context window and must not be guessed about.

This prevents a user prompt such as “compare all attached documents” from producing an answer that silently ignores one of the files without the model knowing the omission happened.

### A6. New Chat must clear content-bearing caches

`reset_chat_session()` must clear conversation-scoped content caches, especially:

- `_tika_cache` — can contain full extracted document text.
- `_token_count_cache` — contains hashes/token counts, not full text, but should reset with the conversation for consistency.

This is not merely tidying. `README.md` currently promises that document parsing results are cached per-session for performance but are cleared when starting a new conversation or closing the browser. Therefore A6 fixes a documented privacy claim violation; do not weaken the README promise to match the bug.

Add:

```python
st.session_state.pop("_tika_cache", None)
st.session_state.pop("_token_count_cache", None)
```

Keep existing reset behavior for messages, welcome state, token count, tokenizer state, vision support, thinking mode, and the `main_chat` widget key.

## Non-requirements for PR A

Do not:

- persist warnings as visible assistant messages;
- change export/copy UX except to ensure hidden synthetic notes are excluded;
- change the system prompt;
- change `CONTEXT_PREFIX` document context format;
- change Tika parsing implementation;
- refactor `ephemeral_app.py` broadly;
- add a database or durable upload store.

## Tests for PR A

At minimum:

1. Add or update tests in `tests/test_export.py` proving that synthetic unavailable-attachment notes are excluded from:
   - `_extract_export_info(...)` message text;
   - `build_message_markdown(...)`;
   - `build_message_html(...)`;
   - full conversation markdown/HTML export.

   Example synthetic note for the test:

   ```python
   {
       "type": "text",
       "_synthetic": True,
       "_attachment_unavailable": {
           "name": "scan.pdf",
           "kind": "document",
           "reason_code": "empty_extraction",
       },
       "text": '[Attachment unavailable: The user attached "scan.pdf" (document), but its contents were not available to you because text extraction returned no readable text. Do not guess or invent the attachment contents.]',
   }
   ```

   The note text must not appear in exported message text. The filename may appear in exports only if there is a separate visible attachment marker such as `📄 *scan.pdf*`.

2. Add a test that a synthetic unavailable note containing ordinary bracketed text is not parsed as document context.

3. Add a test or static contract proving `reset_chat_session()` clears `_tika_cache` and `_token_count_cache`. If importing `ephemeral_app.py` is unsafe because it executes Streamlit UI code, a static contract in `tests/test_ui_static_contracts.py` is acceptable.

4. If a helper function is introduced for synthetic note construction, test it as a pure function. Do not add broad app import side effects just for testing.

5. Add a unit/static test for the over-limit unavailable-note branch by testing the note-construction/helper behavior or by temporarily lowering `MAX_UPLOAD_BYTES` in a controlled test. Do not rely on a normal UI upload larger than 50 MB, because Streamlit rejects oversized files before app code sees them.

## Manual validation for PR A

After tests pass, manually validate:

1. Tika down:
   - Stop/disable Tika.
   - Upload a PDF with no typed text.
   - Assistant should say it cannot read the document, not summarize it.

2. Empty extraction:
   - Upload a scanned/image-only PDF or force `parse_with_tika` to return empty text in a test/stub environment.
   - Assistant should not invent document contents.

3. Non-vision image:
   - Force `LLM_SUPPORTS_VISION=false`.
   - Upload an image.
   - Assistant should say it cannot see/read the image unless the user describes it.

4. Over-limit defense-in-depth path:
   - Do not expect the normal UI to exercise this with a >50 MB file, because `st.chat_input(max_upload_size=50)` and server `maxUploadSize = 50` reject it before app code sees it.
   - Validate with a unit test/helper test or, for manual testing only, temporarily lower `MAX_UPLOAD_BYTES` below the UI/server cap and upload a file above that temporary app limit.
   - The model must not receive only `Please analyze the uploaded files.`

5. Export/copy:
   - Copy/export conversation after an unavailable attachment.
   - Hidden synthetic notes must not appear in the copied/exported transcript.

---

# PR B — Context-source cleanup and retargeting docs

## Problem

`docker-compose.yml` currently sets:

```yaml
- LLM_CONTEXT_TOKENS=262144
```

This makes the app use a hard-coded app-side context-budgeting hint before querying Ollama `/api/show`. That can drift from the actual runtime `PARAMETER num_ctx` in the `ephemeral-default` Modelfile, especially if an operator follows deployment guide advice to lower `num_ctx` for VRAM/latency reasons.

The repo also currently says the app can be retargeted by changing `LLM_MODEL_NAME` to any model tag. That is incomplete because raw model tags may expose model maximum context metadata rather than the actual runtime `num_ctx` allocated by Ollama. The stable, safer path is to keep `LLM_MODEL_NAME=ephemeral-default` and recreate that alias with the desired base model and explicit `PARAMETER num_ctx`.

## Functional requirements

1. Remove `LLM_CONTEXT_TOKENS=262144` from `docker-compose.yml` default environment.
2. Keep `LLM_CONTEXT_TOKENS` supported in `ephemeral/config.py` and `ephemeral/llm_client.py` as an explicit operator escape hatch.
3. Do not change `get_model_ctx()` fallback logic in this PR.
4. Update `README.md` so the primary retarget path is:
   - create/recreate local alias `ephemeral-default` from the chosen Ollama base model;
   - include explicit `PARAMETER num_ctx <value>` in that alias Modelfile;
   - keep `LLM_MODEL_NAME=ephemeral-default` in Compose.
5. Update `System Deployment Guide.md` so remediation for CPU offload/OOM/latency says:
   - lower `PARAMETER num_ctx` in `/root/Modelfile.qwen36-ephemeral` or equivalent alias Modelfile;
   - recreate the alias;
   - restart/test;
   - no compose context override is needed for the default Ollama deployment.
6. Update `AGENTS.md` context guidance:
   - `PARAMETER num_ctx` in the Ollama alias is the default source of truth;
   - `LLM_CONTEXT_TOKENS` is only for non-Ollama backends, discovery failures, or explicit operator override;
   - do not reintroduce `LLM_CONTEXT_TOKENS` to the default Compose stack without a reason.
7. Review any docs that say “change one environment variable” or “set `LLM_MODEL_NAME` to any model tag” and soften/correct them.

## Documentation wording guidance

Use plain-language wording suitable for IT generalists. Suggested language:

```text
For Ollama deployments, prefer retargeting the local alias rather than pointing the app directly at a raw model tag. Keep `LLM_MODEL_NAME=ephemeral-default`, recreate the alias from the desired base model, and set `PARAMETER num_ctx <value>` in the alias Modelfile. EphemerAl reads that alias metadata from Ollama and uses it for document/context budgeting.
```

Mention that `LLM_CONTEXT_TOKENS` still exists as an advanced override, but it must match the backend’s real context window or the app can over-pack prompts.

## Tests for PR B

At minimum:

- Existing tests must pass.
- Add/update a static contract if useful to assert that default `docker-compose.yml` no longer contains `LLM_CONTEXT_TOKENS=262144`.
- Do not add brittle exact-copy tests for long README paragraphs unless already consistent with the repo’s static-contract testing style.

## Manual validation for PR B

1. Build/run stack with default alias.
2. Confirm debug sidebar/context display still shows model context when Ollama is reachable.
3. Confirm no Python import or config errors after removing the compose env var.

---

# PR C — Tika timeout and timezone deployment hardening

## C1. Raise Tika timeout default

### Problem

`ephemeral/config.py` currently defaults:

```python
TIKA_TIMEOUT_S = _int_env("TIKA_TIMEOUT_S", 15)
```

The app allows 50 MB uploads and uses the full Apache Tika image with OCR capability. A 15-second timeout is too short for many legitimate large PDFs, Office documents, and OCR/scanned-PDF cases.

### Requirements

1. Change default timeout to 120 seconds:

   ```python
   TIKA_TIMEOUT_S = _int_env("TIKA_TIMEOUT_S", 120)
   ```

2. Keep the `TIKA_TIMEOUT_S` environment override.
3. Do not add background parsing, progress bars, queues, or threading.
4. Preserve the existing spinner `Reading {filename}…`.
5. Update `System Deployment Guide.md` customization/troubleshooting notes to mention `TIKA_TIMEOUT_S` and explain that large/OCR-heavy files can take longer.
6. Optionally update `README.md` if it already has a configuration table or deployment-tuning section.

### Tests

- Existing tests must pass.
- Add a simple static/config test only if consistent with existing style.

## C2. Surface `EPHEMERAL_TIMEZONE`

### Problem

The app already supports `EPHEMERAL_TIMEZONE` in `get_local_timezone()`, but `docker-compose.yml` leaves it commented out. Containers often default to UTC, which can make the system prompt’s “Current local time” wrong for staff.

### Requirements

1. In `docker-compose.yml`, make `EPHEMERAL_TIMEZONE` an active environment variable with an IANA timezone value and a clear customization comment.

   Preferred pattern for the current UW/Pacific-oriented deployment:

   ```yaml
   - EPHEMERAL_TIMEZONE=${EPHEMERAL_TIMEZONE:-America/Los_Angeles}  # CUSTOMIZE: set to your local IANA timezone.
   ```

   If the repo owner wants a more geographically neutral public default, use an obvious placeholder and docs requiring customization. Do not leave the variable commented out without a clear required setup step.

2. Do not mount `/etc/localtime` from host into the container.
3. Update `System Deployment Guide.md` pass criteria to include:
   - ask the assistant what time it is;
   - confirm it matches the local wall clock/timezone.
4. Mention that `EPHEMERAL_TIMEZONE` must be an IANA timezone name such as `America/Los_Angeles`.

### Tests

- Existing tests must pass.
- No app code change is required unless docs/static tests need adjustment.

---

# PR D — Remove dead mobile device detection dependency

## Problem

The repo includes `streamlit-browser-engine==0.0.3` only for optional mobile detection and a duplicate mobile “🔄 New Chat” button. The sidebar already has New Chat, and Streamlit’s responsive sidebar is the supported mobile path. This dependency adds supply-chain surface for little or no value.

## Requirements

1. Remove `streamlit-browser-engine==0.0.3` from `requirements.txt`.
2. Remove the optional import block from `ephemeral_app.py`:
   - `from streamlit_browser_engine import device`
   - `HAS_DEVICE_DETECTION`
   - `device = None`
3. Remove the mobile convenience button block:

   ```python
   if HAS_DEVICE_DETECTION and device and device.is_mobile:
       if st.button("🔄 New Chat", key="mobile_new", width="stretch"):
           reset_chat_session()
           st.rerun()
   ```

4. Preserve the sidebar `New Chat` button.
5. Update tests:
   - `tests/test_ui_static_contracts.py::test_new_chat_labels_and_placeholder_contracts` currently expects `"🔄 New Chat"`; remove or revise that assertion.
   - Add/adjust a static contract to assert `streamlit-browser-engine` is not in `requirements.txt` and `streamlit_browser_engine` is not imported.
6. Update `AGENTS.md` only if it mentions mobile detection/device engine behavior. Do not otherwise rewrite AGENTS.

## Non-requirements

Do not replace this with another device-detection library. Do not add custom mobile CSS. Do not move or redesign the sidebar.

---

# PR E — Logging/troubleshooting consistency

## Problem

The deployment guide instructs operators to run:

```bash
docker compose logs ollama
docker compose logs tika-server
```

But `docker-compose.yml` currently configures both `ollama` and `tika-server` with:

```yaml
logging:
  driver: "none"
```

That means the guide’s troubleshooting command is inconsistent with the default compose privacy posture.

## Requirement decision

Do **not** automatically enable Ollama/Tika logs by default unless the repo owner explicitly chooses installability over the stricter privacy default.

For this requirements document, use the privacy-conservative implementation:

1. Keep default `logging: driver: "none"` for `ollama` and `tika-server`.
2. Update `System Deployment Guide.md` troubleshooting to explain:
   - app logs are available from `ephemeral-app` because it uses rotated local logs;
   - Ollama and Tika logs are disabled by default for privacy/minimal retention;
   - because backend logs are disabled, `docker compose logs ollama` and `docker compose logs tika-server` will not show useful output unless logging is temporarily re-enabled;
   - disabling Ollama logs also suppresses server-side diagnostics such as prompt-truncation warnings, which are useful when investigating context/window drift;
   - for troubleshooting, operators may temporarily switch those two services to rotated local logs, collect diagnostics, then switch back.
3. Include an explicit rotated-local example in the guide:

   ```yaml
   logging:
     driver: "local"
     options:
       max-size: "2m"
       max-file: "3"
   ```

4. Include the exact command sequence and the container-recreation warning:

   ```bash
   # After editing docker-compose.yml to temporarily enable logs:
   docker compose up -d --force-recreate ollama tika-server
   docker compose logs --tail=200 -f ollama tika-server

   # After collecting diagnostics, change both services back to driver: "none", then recreate again:
   docker compose up -d --force-recreate ollama tika-server
   ```

   Add this warning in plain language:

   ```text
   Docker logging driver changes apply when containers are created. `docker compose restart` is not enough after changing a service's logging driver.
   ```

5. Update README wording if it currently says log suppression is optional in a way that conflicts with the compose default. Make the README accurately describe the default:
   - EphemerAl app logs: rotated local logs for debugging.
   - Ollama/Tika logs: disabled by default in the privacy-oriented stack.
   - Hardened/diagnostic choices are documented in compose/guide.

## Alternative owner-approved implementation

If the owner explicitly approves enabling backend logs by default, then change `ollama` and `tika-server` to the same rotated local driver as `ephemeral-app`, and add a compose comment saying hardened kiosk deployments can change those two services back to `driver: "none"`.

Do not make that choice silently.

---

# Optional PR F — Replace `tika` PyPI client with behavior-preserving direct HTTP

## Status

This is a useful simplification but should be a separate PR after PRs A-C. It touches document parsing behavior and must be validated with real Tika server containers and representative files.

Do not implement PR F unless explicitly requested.

## Factual constraint

A behavior-preserving replacement for `tika.parser.from_buffer(...)` must use Tika's recursive metadata endpoint, not the simpler plain-text endpoint.

`tika.parser.from_buffer(...)` in `tika==3.1.0` uses `/rmeta/text` with `Accept: application/json` and concatenates `X-TIKA:content` from each returned JSON object. That recursive behavior matters for container formats such as email files, Office files with embedded objects, archives, and attachments.

Do **not** replace it with `PUT /tika` + `Accept: text/plain` as a supposedly equivalent drop-in. `/tika` changes extraction semantics and can introduce charset-decoding issues when a `text/*` response omits charset.

## Problem

The app already talks to a Tika server. The `tika` PyPI client adds behavior that is undesirable outside compose, including trying to manage/download a Tika server unless configured correctly. A direct HTTP call can remove that dependency and keep timeout behavior under app control, but only if it preserves the current recursive extraction semantics.

## Requirements

1. In `ephemeral/tika_client.py`, remove:

   ```python
   from tika import parser
   ```

2. Replace `parser.from_buffer(...)` inside `parse_with_tika(data, filename)` with direct `requests.put(...)` to the existing Tika server recursive endpoint:

   ```python
   base = TIKA_URL.rstrip("/")
   resp = requests.put(
       f"{base}/rmeta/text",
       data=data,
       headers={
           "Accept": "application/json",
           "Content-Type": "application/octet-stream",
       },
       timeout=TIKA_TIMEOUT_S,
   )
   ```

3. On non-2xx response, raise a concise `RuntimeError` containing only status code/reason, not the response body, to avoid accidentally surfacing document text or parser internals.

4. On success, parse JSON and concatenate `X-TIKA:content` values:

   ```python
   try:
       payload = resp.json()
   except ValueError as exc:
       raise RuntimeError("Tika returned invalid JSON") from exc

   if not isinstance(payload, list):
       raise RuntimeError("Tika returned an unexpected response shape")

   text = "".join(
       (entry.get("X-TIKA:content") or "")
       for entry in payload
       if isinstance(entry, dict)
   ).strip()
   ```

5. Preserve exactly:
   - `parse_with_tika(data: bytes, filename: str) -> str` signature;
   - SHA-256 content hash cache key;
   - session-scoped cache in `st.session_state["_tika_cache"]`;
   - TTL cleanup behavior;
   - spinner `Reading {filename}…`;
   - no app-level logging of uploaded content or extracted text.

6. Remove `tika==3.1.0` from `requirements.txt`.
7. Remove `TIKA_CLIENT_ONLY=true` from `docker-compose.yml` because the PyPI client is gone.
8. Update `AGENTS.md` dependency notes to say Tika parsing is performed by direct HTTP to the Tika server, not `tika-python`.

## Behavior-changing alternative, not recommended here

If the owner deliberately wants main-document-only extraction instead of recursive extraction, that is a separate behavior-changing PR and must say so explicitly. It should not be presented as cleanup.

If `/tika` text extraction is ever chosen intentionally, decode from bytes explicitly rather than using `resp.text` blindly:

```python
text = resp.content.decode("utf-8", errors="replace").strip()
```

## Tests and validation

1. Add unit tests by monkeypatching `requests.put` and a minimal Streamlit session state/spinner environment.
2. Test success response assembly from JSON list with multiple `X-TIKA:content` entries.
3. Test non-2xx response raises concise `RuntimeError` without response body.
4. Test invalid JSON and unexpected response shape.
5. Manually validate against the actual `apache/tika:3.3.0.0-full` container:
   - upload a PDF;
   - upload a DOCX;
   - upload a scanned/OCR-heavy PDF if available;
   - upload at least one container-format file such as `.eml`, `.msg`, an archive, or a DOCX with an embedded spreadsheet/object;
   - confirm successful extraction appears only as hidden context to the model, not in export text.

---

# Items deliberately out of scope

Do not implement these as part of the above PRs unless separately requested:

1. Streamlit framework replacement.
2. Ollama replacement.
3. OpenAI-compatible API → native Ollama API migration.
4. Clipboard iframe rewrite.
5. CSS consolidation.
6. Broad `ephemeral_app.py` refactor.
7. System prompt redesign.
8. Full dependency lockfile/constraints generation.
9. CORS/XSRF changes.
10. Pillow upgrade.

Notes on the last two: CORS/XSRF and Pillow were identified in other reviews as potentially valuable, but they are not included in this requirements document because this document focuses on the third review’s app-grounding/deployment tasks. Treat them as separate security PRs, not part of this implementation batch.

---

# Validation commands

Run from repo root.

Minimum validation for every PR:

```bash
python -m py_compile ephemeral_app.py ephemeral/*.py
python -m pytest -q
ruff check .
bash scripts/validate.sh
```

For PRs touching Streamlit UI behavior, upload/chat flow, `ephemeral_app.py`, or mobile button behavior, also run:

```bash
bash scripts/validate_ui.sh
```

If browser automation is unavailable, report that clearly and perform a manual UI smoke test.

Full stack/manual validation for compose/docs changes:

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

Then open the app and check:

1. Normal chat returns an answer.
2. PDF/DOCX upload works.
3. New Chat clears conversation and upload state.
4. Copy conversation still works.
5. The assistant’s current-time answer matches configured timezone.
6. Retarget/context docs are internally consistent.
7. No prompts, uploaded documents, extracted text, or model outputs are added to app logs.

---

# Expected implementation summary

A correct implementation should produce small diffs focused around:

- `ephemeral_app.py`
- `ephemeral/config.py`
- `ephemeral/tika_client.py` only if optional PR F is implemented
- `ephemeral/export.py` tests only, unless export implementation must change
- `requirements.txt`
- `docker-compose.yml`
- `README.md`
- `System Deployment Guide.md`
- `AGENTS.md`
- `tests/test_export.py`
- `tests/test_ui_static_contracts.py`

It should not touch `theme.css`, `ephemeral/clipboard.py`, `ephemeral/stream_filter.py`, Docker runtime images unrelated to the specified changes, or system prompt text.

---

# Suggested prompt for a fresh coding context

Upload the current repo and this document, then use:

```text
Read the attached repo and the attached requirements document. Implement PR A only. Do not implement PRs B-F unless asked. Follow the requirements exactly. If any requirement does not match the current repo, stop and report the mismatch before editing. After implementation, report the exact files changed and validation results.
```
