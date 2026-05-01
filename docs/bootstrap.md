# Bootstrap Scripts

Use these scripts for a safe, one-command first run. They validate prerequisites, create `.env` when missing, start the stack, create the model alias, and run the doctor checks.

## What bootstrap does

1. Checks Docker + Docker Compose.
2. Checks Git and Python availability.
3. In interactive mode, optionally runs `scripts/setup_wizard.py` when `.env` is missing.
4. In non-interactive mode (`--yes` / `-Yes`), creates `.env` from `.env.example` safe defaults when missing.
5. Runs `docker compose up -d --build` (CPU-safe default).
6. Runs `scripts/create_ollama_model.sh`.
7. Runs `python scripts/doctor.py`.

Notes:
- The scripts do **not** install Docker, GPU drivers, NVIDIA toolkit, or OS packages.
- Raw Ollama API remains internal by default.
- `OLLAMA_NO_CLOUD=1` remains the default privacy setting.
- Codex web/cloud execution environments may not include the Docker CLI.
- For Compose-related changes, run Docker Compose validation locally or in GitHub Actions before merging.
- `python scripts/validate_compose_static.py` is the Docker-free fallback validator.
- When PowerShell is unavailable in CI/Codex, validate `scripts/bootstrap.ps1` with static contract tests (no `pwsh` runtime required).

## Linux / macOS / WSL

From repository root:

```bash
bash scripts/bootstrap.sh
```

Preview actions without changing anything (side-effect-free; does not create `.env`, start containers, or create Ollama models):

```bash
bash scripts/bootstrap.sh --dry-run
```

Show options:

```bash
bash scripts/bootstrap.sh --help
```

Non-interactive mode (skips setup wizard prompts; creates `.env` from safe defaults if missing):

```bash
bash scripts/bootstrap.sh --yes
```

## Windows / PowerShell

From repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

Preview actions without changing anything (side-effect-free; does not create `.env`, start containers, or create Ollama models):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -DryRun
```

Show options:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Help
```

Non-interactive mode (skips setup wizard prompts; creates `.env` from safe defaults if missing):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Yes
```


## Compose mode by hardware

- CPU / low-end: `docker compose up -d --build`
- GPU / high-VRAM: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`
- High-VRAM profile values are provided in `examples/profiles/high-vram-workstation.env` (including `qwen3.6:35b-a3b`, `LLM_CONTEXT_TOKENS=262144`, `OLLAMA_NUM_CTX=262144`, and `OLLAMA_KV_CACHE_TYPE=q8_0`).
