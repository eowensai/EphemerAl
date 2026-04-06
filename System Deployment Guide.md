# EphemerAl: System Deployment Guide (Ollama Qwen 3.5 35B Default)

This guide is written for IT generalists and focuses on copy/paste steps.

---

## 📋 What this guide installs

You will install:
- Docker (inside WSL2 Ubuntu)
- Ollama container
- Apache Tika container
- EphemerAl Streamlit app container
- The default Ollama model: `qwen3.5:35b-a3b`

---

## 1) System requirements

### Windows
- Windows 11 (fully updated)
- Administrator access

### GPU (important)
Qwen 3.5 35B is a large model.

- **Recommended:** 32 GB+ total NVIDIA VRAM
- **Works for many users:** 24 GB total VRAM (usually with lower context)
- **Not recommended:** CPU-only for day-to-day interactive usage

---

## 2) Install WSL2 + Ubuntu

Open **PowerShell as Administrator** and run:

```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

Reboot Windows, then run:

```powershell
wsl --install -d Ubuntu-24.04
```

Create your Linux username/password when prompted.

---

## 3) Install Docker + NVIDIA container toolkit in Ubuntu

Open Ubuntu (`wsl`) and run:

```bash
cd ~
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y build-essential curl unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Log out and back into Ubuntu:

```bash
exit
```

Then open `wsl` again and run:

```bash
cd ~
```

Install NVIDIA toolkit:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
```

Set Docker runtime + log rotation:

```bash
sudo tee /etc/docker/daemon.json > /dev/null <<EOF_DAEMON
{
  "default-runtime": "nvidia",
  "runtimes": { "nvidia": { "path": "/usr/bin/nvidia-container-runtime", "runtimeArgs": [] } },
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
EOF_DAEMON
sudo systemctl restart docker
```

---

## 4) Deploy EphemerAl stack

```bash
git clone https://github.com/eowensai/EphemerAl.git ~/ephemeral-llm
cd ~/ephemeral-llm
docker compose up -d --build
```

> This repo pins Ollama to `ollama/ollama:0.20.2` in `docker-compose.yml` to keep compatibility with current `qwen3.5` tags predictable.

---

## 5) Pull and configure the default model (Qwen 3.5 35B)

### Step A: Pull the model

```bash
docker exec -it ollama ollama pull qwen3.5:35b-a3b
```

### Step B: (Optional but recommended) Create a neutral local alias

Why: if upstream tags change later, you only update one alias.

```bash
docker exec -it ollama bash
cat > Modelfile <<EOF_MODEL
FROM qwen3.5:35b-a3b
PARAMETER num_ctx 32768
PARAMETER num_gpu 99
PARAMETER temperature 0.7
PARAMETER top_p 0.9
SYSTEM "You are a helpful assistant. /no_think"
EOF_MODEL
ollama create ephemeral-default -f Modelfile
exit
```

If you create this alias, set app model name to `ephemeral-default`:

```bash
sed -i 's#LLM_MODEL_NAME=qwen3.5:35b-a3b#LLM_MODEL_NAME=ephemeral-default#' docker-compose.yml
docker compose up -d
```

> Context note: `num_ctx 32768` is a practical starting point for many 24–32 GB setups. Increase only if performance and VRAM headroom allow.

---

## 6) Open the app

- Local machine: `http://localhost:8501`
- LAN users: `http://<windows-host-ip>:8501`

---

## 7) Migration from existing Gemma-based installs

If your current setup uses a Gemma alias such as `gemma3-prod`, migrate with these steps.

### Option 1 (fastest): switch app directly to Qwen tag

```bash
cd ~/ephemeral-llm
docker exec -it ollama ollama pull qwen3.5:35b-a3b
sed -i 's#LLM_MODEL_NAME=gemma3-prod#LLM_MODEL_NAME=qwen3.5:35b-a3b#' docker-compose.yml
docker compose up -d
```

### Option 2 (recommended): adopt neutral alias and keep config stable

```bash
cd ~/ephemeral-llm
docker exec -it ollama ollama pull qwen3.5:35b-a3b
docker exec -it ollama bash
```

Then inside the container:

```bash
cat > Modelfile <<EOF_MODEL
FROM qwen3.5:35b-a3b
PARAMETER num_ctx 32768
PARAMETER num_gpu 99
PARAMETER temperature 0.7
PARAMETER top_p 0.9
SYSTEM "You are a helpful assistant. /no_think"
EOF_MODEL
ollama create ephemeral-default -f Modelfile
exit
```

Back on Ubuntu:

```bash
sed -i 's#LLM_MODEL_NAME=gemma3-prod#LLM_MODEL_NAME=ephemeral-default#' docker-compose.yml
docker compose up -d
```

### (Optional) remove old Gemma model to free space

```bash
docker exec -it ollama ollama rm gemma3:12b-it-qat gemma3:27b-it-qat gemma3-prod
```

Only remove old models after confirming the new setup is working.

---

## 8) Basic health checks

Run these in `~/ephemeral-llm`:

```bash
docker compose ps
docker exec -it ollama ollama list
curl -s http://localhost:11434/api/tags
curl -s http://localhost:9998/version
```

You should see:
- all 3 containers running
- `qwen3.5:35b-a3b` (or your alias) listed in Ollama
- JSON from Ollama tags
- a version string from Tika

---

## 9) Troubleshooting quick wins

- If app responds but ignores images: your selected model may not expose vision capability in Ollama metadata.
- If replies are very slow: lower `num_ctx` in your Modelfile alias and recreate model.
- If model fails to load: confirm NVIDIA drivers and toolkit installation, then restart Docker.
