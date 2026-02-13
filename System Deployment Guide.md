# EphemerAl: System Deployment Guide

## 📋 System Requirements

This guide walks you through a full native Windows deployment of EphemerAl. You can follow it step-by-step, even if you are not a developer.

**OS Requirements:**
* **Supported:** Windows 11 (Pro or Enterprise recommended, Home is supported).
* **Version:** 21H2 or higher (Fully updated).
* *Note: Windows Server 2019/2022 is NOT covered by this specific guide due to installation differences.*

**Hardware Requirements:**
* **Entry Level:** NVIDIA RTX 3060 (12GB)
* **Mid Range:** NVIDIA RTX 5060 Ti (16GB)
* **Value King:** NVIDIA RTX 3090 (24GB)
* **Max Performance:** NVIDIA RTX 5090 (32GB) **OR** Multiple NVIDIA 30-series GPU or newer adding to 24+ GB
* **System RAM:** 16 GB minimum, 32 GB recommended. Windows, Ollama, Apache Tika (Java), and the Streamlit app share system memory.
* **Disk Space:** At least 30 GB free for models, application files, and dependencies. Model files are roughly 8 GB for a 12B variant and 17 GB for a 27B variant.

---

## Phase 1: Prerequisites

Complete all items in this phase before moving on.

1. **Confirm Windows version**
   - Make sure the machine is running **Windows 11, version 21H2 or newer**.

2. **Install the latest NVIDIA GPU driver**
   - Go to <a href="https://www.nvidia.com/Download/index.aspx" target="_blank" rel="noopener noreferrer">NVIDIA Driver Downloads</a>.
   - Install the newest production driver for your GPU model.
   - Reboot if prompted.

3. **Install Python 3.11+ (all users)**
   - Download from <a href="https://www.python.org/downloads/windows/" target="_blank" rel="noopener noreferrer">python.org downloads</a>.
   - During install, check **"Add Python to PATH"** and choose **"Install for all users"**.
   - In Windows Settings, disable the Microsoft Store **App execution aliases** for `python.exe` and `python3.exe` if they are enabled.

4. **Install Java 21+ (Temurin recommended)**
   - Download from <a href="https://adoptium.net/temurin/releases/" target="_blank" rel="noopener noreferrer">Adoptium Temurin Releases</a>.
   - Install a **JDK 21 or newer** build for Windows.

5. **Install NSSM (service manager)**
   - Download **pre-release 2.24-101 (Windows 10+)** from <a href="https://nssm.cc/download" target="_blank" rel="noopener noreferrer">nssm.cc downloads</a>.
   - Extract `nssm.exe` to `C:\NSSM\nssm.exe`.
   - Add `C:\NSSM\` to the **System PATH**:
     - Start Menu → search **"Environment Variables"**.
     - Open **"Edit the system environment variables"**.
     - Click **Environment Variables**.
     - Under **System variables**, select **Path** → **Edit** → **New**.
     - Add `C:\NSSM\` and click **OK** on all windows.
   - If `java --version` fails later, use the same steps to add your Java `bin` folder to **System PATH**.

6. **Verify prerequisites in PowerShell**

```powershell
python --version
java --version
nssm version
```

> **Tip:** If any command says "not recognized," fix PATH first, then reopen PowerShell and test again.

---

## Phase 2: Install Ollama

1. **Download standalone Ollama ZIP**
   - Open <a href="https://github.com/ollama/ollama/releases" target="_blank" rel="noopener noreferrer">Ollama GitHub Releases</a>.
   - Download the latest `ollama-windows-amd64.zip` asset.
   - Do **not** use the setup installer for this deployment.

2. **Extract files**
   - Extract the ZIP into `C:\Ollama\`.
   - Confirm the executable exists at `C:\Ollama\ollama.exe`.

3. **Create model storage folder**

```powershell
New-Item -ItemType Directory -Force -Path C:\Ollama\models
```

4. **Verify GPU detection**

```powershell
C:\Ollama\ollama serve
```

- Watch startup output and confirm it detects your NVIDIA GPU.
- Press `Ctrl + C` to stop once verified.

> **Tip:** If GPU is not detected, update NVIDIA drivers first, then test again.

---

## Phase 3: Install Apache Tika

1. **Create Tika folder**

```powershell
New-Item -ItemType Directory -Force -Path C:\Tika
```

2. **Download Tika server JAR**
   - Open <a href="https://tika.apache.org/download.html" target="_blank" rel="noopener noreferrer">Apache Tika Downloads</a>.
   - Download `tika-server-standard-3.2.3.jar`.
   - Place it in `C:\Tika\`.

3. **Copy the JAR to a generic name for service script compatibility**

```powershell
Copy-Item C:\Tika\tika-server-standard-3.2.3.jar C:\Tika\tika-server-standard.jar -Force
```

4. **Verify Tika runs**

```powershell
java -jar C:\Tika\tika-server-standard-3.2.3.jar --host 127.0.0.1 --port 9998
```

- Open `http://127.0.0.1:9998/` in your browser.
- Press `Ctrl + C` in PowerShell to stop.

