# EphemerAl: System Deployment Guide

**Default model: Qwen3.6-35B-A3B via local alias `ephemeral-default`**

This guide walks you through a complete installation of EphemerAl on a Windows 11 machine with an NVIDIA GPU. Every step is designed for copy-and-paste; no Linux experience is required.

When you are finished, you will have four things running inside a Linux subsystem on your Windows PC:

- **Docker**, the container engine that manages the other three components.
- **Ollama**, the service that runs the AI model on your GPU.
- **Apache Tika**, a document parser that lets the AI read uploaded files (PDFs, Word docs, spreadsheets, and more).
- **EphemerAl**, the web-based chat interface your users will open in a browser.


## System Requirements

**Operating system:** Windows 11 (Pro or Enterprise recommended, Home is supported), version 21H2 or higher, fully updated. Windows Server is not covered by this guide.

**GPU target:** This deployment targets **32 GB total NVIDIA VRAM**, including setups like **2 x 16 GB GPUs**.

- The expected target configuration is **256K context** (`num_ctx 262144`) using Qwen3.6 with q8 KV cache.
- This is a practical target, not a guarantee. Real behavior depends on your GPU model(s), driver version, CUDA/container stack, and concurrent GPU usage.
- After deployment, always verify the actual runtime state with `ollama ps`.
- Only reduce context size if `ollama ps` shows CPU offload, if you hit out-of-memory behavior, or if latency becomes unacceptable.
- CPU-only is technically possible but far too slow for interactive use.

**NVIDIA Driver:** Install the latest WHQL-certified driver from NVIDIA's website before proceeding. If your PC has both integrated graphics and a discrete NVIDIA card, connecting your monitor to the integrated output can leave more VRAM available for AI workloads.


## Preflight Checks

Before entering Linux, confirm two things from the Windows side.

**1. Verify your NVIDIA driver is working.** Open PowerShell (regular, not Admin) and run:

```powershell
nvidia-smi
```

You should see a table with your GPU name, driver version, and VRAM. If this command is not recognized or shows an error, install or update your NVIDIA driver before continuing.

**2. Check your WSL version** (if WSL is already installed). Run:

```powershell
wsl --version
```

If WSL is not installed yet, this will show an error or help text; that is fine, the next step installs it. If WSL is installed, confirm the output shows WSL version 2.x. If it shows version 1, you will need to update.


## Step 1: Install the Linux Subsystem (WSL2)

Windows can run a full Linux environment alongside your desktop through a feature called WSL2 (Windows Subsystem for Linux). This is where all of the AI software will live.

1. Click the **Windows button**, type **PowerShell**, and choose **Run as Administrator**.

2. Run this command, which enables the required Windows features and installs Ubuntu in a single step:

```powershell
wsl --install -d Ubuntu-24.04
```

If the install appears stuck at 0%, try the web-download variant instead:

```powershell
wsl --install --web-download -d Ubuntu-24.04
```

3. **Reboot when prompted.** WSL may ask you to restart to finish enabling background features.

4. After rebooting, Ubuntu should open automatically (or you can launch it from the Start menu). It will ask you to create a Linux username and password:

   - **Username:** You can press Enter to accept the default (usually your Windows username), or type something short like `aiadmin`.
   - **Password:** Choose something you will remember and write it down. You will need it occasionally for install commands. The terminal will not show any characters while you type the password; this is normal.

When you see a prompt that looks like `username@YOURPC:~$`, Ubuntu is ready.

**Verify WSL2 is active.** Switch back to PowerShell (Admin) and run:

```powershell
wsl -l -v
```

You should see `Ubuntu-24.04` listed with VERSION 2. If it shows version 1, upgrade it with `wsl --set-version Ubuntu-24.04 2`.


## Step 2: Install Docker and the NVIDIA GPU Toolkit

Docker is the container system that runs each piece of the stack in its own isolated environment. The NVIDIA toolkit lets Docker pass your GPU through to containers so the AI model can use it.

