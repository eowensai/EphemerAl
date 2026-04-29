# AGENTS.md

## Project Overview
EphemerAl is a privacy-focused document chat application. It is typically run as a
Docker Compose stack with three services: a Streamlit frontend, an Ollama LLM backend,
and an Apache Tika document parsing server.

## Architecture
- **Streamlit app** (`ephemeral_app.py`): Web frontend. Connects to Ollama and Tika via
  Docker service names over an internal Docker network. Environment variables configure
  the endpoints.
- **Ollama**: Serves local LLM APIs (OpenAI-compatible endpoint and Ollama-native APIs).
- **Apache Tika Server**: Parses uploaded documents through HTTP.
- **Docker Compose** (`docker-compose.yml`): Defines the stack. Containers should
  communicate by Docker service name (`ollama`, `tika-server`) on a shared network.

## Key Files
- `ephemeral_app.py` — Main application. Session state is in-memory.
- `ephemeral/` — Mixed package: pure utility modules (`config`, `export`,
  `stream_filter`, `token_budget`) are import-safe with no Streamlit dependency, while
  client modules (`tika_client`, `llm_client`) are Streamlit-aware by design.
- `ephemeral/config.py` — Env parsing helpers and shared configuration constants.
- `ephemeral/export.py` — Conversation transcript/export builders (Markdown/HTML).
- `ephemeral/tika_client.py` — Tika health check and document parsing helpers.
- `ephemeral/llm_client.py` — Ollama/OpenAI client helpers, metadata probes, token counting.
- `ephemeral/stream_filter.py` — Stateful think-block/thought-channel stream filter.
- `ephemeral/token_budget.py` — Token estimation helpers.
- `docker-compose.yml` — Stack definition and service wiring.
- `Dockerfile` — Streamlit app container image build.
- `requirements.txt` — Production/runtime dependencies.
- `requirements-dev.txt` — Development/test dependencies.
- `tests/` — Pytest suite.
- `README.md` — Public project overview and setup guidance.
- `System Deployment Guide.md` — Deployment guide.
- `system_prompt_template.md` — Base system prompt template.
- `.streamlit/config.toml` — Streamlit theme/config.
- `theme.css` — Custom CSS.

## Public-Generalization Rules
- Keep this repository public-ready: do not add organization-specific names, internal
  systems, employee identities, personal profile links, internal URLs, private emails,
  or customer references to tracked files.
- Deployment customization should be done through `.env`/config values, documented
  scripts, or sample profiles—not by hard-coding source edits for one environment.
- Prefer small, focused changes.
- Do not add new production dependencies unless absolutely necessary and justified.
- If a validation command cannot run because a dependency/tool is unavailable in the
  Codex environment, report that explicitly instead of silently skipping it.

## Runtime and Branding Targets
- Target runtime is Python 3.10+.
- Streamlit migration target is 1.56.0 for UI work.
- Branding is configuration-driven via:
  - `APP_DISPLAY_NAME`
  - `APP_SUBTITLE`
  - `APP_LOGO_PATH`
  - `APP_EXPORT_TITLE`
- In-repo defaults intentionally use **EphemerAI** as the product brand, but deployments
  are expected to override branding via environment/config.

## Streamlit 1.56 UI Guidance
- `st.set_page_config(initial_sidebar_state=304)` is valid in Streamlit 1.56 and should
  be used when a 304px default sidebar is needed while preserving auto behavior.
- `st.chat_message(..., width="stretch")` is valid in Streamlit 1.56; `"stretch"` is
  also the default.
- `st.chat_input(..., height=68, max_upload_size=50)` is valid in Streamlit 1.56. Keep
  Python-side upload size validation as defense-in-depth.
- Prefer `st.iframe` over `streamlit.components.v1.html`/`components.html` for the
  sidebar copy button behavior.
- Do not adopt `st.container(autoscroll=True)` unless chat history is moved into a
  fixed-height container.

## CSS and UI Constraints
- Preserve `theme.css` `:root` custom-property architecture.
- Preserve `st-key-{role}-` message wrapper patterns for user/assistant styling.
- No external fonts, web fonts, CDNs, or externally loaded assets.
- Use a system font stack and standard font weights: 400, 500, 600, 700, 800.
- CSS targeting Streamlit internals, `data-testid`, or generated DOM is brittle; add
  comments on selectors that are new/changed for Streamlit 1.56.
- Keep **New chat** and **Copy conversation** visible in the sidebar.

## Model and Hardware Profiles
- The repository is mid-generalization: model/runtime defaults are moving to profile
  files and docs.
- Source of truth for deployment model defaults should be:
  - `examples/profiles/*.env` (upcoming)
  - `docs/model-profiles.md` (upcoming)
- Treat model selection, context windows, sampling settings, and hardware sizing as
  profile-driven configuration (for example, high-VRAM profiles vs lower-resource
  profiles), not immutable hard-coded assumptions.
- Keep raw Ollama internal by default; optional external API exposure should be handled
  via compose overrides or documented deployment profiles.

## Privacy and Security Invariants
- Do not persist prompts, uploaded files, parsed document text, or model output to disk.
- Do not log chat content, uploaded document content, or model output.
- Keep think-block/thought-channel filtering in streaming paths as defense-in-depth.
- Maintain safe Docker networking defaults; avoid unnecessary backend exposure.

## Configuration and Context Policy
- Docker default service endpoints must remain valid for Compose deployments:
  - Ollama: `http://ollama:11434/v1`
  - Tika: `http://tika-server:9998`
- Keep these as defaults in `ephemeral/config.py` unless explicitly requested otherwise.
- Keep pure utility modules import-safe (`config`, `export`, `stream_filter`,
  `token_budget`): no Streamlit imports or side effects at import time.

## Review Guidelines
When reviewing changes, treat these as high-priority checks:
- privacy regressions
- accidental logging of prompts/uploads/model output
- Docker networking exposure changes
- reasoning-leak regressions in streaming output filtering
- incorrect context/output budgeting behavior
- broken copy-paste commands in deployment docs
- Streamlit 1.56 compatibility regressions

## Testing
Core validation from repository root:
1. `python -m pytest -q`
2. `pytest -q`
3. `python -m py_compile ephemeral_app.py ephemeral/*.py`
4. `ruff check .`

Optional validations:
- `bash scripts/validate.sh`
- `python scripts/ui_smoke.py`
- `bash scripts/validate_ui.sh`

Notes:
- UI smoke testing depends on Playwright Python package and an installed Chromium browser.
- UI screenshots under `artifacts/ui-smoke/` are test artifacts and should not be
  committed unless explicitly requested.
- If browser automation is unavailable in the current environment, report it clearly as
  a manual validation gap.

## Do Not
- Do not change Docker default service-name endpoints to localhost in
  `ephemeral/config.py`; that breaks container-to-container communication.
- Do not remove privacy protections around streamed reasoning filtering.
- Do not persist or log sensitive chat/document/model content.
- Do not introduce environment-specific hard-coding when config-driven options are
  available.
