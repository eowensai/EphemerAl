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

## 📋 System Requirements

This software runs inside a "Linux Subsystem" on Windows (technically called **WSL2**). You do not need to know Linux to install it; simply follow the instructions below.

**OS Requirements:**
* **Supported:** Windows 11 (Pro or Enterprise recommended, Home is supported).
* **Version:** 21H2 or higher (Fully updated).
* *Note: Windows Server 2019/2022 is NOT covered by this specific guide due to installation differences.*

**GPU (important):**
Qwen 3.5 35B is a large model.

- **Recommended:** 32 GB+ total NVIDIA VRAM
- **Works for many users:** 24 GB total VRAM (usually with lower context)
- **Not recommended:** CPU-only for day-to-day interactive usage

---

## Phase 2: Install the Foundation (WSL2)

We need to enable the subsystem that allows Windows to run Linux applications.

1.  Click the **Windows Button**, type in **Powershell** and select **"Run as Administrator"**.
2.  Copy the command below and paste it into PowerShell. Press Enter.
```powershell
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

3.  Copy and paste the second command:
```powershell
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

4.  **Reboot your computer.**
5.  Log back in. Open **PowerShell (Admin)** again.
6.  Install Ubuntu:
```powershell
    wsl --install -d Ubuntu-24.04
```

    > **What happens next:** The installation will proceed **directly inside this PowerShell window**.
    > **Action Required:**
    > * **Username:** It will prompt you to create a user. It generally defaults to your Windows username. You can press **Enter** to accept it, or type a new simple name (e.g., `aiadmin`).
    > * **Password:** Create a secure password. **Write this down.** You will not see stars or dots while typing.
    > * **Completion:** You will see a new command prompt (e.g., `username@Device:/mnt/c...`).
    >


---

## Phase 3: Install the Engine (Docker & NVIDIA)

We will now install the software that manages the AI applications.

> **Concept Check:**
> * **PowerShell:** The standard blue/black Windows terminal.
> * **WSL/Ubuntu:** The Linux environment we enter by typing `wsl`.

1.  Run this command to change directories:
```bash
    cd ~
```

    > **Why cd ~?**
    > By default, you start in the Windows System32 folder (`/mnt/c/Windows...`). This command moves you to your Linux "Home" folder, which is safer for installing software.

2.  Update the system tools. Copy/Paste this into the terminal (enter your password if asked):
```bash
    sudo apt update && sudo apt full-upgrade -y
```

3.  Install required utilities and enable auto-updates:
```bash
    sudo apt install -y build-essential curl unattended-upgrades
```
```bash
    sudo dpkg-reconfigure -plow unattended-upgrades
```

    > **Attention:** A pink/blue screen will pop up.
    > Ensure **Yes** is highlighted and press **Enter**. This ensures Linux will automatically install important security updates in the background.

4.  Install Docker (The container system):
```bash
    curl -fsSL https://get.docker.com | sudo sh
```

5.  Enable Docker and add permissions:
```bash
    sudo systemctl enable --now docker
```
```bash
    sudo usermod -aG docker $USER
```

    > **Refresh Permissions:**
    > We need to log out and back in for the group change to take effect.
    > 1. Type `exit` and press **Enter**. *(You drop back to PowerShell)*.
    > 2. Type `wsl` and press **Enter**. *(You enter Ubuntu again)*.
    > 3. Type `cd ~` and press **Enter**. *(Return to your home folder)*.

6.  Install the NVIDIA Toolkit (Allows AI to see your GPU). Run these 3 commands one by one:
```bash
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```
```bash
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```
```bash
    sudo apt update && sudo apt install -y nvidia-container-toolkit
```

7.  Configure Docker for GPU access and Log Rotation (Prevents disk usage issues). Copy this entire block and paste it:
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
```

8.  Restart the engine:
```bash
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