**Where you should be:** Inside the Ubuntu terminal from the previous step. If you closed it, open PowerShell and type `wsl -d Ubuntu-24.04` to get back in (using `-d Ubuntu-24.04` ensures you enter the right Linux environment, which matters if you have multiple distros installed). Then run `cd ~` to make sure you are in your Linux home folder. This is important: the Linux home folder lives on the Linux filesystem, which is significantly faster for file operations than working under `/mnt/c` (your Windows C: drive).

### 2a. Update Ubuntu and install basic tools

```bash
cd ~
```

```bash
sudo apt update && sudo apt full-upgrade -y
```

```bash
sudo apt install -y build-essential curl git gpg unattended-upgrades
```

```bash
sudo dpkg-reconfigure -plow unattended-upgrades
```

The last command opens a pink/blue dialog. Make sure **Yes** is highlighted and press Enter. This turns on automatic security updates for your Linux environment.

### 2b. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
```

```bash
sudo systemctl enable --now docker
```

```bash
sudo usermod -aG docker $USER
```

The last command gives your user account permission to manage Docker, but the change does not take effect until you log out and back in:

1. Type `exit` and press Enter (this drops you back to PowerShell).
2. Type `wsl -d Ubuntu-24.04` and press Enter (this puts you back into Ubuntu).
3. Type `cd ~` and press Enter (returns you to your home folder).

**Verify Docker is working** before continuing:

```bash
docker run --rm hello-world
```

You should see a message that starts with "Hello from Docker!" If you get a permission error instead, repeat the log-out/log-in steps above.

### 2c. Install the NVIDIA Container Toolkit

These three commands add NVIDIA's package repository and install the toolkit. Run them one at a time:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

```bash
sudo apt update && sudo apt install -y nvidia-container-toolkit
```

### 2d. Configure Docker to use the NVIDIA runtime

This command registers the NVIDIA runtime with Docker and makes it the default, so all containers can access the GPU without extra flags:

```bash
sudo nvidia-ctk runtime configure --runtime=docker --set-as-default
```

```bash
sudo systemctl restart docker
```

### 2e. Configure Docker log rotation

This prevents Docker's log files from growing indefinitely and filling your disk. Copy and paste the entire block:

```bash
sudo python3 -c "
import json, pathlib
p = pathlib.Path('/etc/docker/daemon.json')
cfg = json.loads(p.read_text()) if p.exists() else {}
cfg['log-driver'] = 'json-file'
cfg['log-opts'] = {'max-size': '10m', 'max-file': '3'}
p.write_text(json.dumps(cfg, indent=2))
"
```

```bash
sudo systemctl restart docker
```

This merges the log rotation settings into your existing Docker configuration without overwriting the NVIDIA runtime entry that was just added.

### 2f. Verify the GPU is visible to Docker

```bash
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
```

You should see a table showing your GPU name, driver version, and VRAM. If this fails, your NVIDIA driver may need updating, or the toolkit install did not complete. Go back to Step 2c and confirm each command ran without errors.


## Step 3: Deploy EphemerAl and Create the Qwen Alias

This step starts the stack, pulls the Qwen model, and creates the local alias EphemerAl expects.

```bash
git clone https://github.com/eowensai/EphemerAl.git ~/ephemeral-llm
```

```bash
cd ~/ephemeral-llm
```

Start the stack first:

```bash
docker compose up -d --build
```

Then pull Qwen3.6:

```bash
docker exec -it ollama ollama pull qwen3.6:35b-a3b
```

Now enter the Ollama container:

```bash
docker exec -it ollama bash
```

Create `/root/Modelfile.qwen36-ephemeral` with this exact content:

```bash
cat > /root/Modelfile.qwen36-ephemeral <<'EOF_MODEL'
FROM qwen3.6:35b-a3b

PARAMETER num_ctx 262144
PARAMETER num_predict -1

PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER top_k 20
PARAMETER min_p 0
PARAMETER repeat_penalty 1.0
EOF_MODEL
```

Create the alias:

```bash
ollama create ephemeral-default -f /root/Modelfile.qwen36-ephemeral
```

Verify it exists:

```bash
ollama list
```

Check runtime status:

```bash
ollama ps
```

Exit the container shell when done:

```bash
exit
```

### What these settings mean (plain language)

- `num_ctx 262144` pins the alias runtime context window to 256K tokens.
- `num_predict -1` avoids an Ollama-side artificial output cap.
- `temperature`, `top_p`, `top_k`, `min_p`, and `repeat_penalty` are practical Qwen non-thinking defaults that Ollama can store in the Modelfile.
- `presence_penalty` is intentionally **not** in this Modelfile. EphemerAl sends `presence_penalty=1.5` per request. External OpenAI-compatible clients should also send `presence_penalty=1.5` in each request.


## Step 4: Verify the Installation (Pass Criteria)

Run these checks from Ubuntu in your repo folder:

```bash
cd ~/ephemeral-llm
docker compose ps
docker exec -it ollama ollama list
docker exec -it ollama ollama ps
```

Pass criteria:

1. `docker compose ps` shows all services running.
2. `ollama list` shows `ephemeral-default`.
3. `ollama ps` shows `ephemeral-default` loaded.
4. `CONTEXT` is `262144`.
5. `PROCESSOR` is `100% GPU` (or otherwise clearly indicates the model is not CPU-offloaded).
6. The browser app opens at **http://localhost:8501**.
7. A simple prompt returns a normal answer without visible `<think>` content.

If any container is not running, collect logs:

```bash
docker compose logs ollama
docker compose logs ephemeral-app
docker compose logs tika-server
```

If `ollama ps` shows CPU offload, OOM behavior, or unacceptable latency, reduce `num_ctx` in `/root/Modelfile.qwen36-ephemeral`, recreate the alias, and test again.


## Non-Thinking Behavior (Important)

EphemerAl disables Qwen "thinking mode" through the OpenAI-compatible request field:

- `reasoning_effort="none"`

Operator guidance:

- Do **not** add `/nothink` to prompts.
- Do **not** add `<think>` tags to the system prompt.
- Visible reasoning output is intentionally suppressed by default.


## Output Length Behavior (Important)

- EphemerAl does **not** impose `max_tokens` by default.
- `LLM_OUTPUT_RESERVE_TOKENS` reserves part of the input/document budget so the model has room to answer; it does **not** cap output length.
- If endless-loop behavior ever appears, handle that as a separate stability issue. Do not cap normal document-analysis outputs to `8192` tokens as a blanket workaround.


## Step 5: Network Access and Auto-Start (UI on Port 8501)

These steps make EphemerAl available to other computers on your local network and ensure it starts automatically when you log in to Windows.

### Important context

The application runs as a **user-level task**, not a system service. This means it will only start after a specific Windows user logs in. It will not run while the computer is sitting at the lock screen after a reboot. If you want appliance-style behavior where the machine starts everything on boot without a login, search for "netplwiz auto login" to configure automatic Windows login.

### 5a. Allow traffic through the Windows Firewall

Switch to **PowerShell (Admin)** on the Windows side and run:

```powershell
New-NetFirewallRule -DisplayName "EphemerAl Port 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

This rule applies to all network profiles (Domain, Private, and Public). If you want to restrict it to private networks only, add `-Profile Private` to the command.

### 5b. Create the startup script

WSL2 in its default networking mode gets a new internal IP address each time it starts, so Windows needs a small script that discovers that address and forwards incoming traffic on port 8501 to it.

1. Open **Notepad** in Windows.
2. Paste the following:

```powershell
$wslIP = (wsl -d Ubuntu-24.04 -- hostname -I).Split()[0]
netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0 2>$null
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=$wslIP
wsl -d Ubuntu-24.04 -- sleep infinity
```

3. Save the file as `C:\Scripts\Start-EphemerAl.ps1` (create the `C:\Scripts` folder first if it does not exist).

Every `wsl` call in this script explicitly targets `Ubuntu-24.04` with `-d`. This prevents problems on machines that have multiple Linux distros installed, where bare `wsl` would target whichever distro is set as the default.

