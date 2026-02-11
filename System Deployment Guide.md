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

---

## Phase 1: Prerequisites

Complete all items in this phase before moving on.

1. **Confirm Windows version**
   - Make sure the machine is running **Windows 11, version 21H2 or newer**.

2. **Install the latest NVIDIA GPU driver**
   - Go to [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx).
   - Install the newest production driver for your GPU model.
   - Reboot if prompted.

3. **Install Python 3.11+ (all users)**
   - Download from [python.org downloads](https://www.python.org/downloads/windows/).
   - During install, check **"Add Python to PATH"** and choose **"Install for all users"**.
   - In Windows Settings, disable the Microsoft Store **App execution aliases** for `python.exe` and `python3.exe` if they are enabled.

4. **Install Java 21+ (Temurin recommended)**
   - Download from [Adoptium Temurin Releases](https://adoptium.net/temurin/releases/).
   - Install a **JDK 21 or newer** build for Windows.

5. **Install NSSM (service manager)**
   - Download **pre-release 2.24-101 (Windows 10+)** from [nssm.cc downloads](https://nssm.cc/download).
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
   - Open [Ollama GitHub Releases](https://github.com/ollama/ollama/releases).
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
   - Open [Apache Tika Downloads](https://tika.apache.org/download.html).
   - Download `tika-server-standard-3.2.3.jar`.
   - Place it in `C:\Tika\`.

3. **Copy the JAR to a generic name for service script compatibility**

```powershell
Copy-Item C:\Tika\tika-server-standard-3.2.3.jar C:\Tika\tika-server-standard.jar -Force
```

4. **Verify Tika runs**

```powershell
java -jar C:\Tika\tika-server-standard-3.2.3.jar --port 9998
```

- Open `http://localhost:9998/` in your browser.
- Press `Ctrl + C` in PowerShell to stop.

> **Tip:** If you want to test the generic filename used by the service script, use this command instead:
>
> ```powershell
> java -jar C:\Tika\tika-server-standard.jar --port 9998
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

```powershell
Set-Location C:\EphemerAl
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. **Verify the app runs**

```powershell
python -m streamlit run ephemeral_app.py
```

- Open `http://localhost:8501`.
- Confirm the interface loads.
- Press `Ctrl + C` to stop.

---

## Phase 5: Install Windows Services

In this phase, you will install three services:
- `OllamaService`
- `TikaService`
- `EphemerAlApp`

These start automatically at boot and run even when no user is signed in.

1. **Open PowerShell as Administrator**

2. **Run the install script**

```powershell
C:\EphemerAl\services\Install-EphemerAlServices.ps1
```

3. **Verify service health**

```powershell
C:\EphemerAl\services\Check-EphemerAlServices.ps1
```

> **Tip:** If script execution is blocked by policy, run this in the same elevated PowerShell session:
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> ```

---

## Phase 6: Configure the AI Model

Choose **one** path based on available VRAM.

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

```powershell
nssm restart OllamaService
```

---

## Phase 7: Networking

1. **Allow inbound access to Streamlit port 8501**

Open PowerShell as Administrator and run:

```powershell
New-NetFirewallRule -DisplayName "EphemerAl Port 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

2. **Access the app over the network**

Since services run natively on Windows, the application is directly accessible using the machine's IP address. No additional forwarding configuration is required.

Find the machine IP:

```powershell
ipconfig
```

Open from another device on the same network:

```text
http://<YOUR_IP_ADDRESS>:8501
```

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
  - Update the NVIDIA driver from [nvidia.com](https://www.nvidia.com/Download/index.aspx).
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

## ✅ Success Checklist

1. Reboot the machine.
2. Wait 30-60 seconds after startup.
3. Verify all services are running:

```powershell
Get-Service OllamaService, TikaService, EphemerAlApp
```

4. Find the machine IP:

```powershell
ipconfig
```

5. From another device on the same network, open:

```text
http://<YOUR_IP_ADDRESS>:8501
```

If the page loads and chat works, deployment is complete.
