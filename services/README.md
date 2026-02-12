# EphemerAl Services Reference

This file is a quick reference for the PowerShell scripts in this folder.
For full, step-by-step deployment instructions, use the root [`System Deployment Guide.md`](../System%20Deployment%20Guide.md).

## Scripts in this folder

- `Install-EphemerAlServices.ps1`
  - Installs (or re-installs) three NSSM-managed Windows services:
    - `OllamaService`
    - `TikaService`
    - `EphemerAlApp`
  - Sets each service to automatic startup.
  - Configures `EphemerAlApp` to depend on `OllamaService` and `TikaService`.
  - Starts each service and prints status.
- `Uninstall-EphemerAlServices.ps1`
  - Stops and removes the three NSSM services.
- `Check-EphemerAlServices.ps1`
  - Reports Windows service status.
  - Runs HTTP reachability checks for local endpoints.
  - Reports Streamlit listening address/port guidance for remote access troubleshooting.

## Default paths and how to customize

The install script currently assumes these defaults:

The installer also validates that it can resolve a real Python interpreter (not the Windows Store App Execution Alias shim), checks required files exist, and confirms `streamlit` is importable before creating services.

- Ollama executable: `C:\Ollama\ollama.exe`
- Ollama model directory: `C:\Ollama\models`
- Tika JAR location: `C:\Tika\tika-server-standard.jar`
- Tika working directory: `C:\Tika`
- EphemerAl app path: `C:\EphemerAl\ephemeral_app.py`
- EphemerAl working directory: `C:\EphemerAl`

### Customize by editing the script

`Install-EphemerAlServices.ps1` does not currently expose command-line parameters. To customize paths, edit:

- `$services` entries (`AppPath`, `AppArgs`, `AppDirectory`)
- `$ollamaEnv`, `$tikaEnv`, `$appEnv` values

After changes, run the install script again as Administrator. It removes and re-creates services so updates are applied.

## Change model name or Tika version

### LLM model name

In `Install-EphemerAlServices.ps1`, update this line in `$appEnv`:

- `LLM_MODEL_NAME=gemma3-prod`

Set it to your target local model (for example `LLM_MODEL_NAME=gemma3:12b`).

### Tika version

Update the Tika JAR name/path in `TikaService` `AppArgs`, for example:

- `-jar C:\Tika\tika-server-standard.jar --host 127.0.0.1 --port 9998`

If you install a different Tika release filename, point `-jar` to that exact file.

## Default network binding behavior (security)

By default, `Install-EphemerAlServices.ps1` configures:

- `OllamaService` with `OLLAMA_HOST=127.0.0.1:11434` (localhost only)
- `TikaService` with `--host 127.0.0.1 --port 9998` (localhost only)
- `EphemerAlApp` with Streamlit arguments: `--server.port=8501 --server.address=0.0.0.0 --server.headless=true`

This means:

- Users can access the Streamlit UI from the LAN on port `8501` when firewall rules allow it.
- Ollama and Tika APIs are not exposed on the LAN unless you intentionally reconfigure them.

### Intentionally expose Ollama or Tika on LAN (advanced)

Only do this if you fully trust your network and understand the risk.

- For Ollama, change `OLLAMA_HOST` in `$ollamaEnv` (for example `0.0.0.0:11434`) and reinstall services.
- For Tika, change `--host 127.0.0.1` to `--host 0.0.0.0` in `TikaService` `AppArgs` and reinstall services.
- Keep firewall rules restricted (for example `-Profile Domain,Private`) and open only required ports.

## NSSM log output defaults

The install script now configures logging automatically for all services in `C:\EphemerAl\logs`:

- `C:\EphemerAl\logs\OllamaService.out.log` / `.err.log`
- `C:\EphemerAl\logs\TikaService.out.log` / `.err.log`
- `C:\EphemerAl\logs\EphemerAlApp.out.log` / `.err.log`

It also enables basic rotation controls (`AppRotateFiles=1`, `AppRotateOnline=1`, `AppRotateBytes=10485760`).

If you want custom locations, update them after install with `nssm set <ServiceName> AppStdout <Path>` and `AppStderr <Path>`.

## Add EPHEMERAL_TIMEZONE or EPHEMERAL_DEBUG to Streamlit service

Use NSSM to update `AppEnvironmentExtra` for `EphemerAlApp` as one newline-delimited value in a single `nssm set` call.

1. Inspect current values:

```powershell
nssm get EphemerAlApp AppEnvironmentExtra
```

2. Build a full environment block (existing lines plus new lines) and set it:

```powershell
$envLines = @(
  'LLM_BASE_URL=http://127.0.0.1:11434/v1'
  'LLM_MODEL_NAME=gemma3-prod'
  'TIKA_URL=http://127.0.0.1:9998'
  'TIKA_CLIENT_ONLY=true'
  'EPHEMERAL_TIMEZONE=America/Chicago'
  'EPHEMERAL_DEBUG=1'
)

nssm set EphemerAlApp AppEnvironmentExtra ($envLines -join "`n")
```

Important: include all required existing lines when you run `nssm set`; this replaces the prior `AppEnvironmentExtra` value.

You can also update the `$appEnv` block in `Install-EphemerAlServices.ps1` and rerun install.

## EphemerAl environment variables

| Variable | Description | Default |
|---|---|---|
| `LLM_BASE_URL` | Base URL for OpenAI-compatible Ollama endpoint used by the app. | `http://127.0.0.1:11434/v1` |
| `LLM_MODEL_NAME` | Model name sent in chat requests. | `gemma3-prod` |
| `TIKA_URL` | Apache Tika server endpoint for document parsing. | `http://127.0.0.1:9998` |
| `TIKA_TIMEOUT_S` | Timeout (seconds) for Tika parsing requests. | `15` |
| `TIKA_CLIENT_ONLY` | When true, the Tika Python client skips local JAR startup and uses remote server mode only. | `true` (app default; service script also sets `true`) |
| `DEFAULT_UPLOAD_PROMPT` | Prompt inserted when files are uploaded without text input. | `Please analyze the uploaded files.` |
| `LLM_SUPPORTS_VISION` | Optional override for image capability detection (`true`/`false`). | Not set (auto-detect) |
| `EPHEMERAL_TIMEZONE` | Optional IANA timezone name for app timestamps. | Not set (uses system local timezone) |
| `EPHEMERAL_DEBUG` | Enables debug mode when truthy (`1`, `true`, etc.). | `0` |
| `ENABLE_TOKEN_BUDGETING` | Enables token budgeting/tokenize path unless explicitly disabled. | `1` |

