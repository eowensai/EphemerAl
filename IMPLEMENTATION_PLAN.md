# EphemerAl implementation plan

**Status:** Proposed implementation baseline; application implementation has not started
**Repository analysis baseline:** `bede6eb79cfa39115ef1e941e0b3358d23713275`
**Program integration branch:** `Dev`
**Public release branch:** `main`
**Plan created:** July 10, 2026
**Audience:** The project owner and coding agents working in fresh contexts

## 1. Purpose and authority

This is the single implementation authority for turning EphemerAl from a working
technical project into a credible public, privacy-oriented application. It consolidates:

- the current repository;
- the owner's product briefing;
- the principal architecture and technology review completed July 10, 2026; and
- useful findings from
  `ephemeral_requirements_grounding_deployment_hardening_v2.md`.

The Fable requirements document is preserved for provenance, but agents must not
execute it as a second roadmap. This plan accepts, modifies, sequences, or rejects its
recommendations.

`README.md` and `System Deployment Guide.md` describe released/current behavior. They
must be updated as work packages change that behavior, but they do not override this
plan. Tests and source comments likewise document current contracts; approved work may
update obsolete contracts atomically.

The planning package was published in merge commit `68427d3`; Prompt 0 in the runbook
is complete and must not be used again. Pasting Prompt 1 as directed in the runbook
constitutes approval to begin this documented program. Until then, this remains a
proposed plan and none of the application work below is accepted or started.

Once execution begins, only the owner may change product goals, privacy promises,
license obligations, supported platforms, meaningful acceptance outcomes, or package
scope. Coding agents may select an equivalent technical fallback within an approved
package when a named version/library/model is unavailable, insecure, or fails its gate.
The fallback must preserve product intent, use current primary-source evidence, remain
inside package non-scope, and receive independent review. Agents update package status
and evidence as described in Section 7 rather than returning technical selection to the
owner.

## 2. How the owner uses this plan

The owner should never have to edit source files or choose implementation details.

1. Open Codex in the web browser.
2. Select repository `eowensai/EphemerAl` and starting branch `Dev`.
3. Paste Prompt 1 from `CODEX_RUNBOOK.md`. Codex will inspect this plan and implement
   only the first eligible work package.
4. When Codex finishes, use its **Create pull request** control if it did not already
   create one. The pull request must say that its destination or base branch is `Dev`.
5. Copy the pull-request link and open a new ChatGPT Work conversation. In the empty
   message box, type `@GitHub` and select **GitHub** from the list, then paste Prompt 2
   with the link in the marked place. ChatGPT Work inspects the pull-request branch and
   `Dev`; the owner does not need to check out code or understand the branch structure.
6. If that completed review cannot access the final merge action, paste the runbook's
   Prompt 2M into a new ChatGPT Work conversation: type `@GitHub`, select **GitHub**,
   and include the same pull-request link. ChatGPT Work re-verifies and merges the
   approved pull request into `Dev`.
7. Repeat. Package status, pull requests, and the evidence ledger carry context
   forward; the owner does not need to remember implementation details between chats.

The runbook describes each browser step and provides complete prompts. The owner is
not expected to use a terminal, maintain a local repository, understand worktrees, or
configure a Codex environment or setup script. If Codex needs dependencies in its
hosted workspace, Codex installs the repository's pinned requirements itself in an
isolated environment.

If owner action on real Windows/GPU hardware is unavoidable, Codex must provide one
complete copy/paste command or script and explain what output to return. The owner must
not be told to edit YAML, insert code at line numbers, choose a library, or design a
technical solution.

### Program branch and release path

`Dev` is the authoritative integration line for this implementation program even
though GitHub's repository default branch is `main`.

For every ordinary work package and regression fix:

1. Update from `origin/Dev`.
2. Create one focused work branch from that exact `Dev` commit.
3. Open the pull request with `Dev` as its destination/base.
4. Independently review and merge it into `Dev` only after its gates pass.

Do not modify `main` during ordinary work packages. It remains the public-release line.
After WP-10 produces a GO result, Prompt 7 verifies the complete `Dev` history, opens a
dedicated `Dev`-to-`main` promotion pull request, requires its checks to pass, and
merges it. Only the resulting verified `main` commit may receive the version tag and
published release artifacts. If `main` contains unexpected work that is not already in
`Dev`, the promotion stops for review rather than overwriting or bypassing it.

## 3. Product briefing

### Purpose

EphemerAl provides a modern local LLM experience without cloud processing, user
accounts, or saved chat history. Important use cases include:

- a technically inclined person hosting private AI for a household;
- a small school giving teachers and students supervised experience with AI;
- a small department proofreading or analyzing material containing PII; and
- accurate meeting-minutes and action-item extraction from long transcripts.

### Expected usage

- Approximately 1–20 intermittent users.
- One model generation at a time by default.
- One Windows 11 computer with an NVIDIA GPU for the first supported release.
- Office documents, PDFs, spreadsheets, text, scanned documents, and images.

### Priorities

In practical order:

1. Truthful and reliable behavior.
2. A setup path a non-Linux user can complete.
3. Local/offline privacy and genuine erasure of conversation state.
4. Strong long-document results without similarity RAG hiding context.
5. Predictable performance and resource use on consumer hardware.
6. Low maintenance burden for one AI-assisted maintainer.
7. A clean, understandable UI for people learning AI.

### Non-negotiables

- Local/offline operation after initial provisioning.
- Windows 11 support and NVIDIA support at minimum.
- No user accounts.
- No application database or persisted chats.
- No cloud inference or cloud document processing.
- No content-bearing application logs.
- No default similarity RAG or vector database.
- No rewrite, microservices, or additional infrastructure without a measured need.

## 4. Definition of a viable public release

The first viable public release is achieved only when all of the following are true:

- An unavailable attachment can never be mistaken by the user or model for a readable
  attachment.
- New Chat clears all conversation-derived text, images, hashes, caches, and widgets.
- Full document text is used whenever it fits the verified running context.
- Configured, advertised, and running context cannot silently drift.
- The default system prompt is organization-neutral.
- Localhost is the network default; trusted-LAN mode is explicit and restricted.
- A non-Linux user can install, start, diagnose, update, and uninstall using complete
  Windows scripts rather than hand-editing files.
- At least one model/hardware profile has published, reproducible validation evidence.
- The UI reports busy, unavailable, omitted, and unsupported states plainly.
- CI, integration tests, and a release-candidate checklist cover the critical privacy,
  document, model, and deployment paths.
