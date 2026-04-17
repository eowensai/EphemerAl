# EphemerAl: System Deployment Guide

**Default model: Gemma 4 31B on Ollama**

This guide walks you through a complete installation of EphemerAl on a Windows 11 machine with an NVIDIA GPU. Every step is designed for copy-and-paste; no Linux experience is required.

When you are finished, you will have four things running inside a Linux subsystem on your Windows PC:

- **Docker**, the container engine that manages the other three components.
- **Ollama**, the service that runs the AI model on your GPU.
- **Apache Tika**, a document parser that lets the AI read uploaded files (PDFs, Word docs, spreadsheets, and more).
- **EphemerAl**, the web-based chat interface your users will open in a browser.


## System Requirements

**Operating system:** Windows 11 (Pro or Enterprise recommended, Home is supported), version 21H2 or higher, fully updated. Windows Server is not covered by this guide.

**GPU:** Gemma 4 31B is a large dense model. Your NVIDIA VRAM determines how well it will run:

- **48 GB or more total VRAM** gives comfortable headroom for longer conversations and larger documents. This is the recommended starting point.
- **32 GB total VRAM** works for many users with default settings.
- **CPU-only** is technically possible but far too slow for interactive use.

If your hardware is below 32 GB VRAM, consider targeting a smaller Ollama model instead of Gemma 4 31B. You can change the model at any time by editing one environment variable.

**NVIDIA Driver:** Install the latest WHQL-certified driver from NVIDIA's website before proceeding. If your PC has both integrated graphics and a discrete NVIDIA card, connecting your monitor to the integrated output frees more VRAM for the AI.


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


## Step 3: Deploy EphemerAl

This step downloads the EphemerAl repository and starts the three-container stack (Ollama, Tika, and the web app).

```bash
git clone https://github.com/eowensai/EphemerAl.git ~/ephemeral-llm
```

```bash
cd ~/ephemeral-llm
```

The `docker-compose.yml` file already ships with `LLM_MODEL_NAME=gemma4:31b`, so no model-name change is needed for a standard first run.

If you are upgrading an existing install that already uses the `ephemeral-default` alias, you can keep that alias workflow. In that case, leave your alias in place and set `LLM_MODEL_NAME=ephemeral-default` instead of switching back to the raw upstream tag.

Now start the stack:

```bash
docker compose up -d --build
```

The first run takes several minutes because Docker needs to download container images and build the app. When it finishes, all three containers will be running in the background.

The compose file pins Ollama to version `0.21.0` and Apache Tika to `3.3.0.0-full` for tested compatibility with Gemma 4 (including flash attention and Q8 KV cache). Check each project's release notes before changing these versions.


## Step 4: Download the AI Model

This downloads roughly 20 GB of model weights into the Ollama container's persistent storage. It only needs to happen once.

```bash
docker exec -it ollama ollama pull gemma4:31b
```

This will take a while depending on your internet speed. When it completes, you are ready to use the app.

**A note on context window size:** Ollama automatically scales the context window based on your available VRAM (4k tokens under 24 GB, 32k from 24–48 GB, 256k at 48+ GB). This auto-scaling is a good default for most users. If you want to pin a specific context size for more predictable VRAM usage, see the "Stable Local Alias" section below.

**A note on thinking mode:** In the shipped app, extended reasoning is effectively disabled by default. The default `system_prompt_template.md` is model-agnostic and omits `<|think|>`, and chat requests also set `reasoning_effort="none"`. Gemma 4 may still occasionally emit thought-channel output, but the app's streaming logic filters that from displayed responses. If you want to experiment with thinking mode, plan on app/runtime changes in addition to any prompt or Modelfile edits.


## Step 5: Verify the Installation

Open a browser on the same machine and navigate to:

**http://localhost:8501**

You should see the EphemerAl chat interface. Try sending a message to confirm the model responds.

If the page loads but the model does not respond, check that the model finished downloading and that the containers are healthy:

```bash
cd ~/ephemeral-llm
docker compose ps
docker exec -it ollama ollama list
```