> **Tip:** If you want to test the generic filename used by the service script, use this command instead:
>
> ```powershell
> java -jar C:\Tika\tika-server-standard.jar --host 127.0.0.1 --port 9998
> ```

---

## Phase 4: Install EphemerAl

1. **Get the repository into `C:\EphemerAl\`**

Choose one option:

**Option A — Git clone**

```powershell
git clone https://github.com/eowensai/EphemerAl.git C:\EphemerAl
```

**Option B — Download ZIP**
- Download the project ZIP from GitHub.
- Extract it so the main file is at `C:\EphemerAl\ephemeral_app.py`.

2. **Install Python dependencies**

Open PowerShell **as Administrator** for this step so packages install into the system-wide Python, not per-user:

```powershell
Set-Location C:\EphemerAl
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> **Tip:** If you installed Python "for all users" in Phase 1, an admin shell ensures pip writes to `C:\Program Files\Python3xx\Lib\site-packages\` where the Windows services can find them.

3. **Verify the app runs**

Before launching Streamlit manually, you can set this environment variable in the same PowerShell window:

```powershell
$env:TIKA_CLIENT_ONLY="true"
```

This is a safety step for clarity. The app already defaults to client-only mode, so this command is optional.

Now start Streamlit:

```powershell
python -m streamlit run ephemeral_app.py
```

- Open `http://localhost:8501`.
- Confirm the interface loads.
- Press `Ctrl + C` to stop.

> **Important:** If Ollama and Tika are not running yet, the Streamlit page still opens, but you will see sidebar warnings and document uploads will not parse.
>
> **Full functional smoke test (recommended):**
> - Option 1: In two separate PowerShell windows, run `C:\Ollama\ollama.exe serve` and `java -jar C:\Tika\tika-server-standard.jar --host 127.0.0.1 --port 9998` while you test Streamlit.
> - Option 2: Install services in Phase 5 first, then run this Streamlit test after `Check-EphemerAlServices.ps1` shows all services healthy.

---

## Phase 5: Install Windows Services

In this phase, you will install three services:
- `OllamaService`
- `TikaService`
- `EphemerAlApp`

These start automatically at boot and run even when no user is signed in.

> **Important:** If you have not completed Phase 6 yet, the services will start successfully but chat will not work because the AI model (`gemma3-prod`) has not been created. This is expected. Complete Phase 6 and then restart `OllamaService` to enable chat.

1. **Open PowerShell as Administrator**

2. **Allow scripts in this session (temporary)**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

> This only applies to the current PowerShell window and resets when you close it.

3. **If you used "Download ZIP", unblock the scripts**

Windows may mark downloaded scripts as blocked. Unblock them before running:

```powershell
Unblock-File -Path C:\EphemerAl\services\*.ps1
```

Optional (unblocks all files in the repo):

```powershell
Get-ChildItem C:\EphemerAl -Recurse -File | Unblock-File
```

4. **Run the install script**

```powershell
C:\EphemerAl\services\Install-EphemerAlServices.ps1
```

5. **Verify service health**

```powershell
C:\EphemerAl\services\Check-EphemerAlServices.ps1
```

---

## Phase 6: Configure the AI Model

Choose **one** path based on available VRAM.

Before running any `ollama pull` or `ollama create` command in this phase, set the model directory for the current PowerShell session so manual model management matches the Windows service configuration:

```powershell
$env:OLLAMA_MODELS='C:\Ollama\models'
```

> **Why this matters:** The service installer configures `OllamaService` to use `C:\Ollama\models`. Setting this variable first prevents a common first-run issue where models are downloaded to a different default folder and then appear missing after service restart.

### Path A: Standard (GPU VRAM = 12GB+)
*Best for RTX 3060, 4060 Ti, 5060 Ti, 3090, 4090.*

1. **Download the 12B model**

```powershell
C:\Ollama\ollama.exe pull gemma3:12b-it-qat
```

2. **Create `Modelfile` in `C:\Ollama\`**

Use PowerShell:

```powershell
Set-Location C:\Ollama
@"
FROM gemma3:12b-it-qat
PARAMETER num_ctx 12000
PARAMETER num_gpu 99
PARAMETER temperature 0.8
PARAMETER top_k 64
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.0
PARAMETER min_p 0.0
"@ | Set-Content -Path .\Modelfile -Encoding ASCII
```

Or use Notepad:

```powershell
notepad C:\Ollama\Modelfile
```

Then paste this content and save:

```text
FROM gemma3:12b-it-qat
PARAMETER num_ctx 12000
PARAMETER num_gpu 99
PARAMETER temperature 0.8
PARAMETER top_k 64
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.0
PARAMETER min_p 0.0
```

3. **Set context size for your VRAM**

Replace `12000` in `PARAMETER num_ctx` using this table:

| Your Card | Value |
| :--- | :--- |
| 12 GB VRAM | `12000` |
| 16 GB VRAM | `50000` |
| 24+ GB VRAM | `131072` |

4. **Create production model**

```powershell
Set-Location C:\Ollama
C:\Ollama\ollama.exe create gemma3-prod -f Modelfile
```

5. **Restart Ollama service**

First verify the service exists and is running:

```powershell
Get-Service OllamaService
```

Then restart it:

```powershell
nssm restart OllamaService
```

> **Stop here for Path A users.** Continue to Phase 7.

### Path B: Higher Performance (Combined GPU VRAM = 24GB+)
*For RTX 5090, Dual GPU (12/16GB x2), or Enterprise Cards.*
*Note: Higher VRAM allows this larger version of Gemma 3 to run, but if its answers are too slow, use Path A*

1. **Download the 27B model**

```powershell
C:\Ollama\ollama.exe pull gemma3:27b-it-qat
```

2. **Create `Modelfile` in `C:\Ollama\`**

Use PowerShell:

```powershell
Set-Location C:\Ollama
@"
FROM gemma3:27b-it-qat
PARAMETER num_ctx 30000
PARAMETER num_gpu 99
PARAMETER temperature 0.8
PARAMETER top_k 64
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.0
PARAMETER min_p 0.0
"@ | Set-Content -Path .\Modelfile -Encoding ASCII
```

Or use Notepad:

```powershell
notepad C:\Ollama\Modelfile
```

Then paste this content and save:

```text
FROM gemma3:27b-it-qat
PARAMETER num_ctx 30000
PARAMETER num_gpu 99
PARAMETER temperature 0.8
PARAMETER top_k 64
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.0
PARAMETER min_p 0.0
```

3. **Set context size for your VRAM**

Replace `30000` in `PARAMETER num_ctx` using this table:

| Your Card | Value |
| :--- | :--- |
| 24 GB VRAM (Total) | `30000` |
| 32+ GB VRAM (Total) | `131072` |

4. **Create production model**

```powershell
Set-Location C:\Ollama
C:\Ollama\ollama.exe create gemma3-prod -f Modelfile
```

5. **Restart Ollama service**

First verify the service exists and is running:

```powershell
Get-Service OllamaService
```

Then restart it:

```powershell
nssm restart OllamaService
```

---

## Phase 7: Networking

1. **Allow inbound access to Streamlit port 8501**

Open PowerShell as Administrator and run:

```powershell
New-NetFirewallRule -DisplayName "EphemerAl Port 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Profile Domain,Private -Action Allow
```

> **Note:** This rule applies to **Domain** and **Private** network profiles only. If your network is classified as **Public** (common on first connection), remote devices will not be able to reach port 8501. Check your profile with `Get-NetConnectionProfile` and change it if needed with `Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private`. Replace `Ethernet` with the `InterfaceAlias` value shown by `Get-NetConnectionProfile` (commonly `Wi-Fi` on laptops).

2. **Access the app over the network**

Since services run natively on Windows, the application is directly accessible using the machine's IP address when Streamlit is listening on `0.0.0.0`.

> **Security note (default-safe):** The service script keeps Ollama (`11434`) and Tika (`9998`) bound to `127.0.0.1` by default so they are not exposed to the LAN. Do not expose those APIs unless you intentionally need remote access.

Find the machine IP:

```powershell
ipconfig
```

> **Important:** If this machine gets its address from DHCP, the IP can change after a reboot or lease renewal. To keep the address stable, configure a static IP on the machine or create a DHCP reservation on the router for this machine's MAC address. Ask your network administrator if you are unsure which option to use.

Open from another device on the same network:

```text
http://<YOUR_IP_ADDRESS>:8501
```

3. **Remote access troubleshooting (if another device cannot connect)**

Opening a firewall rule is not enough if Streamlit is bound only to localhost.

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8501 | Select-Object LocalAddress, LocalPort, OwningProcess
```