- Documentation matches the released behavior and contains no commands that are known
  not to work with the default configuration.

## 5. Fixed technical decisions

These decisions are made. Do not return them to the owner as open questions.

| Area | Decision |
|---|---|
| Application architecture | Retain the Streamlit modular monolith. Do not add a separate frontend/backend. |
| Service boundaries | Retain Ollama, Apache Tika Server, and Docker Compose for the first viable release. |
| Document strategy | Full-context first. Use every ordered chunk only when content exceeds verified context. Never substitute similarity RAG by default. |
| Persistence | No accounts, database, saved conversations, durable upload store, or content-bearing logs. |
| Parser | Keep the Tika full image. Move the Python client to direct `/rmeta/text` HTTP while preserving recursive extraction. |
| Internal model transport | Keep the OpenAI-compatible SDK path for the first viable release. Native Ollama client migration is a later evidence-gated experiment. |
| Windows distribution | Docker Desktop is the easy path where its license applies. Retain the Docker Engine-in-WSL route as the advanced/license-neutral alternative. |
| Network | Default to localhost. Trusted-LAN exposure is explicit, Private/LocalSubnet restricted, and still described as unencrypted trusted-network traffic. |
| Framework target | After the first viable release unless current APIs block it, test Streamlit `1.59.1` and replace private `st._bottom`. If it fails compatibility, retain the current tested pin and defer modernization rather than asking the owner to choose another version. |
| Tika version target | Retain tested `3.3.0.0-full` on the first-release critical path unless WP-10 finds a material issue. WP-03 later tests `3.3.1.0-full`. Never adopt Tika 4 beta/snapshot in this program. |
| Ollama upgrades | Do not treat `0.21.0` to current `0.31.x` as routine. Benchmark the exact candidate against required Qwen vision, thinking, long-context, follow-up, and GPU tests. Adopt the newer pin only if it passes. |
| Standard model candidate | `gemma4:12b`, 32K context, provisional 16 GB NVIDIA class. If it fails certification, do not silently substitute a model or publish the profile; record the failure for independent review. |
| Extended model candidate | `qwen3.6:35b-a3b`, 128K context, provisional 32 GB NVIDIA class. |
| Maximum-context mode | Qwen 256K remains an advanced certified option only when `/api/ps` and benchmarks prove full context and acceptable GPU residency on that machine. |
| Concurrency | One loaded model and one generation at a time. Queue depth 4. Default keep-alive 30 minutes; dedicated-appliance mode may use `-1`. |
| Logging | Ollama and Tika logs remain disabled in the privacy default. A diagnostic Compose override temporarily enables small rotated logs and recreates the containers automatically. |
| UI | Preserve the clean, low-distraction layout. Modernize supported APIs without a redesign. |
| Timezone | Use browser/session timezone when available, with `EPHEMERAL_TIMEZONE` as an explicit operator override. Never hard-code a public Pacific/UW default. |
| Public prompt | Replace the UW/HFS default with a generic prompt. Preserve the existing UW/HFS prompt as an optional example, not the default. |
| Release method | Versioned app image plus release ZIP and checksums. Do not bundle model weights. |

## 6. Reconciliation of the Fable requirements document

### Accepted and promoted

- Attachment grounding across Tika-down, extraction-error, empty extraction,
  unsupported-image, over-limit, context-dropped, and historical model-change paths.
- Conditional use of `DEFAULT_UPLOAD_PROMPT` only when at least one attachment actually
  reached the model.
- Structured hidden notes that do not leak into copy/export.
- Clearing `_tika_cache` and `_token_count_cache` on New Chat.
- Removing the default Compose `LLM_CONTEXT_TOKENS=262144` foot-gun.
- Raising the 15-second Tika timeout.
- Removing `streamlit-browser-engine`.
- Correcting the contradiction between disabled backend logs and troubleshooting
  commands.
- Replacing `tika-python` through `/rmeta/text`, not plain `/tika`, to preserve
  recursive extraction of embedded/container content.
- Recreating containers rather than merely restarting after logging-driver changes.

### Strengthened or modified

- Sanitize hostile filenames before inserting them into prompts, Markdown, headers, or
  delimiter-based context.
- Unavailable notes should say, “If the request depends on this attachment, tell the
  user,” so an old failure is not mentioned during every unrelated later turn.
- Persist `Unavailable` or `Omitted from context` status in the visible attachment
  card/history instead of relying only on transient messages.
- Recalculate admission from the final payload after omission notes are added.
- Use a diagnostic override and scripts instead of asking a nontechnical operator to
  hand-edit logging YAML.
- Use browser/detected timezone rather than a Pacific default.
- Preserve Streamlit 1.56 only during early correctness changes; modernize it later
  after CI exists.

### Not adopted as permanent constraints

- The prohibition on changing the system prompt; the public default must become
  generic in its own package.
- The prohibition on CORS/XSRF work; safe network defaults are a separate package.
- Permanent Streamlit 1.56 compatibility freezes.
- Permanent manual WSL/Docker/model provisioning.
- Treating the Fable document's optional/out-of-scope list as cancellation of the
  broader product roadmap.

## 7. Work-package workflow and status

### Status meanings

- `Planned`: approved, but prerequisites are not complete.
- `Ready`: next eligible package for implementation.
- `In progress`: implementation started but is not ready for independent review.
- `Needs review`: implementation claims acceptance criteria pass; a fresh context must
  independently verify it.
- `Complete`: independently reviewed, validated, and merged into `Dev`.
- `Blocked`: cannot proceed without a product-level decision or external prerequisite.
- `Deferred`: approved future work intentionally held outside the first-release sequence.

Implementation agents may change only the active package from `Ready` to `In progress`
and then `Needs review`. Independent-review agents may change `Needs review` to
`Complete`, or back to `In progress`/`Blocked`. After marking a package `Complete`, the
review agent may promote the next dependency-satisfied package from `Planned` to
`Ready`. `Deferred` packages are never promoted automatically. A WP-10 GO result leads
to Prompt 7 for the `Dev`-to-`main` promotion and then Prompt 8 for release publication,
not directly to WP-11.

An independent reviewer stages `Complete` and the next `Ready` status on the final
pull-request head only after validation passes. Those staged values are provisional:
the status table on `Dev` remains authoritative, and the package becomes Complete only
when that exact approved pull-request head merges into `Dev`. If `Dev` moves during
review, the same pull request must be updated and independently reviewed again before
merge.

