# AGENTS.md

## Project Overview
EphemerAl is a privacy-focused document chat application. It runs a Streamlit frontend
that connects to an Ollama LLM backend and an Apache Tika document parsing server.
All three services run natively on Windows (no Docker, no WSL).

## Architecture
- **Streamlit app** (`ephemeral_app.py`): The web frontend. Connects to Ollama and Tika
  via HTTP on localhost. Environment variables configure the endpoints.
- **Ollama**: Serves the LLM. Runs natively on Windows with GPU support. API on port 11434.
- **Apache Tika Server**: Parses documents. Runs as a Java JAR. API on port 9998.
- **All three run as Windows services via NSSM** (Non-Sucking Service Manager) to survive
  reboots without requiring user login.

## Key Files
- `ephemeral_app.py` — Main application. All state is in-memory (session_state).
- `requirements.txt` — Python dependencies.
- `System Deployment Guide.md` — End-user deployment instructions (target audience: IT
  generalists, not developers).
- `system_prompt_template.md` — LLM system prompt template.
- `.streamlit/config.toml` — Streamlit theme/config.
- `theme.css` — Custom CSS.
- `static/` — Logo and static assets.
- `services/` — PowerShell scripts for Windows service management.

## Conventions
- The deployment guide is written for non-technical IT staff. Use plain language,
  avoid jargon, explain every step, and provide copy-pasteable commands.
- Python code should work on Windows natively (no Linux-only paths or commands).
- Environment variable defaults in ephemeral_app.py should point to localhost, not
  Docker container names.
- PowerShell scripts should be compatible with PowerShell 5.1+ (ships with Windows).

## Testing
- Verify Python syntax: `python -m py_compile ephemeral_app.py`
- Verify PowerShell syntax: `powershell -Command "Get-Content services/*.ps1 | Out-Null"`
- Verify Markdown renders correctly (no broken links or formatting).

## Do Not
- Do not introduce Docker, WSL, or Linux dependencies.
- Do not modify `system_prompt_template.md` or `theme.css` (unless fixing Windows
  path compatibility).
- Do not add new Python dependencies beyond what's in requirements.txt.