### 5c. Schedule the script to run at login

1. Search Windows for **Task Scheduler** and open it as Administrator.
2. Click **Create Task** in the right sidebar.
3. On the **General** tab: name it `EphemerAl Auto-Start`. Check both **Run only when user is logged on** and **Run with highest privileges**.
4. On the **Triggers** tab: click New. Set "Begin the task" to **At log on**. Set "Delay task for" to **30 seconds**. Click OK.
5. On the **Actions** tab: click New. Set "Program/script" to `powershell.exe`. In the "Add arguments" field, paste:

```
-ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Scripts\Start-EphemerAl.ps1"
```

6. Click OK to save the task.

### 5d. Test network access (UI)

1. Reboot your computer and log in to Windows. Wait about 30 seconds.
2. Find your PC's IP address by opening PowerShell and running `ipconfig`. Look for the **IPv4 Address** under your active network adapter (for example, `192.168.1.50`).
3. From a different device on the same network (phone, laptop, another PC), open a browser and go to `http://YOUR_IP_ADDRESS:8501`.

If the page works locally but not from another device, confirm your Windows network profile is set to **Private** (Settings → Network & Internet → your connection → Network profile type → Private), and verify the firewall rule from Step 5a was created successfully by running `Get-NetFirewallRule -DisplayName "EphemerAl*"` in PowerShell.


## Optional: Expose Ollama as a Shared API Backend (Port 11434)

By default, this stack keeps raw Ollama internal. That is the safest default and is recommended for most operators.

Use this only when you intentionally want professional development/dev tools to call Ollama directly.

### Start with API override

From `~/ephemeral-llm`, run:

```bash
docker compose -f docker-compose.yml -f docker-compose.api.yml up -d
```

This override defaults `OLLAMA_API_BIND` to `127.0.0.1`.

- `127.0.0.1` means local-host access only.
- For LAN exposure, you must intentionally set `OLLAMA_API_BIND=0.0.0.0` (or another appropriate bind address), then apply Windows firewall and WSL portproxy rules as needed.

### Security warning (read before exposing)

Raw Ollama in this stack has **no app-level authentication**. Do not treat it as safe for broad LAN or internet exposure by default.

For team use, place it behind one or more controls:

- VPN access
- firewall allow-list
- reverse proxy with authentication and TLS

### Optional Windows networking for API port 11434

Only do this if you intentionally expose the API beyond localhost.

**PowerShell (Admin):**

```powershell
New-NetFirewallRule -DisplayName "EphemerAl Ollama API 11434" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow
```

```powershell
$wslIP = (wsl -d Ubuntu-24.04 -- hostname -I).Split()[0]
netsh interface portproxy delete v4tov4 listenport=11434 listenaddress=0.0.0.0 2>$null
netsh interface portproxy add v4tov4 listenport=11434 listenaddress=0.0.0.0 connectport=11434 connectaddress=$wslIP
```

Keep this section separate from the normal UI path on port 8501. Exposing 11434 is optional and should be deliberate.


## External API Caller Examples (Optional)

### OpenAI-compatible client example

- `base_url`: `http://<server>:11434/v1`
- `model`: `ephemeral-default`
- `api_key`: any placeholder value (for example, `not-used`)
- Include request fields:
  - `reasoning_effort: "none"`
  - `temperature: 0.7`
  - `top_p: 0.8`
  - `presence_penalty: 1.5`

Example payload body:

```json
{
  "model": "ephemeral-default",
  "messages": [
    {"role": "user", "content": "Summarize this incident report."}
  ],
  "reasoning_effort": "none",
  "temperature": 0.7,
  "top_p": 0.8,
  "presence_penalty": 1.5
}
```

### Native Ollama API example

Endpoint: `POST http://<server>:11434/api/chat`

```json
{
  "model": "ephemeral-default",
  "messages": [
    {"role": "user", "content": "Summarize this incident report."}
  ],
  "think": false,
  "options": {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0,
    "repeat_penalty": 1.0,
    "num_predict": -1
  }
}
```
