# Setup Wizard (`scripts/setup_wizard.py`)

The setup wizard provides a lightweight, line-oriented terminal flow for first-time setup.
It is intended for users who can run commands and prefer profile-driven configuration rather than direct source changes.

## What it does

- Detects platform context (Linux/macOS/Windows/WSL/PowerShell where detectable).
- Checks Docker and Docker Compose availability.
- Attempts safe NVIDIA detection (`nvidia-smi`, then Docker runtime probe) with graceful fallback.
- Lets you choose a profile template from `examples/profiles/*.env`:
  - low-end-laptop
  - midrange-gpu (default in most cases)
  - high-vram-workstation
  - custom/manual
- Prompts for common settings:
  - `APP_DISPLAY_NAME`
  - `APP_PORT`
  - `LLM_MODEL_NAME`
  - `OLLAMA_MODEL_SOURCE`
  - `LLM_CONTEXT_TOKENS` / `OLLAMA_NUM_CTX`
  - raw Ollama API exposure toggle (default: no)
  - `OLLAMA_NO_CLOUD` privacy toggle (default: yes / `1`)
- Validates obvious mistakes (numeric port/context, required model fields).
- Protects existing `.env` files with overwrite confirmation and timestamped backup.
- Optionally runs common follow-up commands with explicit per-command confirmation:
  - `docker compose up -d --build`
  - `bash scripts/create_ollama_model.sh`
  - `python scripts/doctor.py`

## Usage

```bash
python scripts/setup_wizard.py
```

Help:

```bash
python scripts/setup_wizard.py --help
```

## Notes

- The wizard does not make live network calls by itself.
- Service-start/model-download actions happen only if you approve the optional commands.
- The midrange profile default uses `qwen3:8b`, which is text-only (not a vision model).
