# EphemerAl: Local document + image chat with Ollama

EphemerAl is a lightweight, privacy-focused Streamlit chat UI for local LLM use. It runs with Ollama for model inference and Apache Tika for document parsing.

The repository now targets **Qwen 3.5 35B** on Ollama as the default model, using the explicit tag:

- `qwen3.5:35b-a3b`

You can still retarget to another Ollama model by changing one environment variable (`LLM_MODEL_NAME`).

[View the source code on GitHub](https://github.com/eowensai/EphemerAl)

![A screenshot of EphemerAl, a self-hosted AI assistant for local document Q&A and image analysis using Ollama](Ephemeral%20Screenshot.jpg)

---

## Core Features

- **Local AI chat:** Real-time chat against a local Ollama model.
- **Document ingestion:** Upload PDFs, Office docs, text files, and more (via Apache Tika).
- **Image + text chat:** If your selected model supports vision, image uploads are included in the request automatically.
- **Streaming responses:** Assistant output streams token-by-token.
- **Ephemeral by default:** Conversation state is in-memory for the session; no app-level database.
- **Token/context safeguards:** The app estimates prompt size and drops overflowing attachments before request failure where possible.

## Default Model and Retargeting

### Default target

- **Model:** Qwen 3.5 35B
- **Ollama tag:** `qwen3.5:35b-a3b`

### Retarget to a different model

Set `LLM_MODEL_NAME` to any available Ollama model tag or local alias:

- Docker Compose: edit `docker-compose.yml`
- Native/service deployment: set environment variable for the app service

The app performs model capability/context detection at runtime via Ollama (`/api/show`) so behavior remains adaptive across models.

## Privacy Notes

- **No database:** Conversations live in Streamlit memory (`st.session_state`) and are not persisted by this app.
- **Session-scoped parsing cache:** Parsed document text is cached per session only.
- **Container tmpfs:** In Docker deployment, `/tmp` for app/Tika is RAM-backed.
- **Optional log suppression:** Container logs can be disabled in `docker-compose.yml`.

## Technical Stack

- Python 3.11 + Streamlit
- Ollama API (OpenAI-compatible endpoint for chat)
- Apache Tika server
- Docker Compose (for the included deployment path)
- Pinned Ollama container image in compose: `ollama/ollama:0.20.2`

## Hardware Planning (honest baseline)

Qwen 3.5 35B is substantially heavier than small local models.

- **Recommended:** 32 GB+ total VRAM.
- **Works for many users:** 24 GB total VRAM (usually with lower context).
- **CPU-only fallback:** technically possible in some setups but usually too slow for interactive use.

If this model is too heavy for your machine, use a smaller Ollama model tag in `LLM_MODEL_NAME`.

## Deployment

Use the step-by-step guide:

- [System Deployment Guide](System%20Deployment%20Guide.md)

### Migrating an existing Gemma-based install

If your current stack still points at `gemma3-prod` (or another Gemma tag), use the migration section in the deployment guide to switch to either:

- `LLM_MODEL_NAME=qwen3.5:35b-a3b` directly, or
- a neutral local alias like `ephemeral-default` that maps to `qwen3.5:35b-a3b`.

## Accessing EphemerAl

- Local: `http://localhost:8501`
- Network: `http://<host-ip>:8501`

## Support

This project is shared as-is for local/private AI use cases.

If you run into issues, gather logs and screenshots and verify model availability in Ollama first.

## License

MIT (for the parts of this repository authored by the project owner).