- If `LocalAddress` is `0.0.0.0` (or `::`), Streamlit is listening for network traffic.
- If `LocalAddress` is only `127.0.0.1` (or `::1`), remote access will fail.
  - Confirm the `EphemerAlApp` service arguments include `--server.address=0.0.0.0` (re-run `C:\EphemerAl\services\Install-EphemerAlServices.ps1` to reset service settings if needed).

---

## 🛠️ Troubleshooting

### Check service status

```powershell
nssm status OllamaService
nssm status TikaService
nssm status EphemerAlApp
```

```powershell
Get-Service OllamaService, TikaService, EphemerAlApp
```

### Restart a service

```powershell
nssm restart OllamaService
nssm restart TikaService
nssm restart EphemerAlApp
```

### View service logs

NSSM records stdout/stderr logs if AppStdout/AppStderr are configured. To check configured log paths:

```powershell
nssm get OllamaService AppStdout
nssm get OllamaService AppStderr
nssm get TikaService AppStdout
nssm get TikaService AppStderr
nssm get EphemerAlApp AppStdout
nssm get EphemerAlApp AppStderr
```

If a path is returned, open that file to review startup errors.

### Common issues

- **Java not found**
  - Run `java --version`.
  - If command fails, reinstall Java 21+ and verify PATH.

- **Ollama GPU not detected**
  - Update the NVIDIA driver from <a href="https://www.nvidia.com/Download/index.aspx" target="_blank" rel="noopener noreferrer">nvidia.com</a>.
  - Re-test with `C:\Ollama\ollama serve`.

- **Port already in use (8501, 9998, or 11434)**

```powershell
netstat -ano | findstr :8501
netstat -ano | findstr :9998
netstat -ano | findstr :11434
```

- **Service will not start**
  - Check status: `nssm status <ServiceName>`.
  - Check NSSM stdout/stderr log locations using `nssm get <ServiceName> AppStdout` and `nssm get <ServiceName> AppStderr`.
  - Re-run: `C:\EphemerAl\services\Check-EphemerAlServices.ps1`.

### Complete uninstall

```powershell
C:\EphemerAl\services\Uninstall-EphemerAlServices.ps1
```

---

## ✅ Functional Smoke Test Checklist

1. Reboot the machine, then wait 60 seconds after startup.
2. Verify all three services are running:

```powershell
Get-Service OllamaService, TikaService, EphemerAlApp
```

3. On the server, open `http://localhost:8501` in a browser and confirm the welcome screen loads.
4. Send a simple message such as `Hello` and confirm you receive an AI response.
5. Upload a small PDF or Word document, ask the AI to summarize it, and confirm parsing succeeds and the response references document content.
6. Upload an image (for example, a photo), ask the AI to describe it, and confirm the image description is returned.
7. Click **New Conversation** in the sidebar and confirm the previous conversation is cleared.
8. From a different device on the same network, verify network access and chat:

```powershell
ipconfig
```

```text
http://<YOUR_IP_ADDRESS>:8501
```

Confirm the interface loads and chat works from that second device.
