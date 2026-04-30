# Doctor Health Check (`scripts/doctor.py`)

Use the doctor command to run a fast, plain-language validation of an EphemerAl deployment:

```bash
python scripts/doctor.py
```

The command is designed for operators and public users who want a quick signal that local runtime prerequisites and deployment settings are in a healthy state.

## What `scripts/doctor.py` checks

The script runs a set of installation/runtime checks and prints a status line for each one, including what was found and suggested remediation.

Current checks include:

- Python version and required project files.
- `.env` presence and parseability for key values such as `APP_PORT`.
- Docker and Docker Compose availability.
- `docker compose ps` status visibility.
- App reachability at configured bind address and port.
- Tika service running status.
- Ollama container running status.
- Presence of configured model alias (for example `LLM_MODEL_NAME=ephemeral-default`) inside Ollama.
- Ollama runtime status (`ollama ps` inside the container).
- Context alignment between app-side budgeting (`LLM_CONTEXT_TOKENS`) and runtime context (`OLLAMA_NUM_CTX`).
- GPU visibility inside Ollama container (`nvidia-smi`).
- Raw Ollama API exposure risk (for broad `11434` exposure).
- Ollama cloud/privacy mode (`OLLAMA_NO_CLOUD`).

## When to run it

Run doctor:

- After initial setup.
- After changing `.env`, model aliases, context settings, or Compose overrides.
- After upgrading Docker, Ollama, or GPU/container runtime components.
- During troubleshooting when users report app/backend connectivity issues.

## Status meanings: PASS, WARN, FAIL

- **PASS**: Check looks healthy for expected default deployment behavior.
- **WARN**: Non-ideal or unverified condition. App may still work, but you should review whether the warning is expected for your deployment.
- **FAIL**: Blocking issue likely to break core functionality and should be fixed first.

A warning is not always a hard error. For example, **GPU visibility WARN can be acceptable** for CPU-only deployments or environments where GPU acceleration is intentionally not configured.

## Privacy and inspection behavior

Doctor output is intended to be safe for troubleshooting:

- It **redacts secret-like values** in check output (for keys/names that look like secrets, tokens, passwords, API keys, credentials, etc.).
- It evaluates configuration/runtime state only and **does not inspect uploaded document contents**.

## Example output snippets

These snippets are abbreviated examples to help interpret results.

### 1) Healthy default deployment

```text
EphemerAl Doctor — Installation & Runtime Health
======================================================
✅ PASS  Python and required files
✅ PASS  .env presence and parseability
✅ PASS  Docker availability
✅ PASS  Docker Compose availability
✅ PASS  Tika service status
✅ PASS  Ollama container status
✅ PASS  Ollama model alias
✅ PASS  Context configuration alignment
✅ PASS  Raw Ollama API exposure
✅ PASS  Ollama cloud privacy
```

### 2) Docker not available

```text
❌ FAIL  Docker availability
  What we found: docker command not found.
  How to fix: Install Docker Engine/Desktop and ensure it is running.

⚠️ WARN  Docker Compose availability
  What we found: docker compose unavailable.
```

### 3) Ollama container running but model alias missing

```text
✅ PASS  Ollama container status
⚠️ WARN  Ollama model alias
  What we found: Looking for model alias `ephemeral-default`.
  How to fix: Create/pull the model alias (see README create_ollama_model script).
```

### 4) Context mismatch (`LLM_CONTEXT_TOKENS` vs `OLLAMA_NUM_CTX`)

```text
⚠️ WARN  Context configuration alignment
  What we found: Context mismatch: app budget LLM_CONTEXT_TOKENS=131072, runtime OLLAMA_NUM_CTX=262144.
  How to fix: Align LLM_CONTEXT_TOKENS with OLLAMA_NUM_CTX for predictable truncation behavior.
```

### 5) Raw Ollama API exposed broadly

```text
⚠️ WARN  Raw Ollama API exposure
  What we found: Potential broad exposure of port 11434 detected.
  How to fix: Avoid exposing raw Ollama publicly; keep it internal or front it with authenticated proxy.
```

### 6) `OLLAMA_NO_CLOUD` disabled

```text
⚠️ WARN  Ollama cloud privacy
  What we found: OLLAMA_NO_CLOUD is explicitly disabled.
  How to fix: Set OLLAMA_NO_CLOUD=1 unless you explicitly want cloud features.
```

