# Bootstrap Scripts

Use these scripts for a safe, one-command first run. They validate prerequisites, create `.env` when missing, start the stack, create the model alias, and run the doctor checks.

## What bootstrap does

1. Checks Docker + Docker Compose.
2. Checks Git and Python availability.
3. Optionally runs `scripts/setup_wizard.py` when `.env` is missing.
4. Otherwise copies `.env.example` to `.env` and prompts you to review values.
5. Runs `docker compose up -d --build`.
6. Runs `scripts/create_ollama_model.sh`.
7. Runs `python scripts/doctor.py`.

Notes:
- The scripts do **not** install Docker, GPU drivers, NVIDIA toolkit, or OS packages.
- Raw Ollama API remains internal by default.
- `OLLAMA_NO_CLOUD=1` remains the default privacy setting.

## Linux / macOS / WSL

From repository root:

```bash
bash scripts/bootstrap.sh
```

Preview actions without changing anything:

```bash
bash scripts/bootstrap.sh --dry-run
```

Show options:

```bash
bash scripts/bootstrap.sh --help
```

Non-interactive mode:

```bash
bash scripts/bootstrap.sh --yes
```

## Windows / PowerShell

From repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

Preview actions without changing anything:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -DryRun
```

Show options:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Help
```

Non-interactive mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Yes
```