You should see all three containers in a "running" state, and either `gemma4:31b` or `ephemeral-default` listed in the Ollama model list (depending on whether you kept the direct model tag or adopted the alias workflow).

If a container is not running, check its logs for errors:

```bash
docker compose logs ollama
docker compose logs ephemeral-app
docker compose logs tika-server
```


## Step 6: Network Access and Auto-Start

These steps make EphemerAl available to other computers on your local network and ensure it starts automatically when you log in to Windows.

### Important context

The application runs as a **user-level task**, not a system service. This means it will only start after a specific Windows user logs in. It will not run while the computer is sitting at the lock screen after a reboot. If you want "appliance" behavior where the machine starts everything on boot without a login, search for "netplwiz auto login" to configure automatic Windows login.

### 6a. Allow traffic through the Windows Firewall

Switch to **PowerShell (Admin)** on the Windows side and run:

```powershell
New-NetFirewallRule -DisplayName "EphemerAl Port 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

This rule applies to all network profiles (Domain, Private, and Public). If you want to restrict it to private networks only, add `-Profile Private` to the command.

### 6b. Create the startup script

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

### 6c. Schedule the script to run at login

1. Search Windows for **Task Scheduler** and open it as Administrator.
2. Click **Create Task** in the right sidebar.
3. On the **General** tab: name it `EphemerAl Auto-Start`. Check both **Run only when user is logged on** and **Run with highest privileges**.
4. On the **Triggers** tab: click New. Set "Begin the task" to **At log on**. Set "Delay task for" to **30 seconds**. Click OK.
5. On the **Actions** tab: click New. Set "Program/script" to `powershell.exe`. In the "Add arguments" field, paste:

```
-ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Scripts\Start-EphemerAl.ps1"
```

6. Click OK to save the task.

### 6d. Test network access

1. Reboot your computer and log in to Windows. Wait about 30 seconds.
2. Find your PC's IP address by opening PowerShell and running `ipconfig`. Look for the **IPv4 Address** under your active network adapter (for example, `192.168.1.50`).
3. From a different device on the same network (phone, laptop, another PC), open a browser and go to `http://YOUR_IP_ADDRESS:8501`.

If the page works locally but not from another device, confirm your Windows network profile is set to **Private** (Settings → Network & Internet → your connection → Network profile type → Private), and verify the firewall rule from Step 6a was created successfully by running `Get-NetFirewallRule -DisplayName "EphemerAl*"` in PowerShell.


## Optional (Advanced/Operator): Stable Local Alias

For operators who want more control over model parameters, you can create a local alias that pins specific settings. This is optional and not required for normal deployments. It is useful if you want to lock the context window to a predictable size or insulate the app from upstream changes to the Ollama model tag.

Enter the Ollama container:

```bash
docker exec -it ollama bash
```

Inside the container, paste this entire block:

```bash
cat > Modelfile <<EOF_MODEL
FROM gemma4:31b
PARAMETER num_ctx 4000
PARAMETER num_gpu 99
PARAMETER temperature 1.0
PARAMETER top_p 0.95
PARAMETER top_k 64
SYSTEM "You are a helpful assistant."
EOF_MODEL
ollama create ephemeral-default -f Modelfile
exit
```

Then update the app to use the alias:

```bash
cd ~/ephemeral-llm
sed -i 's#LLM_MODEL_NAME=gemma4:31b#LLM_MODEL_NAME=ephemeral-default#' docker-compose.yml
docker compose up -d
```

Some notes on the parameters in this Modelfile:

- **num_ctx 4000** pins the context window to 4,000 tokens regardless of your VRAM. This is a conservative choice for predictable memory usage. Ollama's default auto-scaling would give you 32k on a 24–48 GB card, or 256k at 48+ GB. If you have VRAM headroom and want longer conversations or larger document uploads, increase this value or remove the line to let Ollama auto-scale.
- **num_gpu 99** tells Ollama to offload as many layers as possible to the GPU.
- **SYSTEM line** is intentionally simple and model-agnostic. In the shipped app, changing this line alone does not enable visible thinking mode because chat requests also force `reasoning_effort="none"`.
