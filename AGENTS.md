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
- `docker-compose.yml` — Stack definition. Pins Ollama and Tika image versions.
- `Dockerfile` — Builds the Streamlit app container image.
- `requirements.txt` — Python dependencies (installed inside the app container).
- `System Deployment Guide.md` — End-user deployment instructions (target audience: IT
  generalists, not developers). Written for WSL2 + Docker on Windows 11.
- `README.md` — Project overview, feature list, system requirements.
- `system_prompt_template.md` — LLM system prompt template. Includes Gemma 4
  thinking control guidance via the `<|think|>` token in the system prompt.
- `.streamlit/config.toml` — Streamlit theme and config. The Dockerfile merges server
  settings into this file at build time.
- `theme.css` — Custom CSS loaded by the app.
- `static/` — Logo and static assets.

## Conventions
- The deployment guide is written for non-technical IT staff. Use plain language,
  avoid jargon, explain every step, and provide copy-pasteable commands.
- The app runs inside Docker. Environment variable defaults in `ephemeral_app.py` MUST
  use Docker service names (`http://ollama:11434/v1` and `http://tika-server:9998`),
  NOT `localhost`. Using localhost as defaults will break the Docker Compose deployment.
- The default LLM model is `gemma4:31b`. The model tag is set via the
  `LLM_MODEL_NAME` environment variable in `docker-compose.yml`.
- The app detects model capabilities (vision support, context size) at runtime via
  Ollama's `/api/show` endpoint, so it adapts to different models automatically.
- Gemma 4 models may emit thought-channel blocks during streaming in the
  `<|channel>thought\n...<channel|>` format. The app includes a streaming filter
  that strips these, and thinking is controlled by the `<|think|>` token in the
  system prompt.

## Testing
- Verify Python syntax: `python -m py_compile ephemeral_app.py`
- Verify requirements install: `pip install -r requirements.txt && pip check`
- Verify Markdown links resolve: all relative links in README.md and the deployment
  guide should point to files that exist in the repo.
- Full stack test: `docker compose up -d --build` inside WSL2, then access
  `http://localhost:8501`.

## Do Not
- Do not change environment variable defaults in `ephemeral_app.py` to use `localhost`.
  The defaults MUST remain Docker service names for container-to-container communication.
- Do not remove Docker, WSL2, or Linux content from the deployment guide or README.
  That is the supported deployment path.
- Do not modify `system_prompt_template.md` unless changing the LLM's system behavior.
- Do not add new Python dependencies beyond what's in `requirements.txt` without
  documenting the reason.
- Do not remove Gemma 4 thinking guidance from `system_prompt_template.md` or the
  thought-channel streaming filter from `ephemeral_app.py`. Both are required for
  correct Gemma 4 model output (including `<|channel>thought\n...<channel|>` blocks).
