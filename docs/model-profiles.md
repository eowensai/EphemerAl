# Model profiles and local alias setup

This repository includes ready-to-copy `.env` model profiles for common hardware tiers.

## Profiles

- `examples/profiles/low-end-laptop.env`
  - Text-only profile tuned for low memory usage and stability.
  - Uses `llama3.2:3b` and an `8192` context budget.
  - This is optimized for constrained hardware, not maximum output quality.
- `examples/profiles/midrange-gpu.env` (public default)
  - Text-only default for most users.
  - Uses `qwen3:8b` with `32768` context.
  - Image upload requires a vision-capable model; `qwen3:8b` default here is text-only.
- `examples/profiles/high-vram-workstation.env`
  - Reproduces current high-resource behavior with `qwen3.6:35b-a3b` and large context.

## Compose mode selection

- **CPU / low-end path (default):**

```bash
docker compose -f docker-compose.yml up -d --build
```

- **GPU path (explicit override):**

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

- **High-VRAM path:** use `examples/profiles/high-vram-workstation.env` plus the GPU override above to preserve the 35B/256K/Q8 settings.

## Quick start

From repository root:

```bash
cp examples/profiles/midrange-gpu.env .env
bash scripts/create_ollama_model.sh --dry-run
docker compose up -d --build
bash scripts/create_ollama_model.sh
```

`--dry-run` works before Docker and previews resolved settings only. Real alias creation requires the Ollama container to be running.

Swap `midrange-gpu.env` for another profile if needed.

For low-end installs, combine `low-end-laptop.env` with base Compose only (no GPU override).

## Alias behavior: `LLM_MODEL_NAME` vs `OLLAMA_MODEL_SOURCE`

- `OLLAMA_MODEL_SOURCE` is the upstream/source model tag in Ollama (for example `qwen3:8b`).
- `LLM_MODEL_NAME` is the local alias name your app calls (default `ephemeral-default`).
- `scripts/create_ollama_model.sh` creates/recreates `LLM_MODEL_NAME` from `OLLAMA_MODEL_SOURCE` with configured runtime parameters.

## Context behavior: `LLM_CONTEXT_TOKENS` vs `OLLAMA_NUM_CTX`

- `OLLAMA_NUM_CTX` is written into the generated Modelfile (`PARAMETER num_ctx ...`) and controls Ollama context allocation.
- `LLM_CONTEXT_TOKENS` is app-side context budgeting.
- Keep them aligned to avoid UI budgeting that exceeds runtime context.

Why `8192` on the low-end profile even if some model pages advertise larger windows?
- Larger context windows significantly increase memory demand and can degrade responsiveness on lower-memory systems.
- `8192` is a safer baseline for non-expert deployments on constrained hardware.

## Presence penalty note

`LLM_PRESENCE_PENALTY` remains request-level by default. Ollama Modelfile parameter support can vary by version; keeping presence penalty at request-level avoids relying on version-specific Modelfile behavior.

## Vision-model note

Image support requires selecting a vision-capable model and setting compatible app/runtime options. The public default profile (`qwen3:8b`) is intentionally text-only.
