# AGENTS.md

## Project Overview
EphemerAl is a privacy-focused document chat application. It runs as a Docker Compose
stack inside WSL2 (Ubuntu) on Windows. Three containers make up the stack: a Streamlit
frontend, an Ollama LLM backend, and an Apache Tika document parsing server.

## Architecture
- **Streamlit app** (`ephemeral_app.py`): The web frontend. Connects to Ollama and Tika
  via Docker service names over an internal Docker network. Environment variables configure
  the endpoints.
- **Ollama**: Serves the LLM inside a container with GPU passthrough. API on port 11434.
- **Apache Tika Server**: Parses documents inside a container. API on port 9998.
- **Docker Compose** (`docker-compose.yml`): Defines the full stack. Containers communicate
  by Docker service name (`ollama`, `tika-server`) on a shared `llm-net` bridge network.

## Key Files
- `ephemeral_app.py` — Main application. All state is in-memory (session_state).
- `ephemeral/` — Mixed package: pure utility modules (`config`, `export`, `stream_filter`, `token_budget`) are import-safe with no Streamlit dependency, while client modules (`tika_client`, `llm_client`) are Streamlit-aware by design.
- `ephemeral/config.py` — Env parsing helpers and shared configuration constants.
- `ephemeral/export.py` — Conversation transcript/export builders (Markdown/HTML).
- `ephemeral/tika_client.py` — Tika health check and document parsing client helpers.
- `ephemeral/llm_client.py` — Ollama/OpenAI client helpers, model metadata probes, and token counting.
- `ephemeral/stream_filter.py` — Stateful think-block/thought-channel stream filter.
- `ephemeral/token_budget.py` — Token estimation helpers.
- `docker-compose.yml` — Stack definition. Pins Ollama and Tika image versions.
- `Dockerfile` — Builds the Streamlit app container image.
- `requirements.txt` — Python dependencies (installed inside the app container).
- `requirements-dev.txt` — Development-only test dependencies (pytest/coverage).
- `tests/` — Pytest suite for import-safe utility modules.
- `System Deployment Guide.md` — End-user deployment instructions (target audience: IT
  generalists, not developers). Written for WSL2 + Docker on Windows 11.
- `README.md` — Project overview, feature list, system requirements.
- `system_prompt_template.md` — LLM system prompt template. The default template is
  model-agnostic and omits `<|think|>`.
- `.streamlit/config.toml` — Streamlit theme and config. The Dockerfile merges server
  settings into this file at build time.
- `theme.css` — Custom CSS loaded by the app.
- `.gitignore` — Git hygiene for local/dev artifacts (venvs, caches, editor files, secrets).
- `.dockerignore` — Docker build-context hygiene to keep non-runtime files out of images; must not exclude `.streamlit/config.toml`.
- `static/` — Logo and static assets.

## Conventions
- The deployment guide is written for non-technical IT staff. Use plain language,
  avoid jargon, explain every step, and provide copy-pasteable commands.
- The app runs inside Docker. Environment variable defaults in `ephemeral_app.py` MUST
  use Docker service names (`http://ollama:11434/v1` and `http://tika-server:9998`),
  NOT `localhost`. Using localhost as defaults will break the Docker Compose deployment.
- The default LLM model is `ephemeral-default` (`LLM_MODEL_NAME=ephemeral-default` in
  `docker-compose.yml`). The alias should be created from `qwen3.6:35b-a3b`.
- The app detects model capabilities (vision support, context size) at runtime via
  Ollama's `/api/show` endpoint, so it adapts to different models automatically.

## Qwen3.6 Defaults (Target Behavior)
- `Qwen3.6-35B-A3B` is the default target model, exposed through the local Ollama alias
  `ephemeral-default`.
- Run Qwen in **non-thinking mode** by default. EphemerAl request defaults should be:
  - `reasoning_effort="none"`
  - `temperature=0.7`
  - `top_p=0.8`
  - `presence_penalty=1.5`
- The Ollama alias `Modelfile` should define:
  - `PARAMETER num_ctx 262144`
  - `PARAMETER num_predict -1`
  - `PARAMETER temperature 0.7`
  - `PARAMETER top_p 0.8`
  - `PARAMETER top_k 20`
  - `PARAMETER min_p 0`
  - `PARAMETER repeat_penalty 1.0`
- Do **not** put `presence_penalty` in the Modelfile unless the installed Ollama
  version explicitly supports it. Keep `presence_penalty` request-level for EphemerAl
  and OpenAI-compatible clients.

## Context and Output Policy
- `PARAMETER num_ctx` in the alias Modelfile is the source of truth for actual Ollama
  model context.
- `LLM_CONTEXT_TOKENS` is only EphemerAl's document-budgeting hint.
- `OLLAMA_CONTEXT_LENGTH` is not the primary approach for this stack because Ollama may
  become a shared API backend.
- `num_predict -1` avoids an Ollama-side artificial output cap.
- EphemerAl should not send `max_tokens` unless `LLM_MAX_TOKENS` is explicitly set.
- `LLM_OUTPUT_RESERVE_TOKENS` reserves input budget for large responses; it is not an
  output cap.

## Reasoning / Thinking Policy
- Qwen3.6 thinking should be disabled via runtime/API controls, not prompt text.
- Do not add `/nothink`, `<think>`, or "think step by step" to the system prompt.
- EphemerAl should discard streamed reasoning deltas unless
  `LLM_SHOW_REASONING=true`.
- Keep think-block stripping as defense-in-depth.

## Shared API Backend Policy
- Raw Ollama should remain internal by default.
- Optional API exposure should happen via a separate `docker-compose.api.yml`
  override.
- Keep `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL=1` unless capacity testing
  proves otherwise.
- Shared API users should call model `ephemeral-default`.
- External OpenAI-compatible clients should send:
  - `reasoning_effort="none"`
  - `temperature=0.7`
  - `top_p=0.8`
  - `presence_penalty=1.5`

## Review Guidelines
When reviewing Codex changes, treat the following as high-priority checks:
- privacy regressions
- accidental logging of prompts, uploaded documents, or model output
- Docker networking exposure changes
- loss of non-thinking behavior
- incorrect context/output budgeting
- broken copy-paste commands in deployment docs

## Testing
- Verify Python syntax: `python -m py_compile ephemeral_app.py ephemeral/*.py`
- Verify requirements install: `pip install -r requirements.txt && pip check`
- Verify test tooling + run tests: `pip install -r requirements-dev.txt && python -m pytest`
- Verify Markdown links resolve: all relative links in README.md and the deployment
  guide should point to files that exist in the repo.
- Full stack test: `docker compose up -d --build` inside WSL2, then access
  `http://localhost:8501`.
- Keep pure utility modules import-safe (`config`, `export`, `stream_filter`,
  `token_budget`): no Streamlit imports or Streamlit side effects at import time, so
  tests run without Streamlit.
- `ephemeral/tika_client.py` and `ephemeral/llm_client.py` are Streamlit-aware by
  design and may use Streamlit caching decorators/session state.

## Do Not
- Do not change environment variable defaults in `ephemeral_app.py` to use `localhost`.
  The defaults MUST remain Docker service names for container-to-container communication.
- Do not remove Docker, WSL2, or Linux content from the deployment guide or README.
  That is the supported deployment path.
- Do not modify `system_prompt_template.md` unless changing the LLM's system behavior.
- Do not add new Python dependencies beyond what's in `requirements.txt` without
  documenting the reason.
- Do not remove think-block/thought-channel filtering from `ephemeral/stream_filter.py` or from the streaming response path in `ephemeral_app.py`; it is required as defense-in-depth against leaked reasoning output.