Only one work package may be active repository-wide. If any package is `In progress` or
`Needs review`, or any work-package pull request remains open, a new implementation
agent must stop and resume/review that package rather than starting another.

Even when the table shows a package Ready, implementation may begin only after every
required push check on the exact current `Dev` head has completed successfully. A
pending or failed current-`Dev` check is a program blocker to investigate, not
permission to start the next package.

The status table and evidence ledger on `Dev` are the durable program record. Every
ordinary work-package or regression-fix pull request must target `Dev`. An open Codex
web task that has not yet produced its pull request also counts as the one active work
package; the owner must let it finish or resume it instead of launching another. A
Codex web task's inability to open a draft pull request midway through its run is not a
technical blocker. It may finish the focused implementation in its managed workspace
and publish the reviewable branch and pull request at the end.

### Validation gate classes

- **Automated merge gates:** Every package must pass its unit/static/integration tests,
  compilation, lint, and applicable PR checks before merge. After merge, required push
  checks on the exact resulting `Dev` commit must pass before another package begins.
- **Package environment gates:** Docker/browser behavior explicitly changed by a package
  must be tested in a suitable non-production environment when available. If the plan
  labels the check as release-candidate validation, it may be recorded for WP-10 rather
  than forcing the owner to test hardware after every early package.
- **Mandatory real-Windows/GPU merge gates:** Normally only WP-08, WP-09, and WP-10.
  These packages may remain `In progress` or `Needs review` while awaiting one complete
  owner-run script result.
- **Deferred release-candidate validation:** Early correctness packages may merge with
  strong automated coverage when full Windows/GPU/browser infrastructure is unavailable,
  provided the missing end-to-end case is recorded in the ledger and WP-10 matrix.

### Current status

| ID | Work package | Status | Prerequisite |
|---|---|---|---|
| WP-00 | Baseline, CI, and release guardrail | Ready | None |
| WP-01 | Attachment grounding and genuine New Chat erasure | Planned | WP-00 |
| WP-02 | Context source of truth and payload budgeting | Planned | WP-01 |
| WP-03 | Tika dependency consolidation | Deferred | First release published; separate owner authorization |
| WP-04 | Generic public prompt and correct conversation time | Planned | WP-02 |
| WP-05 | Attachment and extraction resource bounds | Planned | WP-01, WP-02, WP-04 |
| WP-06 | Supported Streamlit modernization | Deferred | First release published; separate owner authorization |
| WP-07 | Network, readiness, queue, and diagnostics | Planned | WP-00, WP-01, WP-02, WP-04, WP-05 |
| WP-08 | Curated model profiles and runtime certification | Planned | WP-02, WP-07 |
| WP-09 | Easy Windows distribution and release packaging | Planned | WP-08 |
| WP-10 | Independent release-candidate verification | Planned | WP-09 |
| WP-11 | Exhaustive overflow mode | Deferred | First release published; separate owner authorization |
| WP-12 | Image normalization and non-vision OCR fallback | Deferred | First release published, WP-03 complete, separate owner authorization |

The deliberately shortened first-release critical path is WP-00, WP-01, WP-02, WP-04,
WP-05, WP-07, WP-08, WP-09, and WP-10. Tika-wrapper removal, Streamlit modernization,
image normalization/OCR, and exhaustive overflow remain valuable but must not delay the
installable first release unless an earlier package proves one is a blocker.

## 8. Work packages

### WP-00 — Baseline, CI, and release guardrail

**Objective:** Establish repeatable validation before behavior changes.

**Selected approach:** One GitHub Actions workflow and a small monthly dependency
review configuration. Do not upgrade application dependencies in this package.

**Scope:**

- Record the current local test/compile/lint/Compose baseline.
- Add CI for Python 3.11 dependency installation, `pip check`, pytest, Ruff, Python
  compilation, `docker compose config`, and application-image build.
- Run the workflow for pull requests targeting `Dev` or `main` and pushes to `Dev` or
  `main`. This protects ordinary work, the later `Dev`-to-`main` promotion, and the
  release line. Do not configure CI only for GitHub's default `main` branch.
- Add monthly Dependabot pull requests for Python, GitHub Actions, and Docker where
  supported. Configure each Dependabot ecosystem with `target-branch: Dev` so its pull
  requests join the reviewed program line rather than defaulting to `main`. Do not
  auto-merge.
- Remove accidental duplicate test execution from `scripts/validate.sh` only if doing
  so preserves exactly the same coverage.
- Add a short compatibility-evidence location for tested Streamlit/Ollama/Tika/model
  combinations.

**Explicit non-scope:** Application behavior, dependency upgrades, Playwright browser
installation in CI, model downloads, GPU tests, release publication.

**Likely files:** `.github/workflows/ci.yml`, `.github/dependabot.yml`,
`scripts/validate.sh`, this plan's evidence ledger.

**Acceptance criteria:**

- CI configuration is syntactically valid.
- All currently runnable tests pass, or pre-existing failures are precisely recorded
  without being hidden.
- The app image builds without copying planning/review documents into the image.
- Pull requests targeting `Dev` or `main` and pushes to `Dev` or `main` invoke the
  intended CI gates; the eventual promotion to `main` cannot bypass them.
- Python, GitHub Actions, and Docker Dependabot updates target `Dev`, not `main`.
- No runtime behavior or production dependency changes.

**Validation:** Repository baseline commands plus workflow/Compose validation.

### WP-01 — Attachment grounding and genuine New Chat erasure

**Objective:** The model and user must always know whether an attachment was actually
available, and New Chat must remove all conversation-derived state.

**Selected approach:** Add an import-safe pure helper module for attachment identity,
name normalization, availability metadata, and safe model-facing notes. Assign an
in-memory UUID `attachment_id` to every upload and use it—not filename—for marker,
image, status, omission, and note deduplication. Store only session-scoped metadata with
the existing message content and attachment cards; never write it to disk.

**Required behavior:**

1. Permanently store a structured hidden model-facing note for irreversible cases:
   - defense-in-depth application size rejection;
   - Tika unavailable;
   - Tika exception;
   - empty/whitespace extraction;
   - document omitted to fit context after its bytes are no longer retained.
