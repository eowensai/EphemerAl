# EphemerAl: System Deployment Guide

This guide documents one supported **manual deployment path** (Windows + WSL2 + Docker Compose) and points to automated helpers.

For Linux/macOS Docker Compose users: you can skip WSL-specific steps and follow the same repository setup, profile, model-alias, and doctor workflow.

## Deployment defaults and expectations

- Public default profile: **`qwen3:8b` with 32K context**.
- The high-VRAM **Qwen35/256K** setup is an optional workstation profile, not the universal default.
- Public default model behavior is text-first; document uploads are supported.
- Image analysis requires selecting a **vision-capable model** and setting `LLM_SUPPORTS_VISION` if capability auto-detection is insufficient.

For profile selection and hardware targeting, see [`docs/model-profiles.md`](docs/model-profiles.md). High-VRAM users should review `examples/profiles/high-vram-workstation.env`.

## Related docs (recommended before manual steps)

- Bootstrap: [`docs/bootstrap.md`](docs/bootstrap.md)
- Setup wizard: [`docs/setup-wizard.md`](docs/setup-wizard.md)
- Doctor: [`docs/doctor.md`](docs/doctor.md)
- Configuration: [`docs/configuration.md`](docs/configuration.md)
- Model profiles: [`docs/model-profiles.md`](docs/model-profiles.md)

## 1) Preflight (Windows path)

Open PowerShell and verify:

```powershell
nvidia-smi
wsl --version
```

If WSL is missing, continue to install it.

## 2) Install WSL2 (Windows manual path)

In Administrator PowerShell:

```powershell
wsl --install -d Ubuntu-24.04
```

If needed:

```powershell
wsl --install --web-download -d Ubuntu-24.04
```

Reboot if prompted, then initialize Ubuntu user credentials.

## 3) Install Docker + NVIDIA container toolkit in Ubuntu

Inside Ubuntu:

```bash
cd ~
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y build-essential curl git gpg unattended-upgrades
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Restart shell session, then install/configure NVIDIA container toolkit:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
sudo systemctl restart docker
```

Validate:

```bash
docker run --rm hello-world
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
```

## 4) Clone repository and choose profile

Use the public repository URL for your release. Replace `<PUBLIC_REPO_URL>` with the actual URL:

```bash
git clone <PUBLIC_REPO_URL> ~/ephemeral-llm
cd ~/ephemeral-llm
```

Select and copy a profile `.env` template (see `examples/profiles/` and [`docs/model-profiles.md`](docs/model-profiles.md)).

## 5) Setup workflow (recommended order)

1. Run setup wizard or bootstrap:

```bash
python scripts/setup_wizard.py
# or
bash scripts/bootstrap.sh
```

2. Start stack:

```bash
docker compose up -d --build
```

3. Create/update Ollama alias (primary path):

```bash
bash scripts/create_ollama_model.sh
```

4. Run doctor:

```bash
python scripts/doctor.py
```

5. Open app:

```text
http://localhost:8501
```

## 6) Advanced fallback: manual Modelfile editing

Use this only if the helper script cannot satisfy your custom runtime needs.

- Enter Ollama container.
- Create a deployment profile file (for example under `examples/profiles/`) and keep model settings there rather than direct source edits.
- Run `ollama create <alias> -f <modelfile>`.
- Keep `LLM_MODEL_NAME` aligned with your alias in `.env`.

Profile-driven configuration is preferred over manual per-deployment source changes.

## 7) Optional shared Ollama API exposure

If you intentionally expose Ollama API, use compose overrides and firewall/network controls appropriate to your environment.

Security reminder: raw Ollama exposure does not automatically provide app-layer authentication.

## 8) Troubleshooting

- Use `python scripts/doctor.py` and review [`docs/doctor.md`](docs/doctor.md).
- Inspect service logs:

```bash
docker compose logs ollama
docker compose logs ephemeral-app
docker compose logs tika-server
```

- For profile and hardware tuning guidance, use [`docs/model-profiles.md`](docs/model-profiles.md).