2. Image unavailability is reversible. Persist the image plus attachment metadata, then
   materialize a temporary synthetic note during API conversion only while the current
   model lacks vision. Derive the visible status from current capability. If a
   conditional stored note is used internally, suppress it whenever vision is
   available so a later vision model never receives both the image and a contradictory
   warning.
3. The note must be `_synthetic`, contain `attachment_id`, safe display name, kind, and
   a closed reason code. Allowed reason text comes from a fixed map such as
   `size_rejected`, `tika_unavailable`, `parse_error`, `empty_extraction`,
   `vision_unavailable`, and `context_omission`. Never insert raw exception strings,
   HTTP bodies, or parser messages into stored/model-facing text. The note must never
   start with `CONTEXT_PREFIX` or contain a line matching
   `^---\s*(.+?)\s*---\s*$`.
4. Use wording equivalent to:

   ```text
   [Attachment unavailable: The user attached "<safe name>" (<kind>), but its contents
   were not available because <reason>. Do not guess or invent its contents. If the
   current request depends on this attachment, tell the user it could not be read or
   seen.]
   ```

5. Sanitize the displayed/model-facing filename: strip both `/` and `\` path
   components regardless of the host OS, replace CR/LF and control characters, prevent
   delimiter injection, escape it for the destination, and cap the retained name at
   180 characters while preserving a useful extension.
6. Preserve raw typed user text separately. Define one `model_available` result for an
   attachment representation. Use `DEFAULT_UPLOAD_PROMPT` only when at least one
   representation actually reaches the model: retained document text, a vision image,
   or later successful OCR text.
   Do not broadly reorder the Streamlit submit handler merely to perfect the transient
   first render; render raw typed text there and treat post-rerun history as authoritative.
7. Preserve structured content even if the only part is one synthetic note; do not
   collapse it into an empty string.
8. When vision is unavailable for current or historical images, emit one dynamically
   deduplicated note per `attachment_id` during API conversion.
9. Store `Unavailable` or `Omitted from context` status in the attachment card/history
   for the current in-memory session. Reversible vision status updates with current
   capability. Keep existing concise visible notices.
10. Include synthetic-note overhead in the existing conservative budget and fail safely
    at the edge. WP-02 owns the complete final-payload budgeting replacement.
11. Clear `_tika_cache`, `_token_count_cache`, messages, images, attachment metadata,
    token state, vision state, prompt/time state, thinking state, and the input widget
    on New Chat.
12. Hidden notes and their text must not appear in per-message or full-conversation
   Markdown/HTML copy/export.

**Explicit non-scope:** Streamlit upgrade, CSS redesign, system-prompt rewrite, Tika
client replacement, model change, database/persistence.

**Likely files:** `ephemeral_app.py`, a new import-safe attachment helper,
`ephemeral/export.py` only if necessary, and focused tests.

**Acceptance criteria:**

- No supported failure path leaves the model reasonably believing it received missing
  contents.
- Export remains clean, including with hostile filenames containing quotes, Markdown,
  newlines, control characters, and delimiter-like text.
- New Chat removes every conversation-derived value covered above.
- Normal text, successful documents, successful vision images, copy, and export retain
  existing behavior.

**Validation:** Unit tests for helpers and payload decisions; export tests; reset tests;
UI/full-stack manual cases for Tika down, empty extraction, non-vision, model flip, and
context omission. Simulate over-limit behavior below Streamlit's own cap rather than
uploading a normal file over 50 MB.

### WP-02 — Context source of truth and payload budgeting

**Objective:** The app must never knowingly pack against a context size different from
the model actually running, and long follow-up requests should avoid self-inflicted
prefix changes.

**Selected approach:** Keep the OpenAI-compatible chat transport, use native Ollama
metadata endpoints for truth, and compute admission from the complete stored payload.

**Scope:**

- Remove default `LLM_CONTEXT_TOKENS=262144` from Compose. Keep the environment
  variable as an explicit advanced/non-Ollama override.
- Keep `ephemeral-default` as the normal alias and explicit `PARAMETER num_ctx` as the
  pre-load configured source.
- Use `/api/show` for expected alias configuration. Before accepting a document request
  after the model is unloaded, warm-load it through a native control-plane request that
  contains no user content, such as an empty `/api/generate` using alias defaults, then
  query `/api/ps` for actual runtime context and residency. This does not change the
  OpenAI-compatible chat transport.
- If expected and running context disagree, fail model readiness and block document
  generation with a repair-oriented message. Do not silently continue using the
  smaller value.
- Render and store the system prompt once on the first turn and reuse the identical
  string until New Chat. WP-04 may change prompt content/timezone resolution but must
  preserve this lifecycle.
- Estimate occupancy from the complete final system plus stored messages plus images
  and structured parts on every turn, with content-hash caching for speed and a
  documented conservative safety margin.
- Treat backend `usage` as performance telemetry, not the admission-control baseline.
- Remove the undocumented `/api/tokenize` probe and its session state unless current
  official Ollama documentation has added a supported equivalent by implementation
  time. Retain a conservative heuristic.
- Keep a response reserve, but document it as input-budget headroom rather than an
  output cap.
- Do not claim heuristic token estimates prove exact fit. Add backend
  truncation/context-error detection tests and record per-profile certification
  evidence.
- Correct retargeting docs: recreate the tracked alias with explicit `num_ctx` rather
  than telling novice operators to point at arbitrary raw tags.

**Explicit non-scope:** Native Ollama-client migration, dynamic arbitrary models,
per-conversation model switching, RAG, overflow multipass processing.

**Likely files:** `ephemeral/llm_client.py`, `ephemeral/token_budget.py` or a focused pure
context helper, `ephemeral_app.py`, Compose, README, deployment guide, tests.

**Acceptance criteria:**

- Default Compose contains no duplicate context hint.
- A content-free warm load makes `/api/ps` available; app-reported and running context
  agree in a loaded-stack test.
- An intentional show/ps mismatch blocks document submission and explains the operator
  repair rather than silently reducing context.
- A deliberately reduced alias context causes safe document omission rather than
  backend truncation/failure.
- Budget tests cover system, text history, images, structured parts, omission notes,
  and output reserve.
- The manual retargeting instructions contain no “change one variable to any model”
  shortcut.

### WP-03 — Tika dependency consolidation

**Objective:** After the first viable release, keep Tika's format/OCR breadth while
removing the redundant Python wrapper without changing extraction semantics.

**Selected approach:** Direct recursive Tika Server HTTP. Do not replace Tika itself.

**Scope:**

- Replace `tika.parser.from_buffer` with `PUT <TIKA_URL>/rmeta/text`, binary body,
  `Accept: application/json`, and `Content-Type: application/octet-stream`.
- For strict wrapper parity, do not add a filename hint in this package; the current
  `from_buffer` call does not pass the application filename. A future RFC-safe
  `Content-Disposition` enhancement requires separate extraction evidence.
- Require the exact `/rmeta/text` JSON-list shape and concatenate
  `X-TIKA:content` values in returned order.
- Stream the HTTP response with a 16 MiB cap and reject more than 256 recursive metadata
  entries. Abort safely rather than parsing truncated JSON or presenting partial output
  as complete.
- Raise concise errors containing status/reason only; never include response bodies or
  extracted content.
- Remove `tika` from Python requirements and remove `TIKA_CLIENT_ONLY`.
- Remove the duplicate parsed-text cache after WP-01 has established reset behavior.
  The active message already retains successful extracted text.
- Test and adopt `apache/tika:3.3.1.0-full` only after extraction parity passes.
- Add synthetic, non-sensitive fixtures or integration instructions for PDF, DOCX,
  scanned PDF, XLSX, and at least one recursive/container case such as EML, archive, or
  embedded object.
- Compare plain extracted structure with XHTML/HTML as evidence only. Do not change the
  normal extraction format in this package. Any structured-output change requires a
  separate future package with corpus-based acceptance criteria.

**Explicit non-scope:** `/tika` plain-text shortcut, MarkItDown, Kreuzberg, Docling,
format-specific parser collection, background jobs.

**Acceptance criteria:**

- Recursive extraction parity is demonstrated for ordinary and container documents.
- Non-2xx, invalid JSON, unexpected shape, empty content, and health failures
  have content-safe tests.
- Python Tika wrapper and its environment flag are gone.
- No document content is written to logs or disk.

### WP-04 — Generic public prompt and correct conversation time

**Objective:** Remove UW/HFS assumptions and keep one stable, correct system prefix for
each conversation.

**Selected approach:** Generic default prompt, optional file-based organization prompt,
browser/session timezone, and conversation-scoped prompt rendering.

**Scope:**

- Replace `system_prompt_template.md` with a concise generic public prompt preserving:
  honesty, document grounding, uploaded-content-as-untrusted-data, no live tools/web,
  sensitive-data restraint, and concise professional behavior.
- Preserve the current UW/HFS prompt under `examples/system-prompts/` as an optional
  example, not the default.
- Support an operator-supplied local prompt file through one documented environment
  setting. The default requires no configuration.
- Resolve time using `EPHEMERAL_TIMEZONE` when explicitly set, otherwise browser
  timezone/offset when available, otherwise a safe server fallback.
- Use standard-library `zoneinfo`/`datetime`; remove `pytz` when no longer needed.
- Preserve WP-02's conversation-scoped prompt snapshot while changing its generic
  content and timezone source; do not restore per-request rendering.

**Explicit non-scope:** Prompt editor UI, organization accounts, policy packs, tool use,
web access, broad prompt experimentation.

**Acceptance criteria:**

- Default behavior contains no UW/HFS language or implied university-system access.
- Document prompt-injection protection remains.
- Current time is correct in explicit override and browser-timezone tests.
- Follow-up requests reuse the identical system prompt string.
- New Chat creates a new prompt/time snapshot.

### WP-05 — Attachment and extraction resource bounds

**Objective:** Make upload, parser-output, archive, and retained-session memory
predictable across 1–20 sessions without expanding image features before installation.

**Selected initial limits:**

- 10 files per turn.
- 100 MiB aggregate upload bytes per turn while retaining the existing 50 MiB per-file
  defense.
- 8 images per turn.
- 32 MiB of retained image bytes per session.
- One Tika parse at a time per app process.
- 120-second Tika request timeout, operator-configurable.
- 16 MiB maximum extracted text accepted from one parse before session retention.
- Combined retained extracted-text bytes per session capped at the smaller of 8 MiB or
  eight UTF-8 bytes per verified available input token.

These are conservative release defaults, configurable by operators but not exposed as
normal-user controls.

**Scope:**

- Enforce the limits above with plain-language messages and the WP-01 model-facing
  unavailable/omission metadata.
- Raise the current Tika timeout default to 120 seconds while retaining its environment
  override and existing reading spinner; test timeout as a truthful parse failure.
- Apply extracted-output and retained-text limits before storing content in message
  state. Treat a reached bound as a truthful incomplete/omitted attachment state;
  never silently truncate and present it as complete.
- Retain Tika's 2 GiB JVM heap boundary for parser-side containment. Transport-level
  response and recursive-entry caps require the direct HTTP work deferred to WP-03.
- Release raw document bytes after parsing and do not create a second extracted-text
  cache.
- Add concurrency and memory-bound tests without committing sensitive/large fixtures.

**Explicit non-scope:** Background workers, persistent upload queue, GPU OCR model,
image normalization, standalone-image OCR fallback, image editor, arbitrary user
tuning. Image normalization/OCR is deferred to WP-12.

**Acceptance criteria:**

- Limits are enforced before excessive session retention.
- Excessive extracted output and retained-text limits fail truthfully rather than being
  stored or presented as complete.
- Repeated image turns do not retain both raw and encoded duplicates in session state.
- New Chat returns retained attachment memory to the baseline.

### WP-06 — Supported Streamlit modernization

**Objective:** Remove private/stale framework surfaces without redesigning the UI.

**Selected approach:** Pin Streamlit `1.59.1`, the reviewed stable release, after
compatibility testing. Do not jump to a newer release inside this package.

**Scope:**

- Upgrade from 1.56.0 to 1.59.1 in an isolated branch.
- Replace private `st._bottom` with public `st.bottom`.
- Remove `streamlit-browser-engine` and its duplicate mobile New Chat button; rely on
  the responsive sidebar and supported keyed styling.
- Use `st.context` behavior established in WP-04.
- Use supported Streamlit upload/AppTest surfaces.
- Make only CSS changes required for functional/visual compatibility. Gradually remove
  obsolete internal selectors touched by those changes.
- Keep the rich clipboard feature and its implementation unchanged unless a compatibility
  defect must be fixed for Streamlit 1.59.1.

**Explicit non-scope:** React/FastAPI, Gradio/NiceGUI, broad visual redesign, new pages,
feature expansion.

**Acceptance criteria:**

- No private Streamlit API remains.
- Desktop and mobile welcome, chat, upload, New Chat, copy, thinking toggle, streaming,
  and error states pass automated/manual smoke tests.
- AppTest covers upload/reset paths.
- Visual comparison shows no material regression.

### WP-07 — Network, readiness, queue, and diagnostics

**Objective:** Provide safe defaults and useful failure states without accounts or an
observability stack.

**Selected approach:** Explicit local/LAN deployment modes, health-gated startup,
application admission control, privacy-default logging, and a diagnostic override.

**Scope:**

- Keep Streamlit listening on `0.0.0.0` inside its container so Docker networking works.
  In local mode publish only `127.0.0.1:8501:8501` on the host.
- In explicit trusted-LAN mode publish `0.0.0.0:8501:8501` on the host.
- Remove the Dockerfile flags that disable Streamlit CORS/XSRF protection and test
  normal same-origin localhost and LAN use. Do not invent an origin allowlist unless
  the pinned Streamlit version exposes a supported configuration that is actually
  required.
- Restrict Windows firewall guidance/scripts to Private profile and LocalSubnet.
- Add health checks for Ollama, Tika, and Streamlit plus readiness-aware dependencies.
- Distinguish service alive, configured model present, model loaded, actual context,
  and expected GPU residency.
- Set one model, one parallel generation, queue depth 4, and default keep-alive 30
  minutes. Allow `-1` only in dedicated-appliance mode.
- Add an app-wide bounded admission gate and clear Busy/Queue Full/503 messages.
- Keep default Ollama/Tika logging disabled.
- Add `docker-compose.diagnostics.yml` with small rotated logs and automation that uses
  `docker compose up -d --force-recreate`, collects capped diagnostics, then restores
  the privacy-default containers. Never ask the owner to hand-edit logging YAML.
- Remove the deployment-guide recommendation to use Windows auto-login as a normal
  appliance solution.

**Explicit non-scope:** TLS proxy, accounts, SSO, Prometheus/Grafana, public-internet
exposure, database queue.

**Acceptance criteria:**

- Local mode is not reachable from another LAN device.
- LAN mode works from a trusted device, including uploads, with CORS/XSRF enabled.
- Firewall rule is not created for Public/Domain networks.
- Busy and missing-model states are distinguishable without exposing technical noise to
  normal users.
- Diagnostic mode yields useful bounded metadata and reliably returns to logs-disabled
  mode.
- No prompt, upload, extracted text, chat, or model response appears in collected logs.

### WP-08 — Curated model profiles and runtime certification

**Objective:** Reach more hardware without exposing novice users to an arbitrary model
picker or unverified VRAM claims.

**Selected approach:** Two public candidates plus an evidence-gated maximum-context
mode.

**Scope:**

- Track profile manifests and Modelfiles in the repository:
  - Standard candidate: Gemma 4 12B, 32K.
  - Extended candidate: Qwen3.6 35B-A3B, 128K.
  - Maximum-context certification: Qwen3.6 35B-A3B, 256K only after an on-machine pass.
- Define model tag, digest/version where possible, vision support, context, KV type,
  parallelism, queue, keep-alive, tested RAM/VRAM, prompt/decode observations, and
  EphemerAl/Ollama versions in each manifest.
- Create a non-interactive provision/verify command using Ollama pull/create/show/ps.
- Recommend Standard below the validated Extended threshold only if Standard has passed
  its own certification. If Extended fails load, context, or offload checks, select a
  certified Standard profile when available; otherwise stop with a plain unsupported
  hardware result rather than substituting an unreviewed model.
- Verify actual `context_length`, `size_vram`, and processor/offload state.
- Benchmark the pinned Ollama 0.21.0 against the current stable 0.31.x candidate. Adopt
  the newer version only if it passes text, vision, thinking-hidden, long-context,
  follow-up-prefix, multi-GPU where available, and error-handling tests.
- Require the Extended profile to analyze a declared-size synthetic transcript of at
  least 100K tokens containing 30 seeded facts, decisions, and actions distributed
  across the beginning, middle, and end. Across three normal-configuration runs, median
  seeded-item recall must be at least 90%, every designated critical item must be
  recovered, and no owner/decision/action may be fabricated. Record the scoring method,
  latency, prompt processing, and failures. Also use a small document/image corpus.

**Explicit non-scope:** Arbitrary model dropdown, CPU support promise, AMD/Intel/Apple
support, vLLM/SGLang, native Ollama client migration.

**Acceptance criteria:**

- At least one public profile completes provisioning and the full functional matrix on
  supported Windows/NVIDIA hardware. The first release may document only capabilities
  of profiles that pass.
- Because long-transcript analysis is a first-release product claim, the Extended
  profile and seeded transcript quality gate must pass before WP-10 can issue GO. If
  that claim is removed in a separately owner-approved product change, a Standard-only
  release may be reconsidered.
- No VRAM/context minimum is published without recorded evidence.
- App and running model report the same context.
- Failed Extended selection cannot leave a half-configured or CPU-offloaded deployment
  presented as healthy.
- 256K remains hidden/advanced unless its specific certification passes.

**Owner hardware gate:** If Codex cannot access suitable hardware, it must return one
complete diagnostic/benchmark script and request only its output. It must interpret the
result and make the pass/fail decision itself.

### WP-09 — Easy Windows distribution and release packaging

**Objective:** Make the supported installation understandable to someone who has never
used Linux.

**Selected approach:** Versioned ZIP plus complete PowerShell lifecycle scripts. Docker
Desktop is the easy path when licensed; current WSL Engine instructions remain advanced.

**Scope:**

- Add idempotent Windows scripts for Install, Start, Stop, Doctor, Update, and Uninstall.
- Provide one browser-downloadable launcher that handles the supported unsigned-script
  flow without globally weakening PowerShell execution policy. Test ZIP Mark-of-the-Web,
  extraction, process-scoped execution, elevation, Windows Defender, and SmartScreen
  behavior. Do not require users to unblock several files manually.
- Detect prerequisites, Docker Desktop/engine state, NVIDIA driver/GPU/VRAM, RAM, disk,
  ports, timezone, and prior installation.
- Ask only plain-language questions:
  - This computer only or trusted local network?
  - Shared/dedicated AI computer or a computer also used for other work/gaming?
- Before recommending Docker Desktop, display the current official license criteria and
  link, then ask one nontechnical self-certification question: “Is Docker Desktop
  approved for this computer under the terms shown?” A Yes answer may use Docker
  Desktop. A No or Unsure answer must use or explain the license-neutral Docker
  Engine-in-WSL path. Default to Unsure. The script must not interpret legal status for
  the user.
- Generate configuration files; never ask the user to edit `.env`, YAML, Modelfiles, or
  firewall rules.
- Recommend and provision a certified model profile with size/progress/resume behavior.
- Use a prebuilt versioned GHCR application image rather than building Python packages
  on the user's machine.
- Add a manually dispatched GitHub Actions workflow named **Publish release** in
  `.github/workflows/release.yml`, but do not run it to publish a real release in this
  package. Its visible inputs must be the version, exact approved `main` release commit
  R, and exact verified `Dev` candidate V. It must refuse an initial publication unless
  current `main` is R, current `Dev` is V, their tree/content matches, the Version input
  exactly matches `.github/release-candidate.json` at R, the version/tag and public
  outputs are unused, and all release tests pass. It then checks out exact R, creates
  the annotated tag at R, and publishes the GHCR image, release ZIP, SHA-256 checksums,
  release notes, and a GitHub release with provenance tied to R.
- Exercise the workflow's same ref/version guards and build/package logic in pull-
  request CI with publication disabled and read-only permissions. This is the WP-09
  non-publishing test path; do not add another owner-facing release input for dry runs.
- A retry after a partial infrastructure failure may continue only when every existing
  tag, image, artifact, or release under that version belongs to the exact same
  version/R/V attempt and matches its recorded provenance. Any mismatch must fail
  closed. If all outputs already exist and verify, the retry must finish as a no-op
  success rather than replacing them.
- Preserve model weights during normal uninstall; remove them only with an explicit
  plain-language `-RemoveModels` option and confirmation.
- Provide a tested update and rollback path.
- Retain and simplify the Docker Engine-in-WSL guide as the advanced/license-neutral
  route. Include the official Docker Desktop license boundary without interpreting a
  user's legal status for them.
- The Docker Desktop easy path must not use `netsh portproxy`. The advanced Docker
  Engine-in-WSL path may retain port forwarding only when testing proves Windows
  localhost or mirrored networking is insufficient on the supported Windows baseline.

**Explicit non-scope:** MSI, code signing, bundled model weights, silent acceptance of
third-party licenses, every Windows edition, other operating systems.

**Acceptance criteria:**

- On a clean supported Windows 11/NVIDIA system, the intended flow is: download ZIP,
  run one launcher, answer plain-language questions, wait for provisioning, use app.
- Re-running Install is safe and resumes rather than corrupting the deployment.
- Doctor provides a useful redacted result without content.
- Start/Stop survive normal reboot/login behavior as documented.
- Update and rollback work; Uninstall removes the app while preserving models by
  default.
- No manual code/YAML/Linux editing is required on the easy path.
- A ZIP downloaded by a normal browser can be launched through the documented single
  entry point without a global execution-policy change.
- The **Publish release** workflow accepts exact version/R/V inputs through GitHub's
  **Run workflow** form, while pull-request CI exercises the same guards and packaging
  logic without write credentials or publication. Initial runs reject moved refs,
  mismatched trees, a version different from the candidate record, reused outputs, or
  failing validation. Safe retries accept only matching partial outputs and emit a
  final summary containing R, V, tag target, image digest, ZIP/checksum identifiers,
  and release URLs.

### WP-10 — Independent release-candidate verification

**Objective:** Produce an evidence-backed GO/NO-GO decision before any public release.

**Scope:**

- Independently test a clean Windows installation, update, rollback, and uninstall.
- Use Windows CI/Pester with mocks for non-GPU lifecycle logic, a disposable Windows
  Sandbox or VM for downloaded-ZIP/launcher/elevation behavior where supported, and a
  scripted uninstall/reinstall from a known clean EphemerAl state on the real NVIDIA
  host. Do not require the owner to wipe or repurpose a personal computer.
- Test every certified profile where hardware is available.
- Test local and trusted-LAN modes.
- Exercise text, PDF, DOCX, XLSX, image, scanned PDF, recursive/container parsing,
  attachment failures, context omission, reset, copy/export, time, busy queue, service
  restart, and diagnostic mode.
- Inspect logs, temporary locations, volumes, and app state for user-content retention.
- Review every user-facing command and link in order.
- Review third-party licenses and model license notices included in the release.
- Recheck production Python dependencies, container/base images, GitHub Actions, model
  licenses, and current security/maintenance status against primary sources. Fix
  material release issues or document a justified, time-bounded exception. Pin GitHub
  Actions immutably where practical.
- Fix only release blockers discovered during verification; record enhancements for
  later rather than expanding scope.

**Acceptance criteria:**

- Produce a GO or NO-GO report with test evidence, remaining limitations, supported
  hardware/profile claims, and exact version recommendation.
- All first-viable-release criteria in Section 4 pass.
- A GO result has two linked durable locations. In the repository, the ledger staged
  on the WP-10 branch names the pull-request number, exact reviewed `Dev` base D, and
  exact reviewed code head A. Final bookkeeping head B adds
  `.github/release-candidate.json` with exactly
  the approved `version`, `wp10_pull_request`, `reviewed_dev_base` D, and
  `reviewed_code_head` A; it does not try to contain its own future B commit ID. The
  final GitHub review submitted against B explicitly states GO and names the same exact
  version, pull-request number, and full D, A, and B commit IDs. After that pull request
  merges, the release-promotion check must obtain B from that GitHub review and verify
  current `Dev` is the pull request's recorded merge result, its tree/content matches
  B, no later commit was added, every completed first-release package is present, and
  no work-package pull request remains open. The release workflow must reject a Version
  input that differs from the candidate record at the exact release commit.
- A release remains unpublished until Prompt 7 has promoted the recorded WP-10 merge
  result from `Dev`—whose tree/content matches the exact approved WP-10 pull-request
  head—to `main`, and the owner then uses Prompt 8's separate publication authorization
  in `CODEX_RUNBOOK.md`.

### WP-11 — Exhaustive long-document overflow mode

**Objective:** When a transcript cannot fit one verified context, process all of it
without similarity ranking or silent omission.

**Release timing:** Post-first-viable-release unless WP-10 finds oversized transcript
handling to be a release blocker.

**Selected approach:** Ordered exhaustive map/reduce in memory.

**Scope:**

- Preserve the existing single-pass full-context path whenever content fits.
- For overflow, process every chronological chunk exactly once or through a documented
  verification pass.
- Extract decisions, actions, owners, dates, risks, unresolved questions, and critical
  numbers with source/chunk references.
- Synthesize from the complete ordered extraction set and disclose the multipass mode.
- Keep all intermediates in memory and clear them on New Chat/session end.
- Add deterministic fake-model tests proving beginning/middle/end coverage and no
  omitted chunks.

**Explicit non-scope:** Embeddings, vector DB, semantic retrieval, persistent summaries,
background workers, parallel GPU calls.

**Acceptance criteria:**

- Every source chunk participates in final synthesis.
- Normal fitting documents retain the direct single-pass behavior.
- Failures identify incomplete chunks rather than presenting a complete result.
- No intermediate is written to disk or included in durable logs.

### WP-12 — Image normalization and non-vision OCR fallback

**Objective:** After the first release, reduce retained image memory and extract local
text from images when the selected model lacks vision.

**Selected approach:** Normalize once with the existing Pillow dependency and use the
local Tika full server as the OCR fallback.

**Scope:**

- Apply EXIF orientation, cap the longest edge at 2048 pixels, and strip metadata.
- Preserve PNG for original PNG/transparency; otherwise encode JPEG at quality 85.
- Store only the normalized representation needed for display and model use, not raw
  plus encoded duplicates.
- When the current model lacks vision, submit the normalized image to local Tika OCR.
  Successful OCR text counts as a `model_available` representation from WP-01 and is
  labeled as extracted image text. Empty/error OCR retains truthful conditional
  unavailability.
- Test screenshots, diagrams, photographs, transparency, orientation, OCR success,
  OCR failure, and New Chat memory release.

**Explicit non-scope:** GPU OCR model, image editor, cloud OCR, background workers,
arbitrary image-quality controls.

**Acceptance criteria:**

- Normalization materially reduces retained bytes without making seeded screenshot and
  photo tasks fail.
- The model never receives both an image and a contradictory vision-unavailable note.
- OCR success/failure is truthful, local, memory-only, and excluded from durable logs.
- New Chat returns retained image/OCR state to baseline.

## 9. Avoid list and evidence-gated watchlist

Do not schedule these before WP-10 unless a current package uncovers a measured blocker:

| Technology/change | Reconsider only when |
|---|---|
| Native Windows executable/MSI | The scripted first release is stable and real users still abandon setup because Docker is the blocker. |
| Microsoft Foundry Local | It supports the certified model/context/vision needs and a single-user rather than LAN-server product direction becomes acceptable. |
| Docker Model Runner | Its model, context, vision, privacy, and Compose behavior match the certified profiles with less operational work. |
| Native Ollama Python client | It demonstrably removes alias/setup complexity while preserving presence-penalty, thinking, vision, streaming, and usage behavior. |
| MarkItDown | A representative corpus materially beats Tika on Office/spreadsheet fidelity and OCR while reducing operations. |
| Kreuzberg | License and maturity concerns resolve and corpus results materially exceed Tika. |
| Docling | Complex PDF layout becomes a demonstrated primary need that justifies its much larger runtime. |
| llama.cpp directly | Ollama becomes the dominant measured operational or performance problem. |
| vLLM/SGLang | Sustained concurrent demand exceeds the serial consumer-GPU profile and Windows/Linux burden is justified. |
| React/FastAPI, Electron, Tauri | Streamlit itself, rather than deployment/model setup, becomes a measured adoption blocker. |
| AMD/Intel/Apple/CPU support | Continuous test hardware and a maintainer-supported profile exist. |
| RAG/vector database | A future use case explicitly prioritizes search over complete transcript fidelity. It must remain opt-in, not replace full-context behavior. |
| Kubernetes, database, accounts, SSO | The product intentionally changes from a small ephemeral appliance to a managed multi-tenant service. |

## 10. Evidence ledger

Agents append one row per implementation or review event. Do not rewrite prior evidence.

| Date | Package | Event/status | Branch, commit, or PR | Validation evidence | Notes/blockers |
|---|---|---|---|---|---|
| 2026-07-10 | Planning | Plan created; no application work started | Baseline `bede6eb` | Repository inspection; Python compilation passed during architecture review; full dependency/GPU tests not run | Fable input reconciled; WP-00 ready |
| 2026-07-17 | Planning | Dev/web workflow clarified; no application work started | `agent/dev-web-workflow` targeting `Dev` | Full planning-document review; branch/reference scan; Markdown and diff validation | `Dev` established as integration branch; browser-only owner workflow and later `Dev`-to-`main` promotion documented; WP-00 remains Ready |

## 11. Primary technical references

These links support the current decisions. Packages depending on rapidly changing
versions must recheck the relevant primary source at implementation time.

- [Codex cloud](https://learn.chatgpt.com/docs/cloud)
- [Codex cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment)
- [Codex repository guidance with `AGENTS.md`](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex code review in GitHub](https://learn.chatgpt.com/docs/third-party/github)
- [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- [Streamlit `st.bottom`](https://docs.streamlit.io/develop/api-reference/layout/st.bottom)
- [Streamlit context](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.context)
- [Streamlit configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)
- [Ollama context guidance](https://docs.ollama.com/context-length)
- [Ollama running-model state](https://docs.ollama.com/api/ps)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama Windows](https://docs.ollama.com/windows)
- [Ollama FAQ: concurrency, keep-alive, and KV cache](https://docs.ollama.com/faq)
- [Apache Tika Server API](https://cwiki.apache.org/confluence/display/TIKA/TikaServer)
- [Official Apache Tika Docker images](https://github.com/apache/tika-docker)
- [Docker Desktop GPU support](https://docs.docker.com/desktop/features/gpu/)
- [Docker Desktop licensing](https://docs.docker.com/subscription/desktop-license/)
- [Docker Compose readiness/startup order](https://docs.docker.com/compose/how-tos/startup-order/)
- [Microsoft WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [Windows Firewall rule guidance](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)
- [Lost in the Middle](https://arxiv.org/abs/2307.03172)
- [RULER](https://arxiv.org/abs/2404.06654)
