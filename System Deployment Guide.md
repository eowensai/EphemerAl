# EphemerAl: System Deployment Guide

## 📋 System Requirements

This software runs inside a "Linux Subsystem" on Windows (technically called **WSL2**). You do not need to know Linux to install it; simply follow the instructions below.

**OS Requirements:**
*   **Supported:** Windows 11 (Pro or Enterprise recommended, Home is supported).
*   **Version:** 21H2 or higher (Fully updated).
*   *Note: Windows Server 2019/2022 is NOT covered by this specific guide due to installation differences.*

**Hardware Requirements:**
*   **Entry Level:** NVIDIA RTX 3060 (12GB)
*   **Mid Range:** NVIDIA RTX 5060 Ti (16GB)
*   **Value King:** NVIDIA RTX 3090 (24GB)
*   **Max Performance:** NVIDIA RTX 5090 (32GB) **OR** Dual 5060 Ti (16GB x 2)

---

## Phase 1: Install the Foundation (WSL2)

We need to enable the subsystem that allows Windows to run Linux applications.

1.  Right-click the **Windows Start Button** and select **PowerShell (Admin)**.
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

    > **What happens next:** A new window will open installing Ubuntu.
    > **Action Required:** It will ask you to create a `Unix username` and `password`.
    > *   **Username:** simple (e.g., `aiadmin`).
    > *   **Password:** secure. **Write this down.** You won't see stars/dots when typing it.

---

## Phase 2: Install the Engine (Docker & NVIDIA)

We will now install the software that manages the AI applications.

> **Concept Check:**
> Throughout this section, we will be working inside **Ubuntu**.
> *   **PowerShell** is the blue/black window for Windows commands.
> *   **Bash** is the command language used inside the Ubuntu window.
> *   If you ever get lost, open PowerShell and type `wsl` to enter Ubuntu, or `exit` to leave it.

1.  Open your Windows Start Menu, search for **Ubuntu**, and open it.
    *(From now on, this black window is referred to as the **Ubuntu Terminal**)*.

2.  Update the system tools. Copy/Paste this into the Ubuntu Terminal (enter your password if asked):

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

    > **STOP:** Close the Ubuntu window completely. Open a new Ubuntu window from the Start menu. This applies the permission changes.

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

7.  Configure Docker for GPU access and Privacy (Disabling logs). Copy this entire block and paste it:

    ```bash
    sudo tee /etc/docker/daemon.json > /dev/null <<EOF
    {
      "default-runtime": "nvidia",
      "runtimes": { "nvidia": { "path": "/usr/bin/nvidia-container-runtime", "runtimeArgs": [] } },
      "storage-driver": "overlay2",
      "log-driver": "json-file",
      "log-opts": { "max-size": "10m", "max-file": "3" }
    }
    EOF
    ```

8.  Restart the engine:

    ```bash
    sudo systemctl restart docker
    ```

---

## Phase 3: Deploy EphemerAl

1.  Download the application code into Ubuntu:

    ```bash
    git clone https://github.com/eowensai/EphemerAl.git ~/ephemeral-llm
    ```

2.  Enter the folder:

    ```bash
    cd ~/ephemeral-llm
    ```

3.  Start the application:
    *(This will take 5-10 minutes to download the base layers)*.

    ```bash
    docker compose up -d --build
    ```

4.  **Verification:** Type `docker ps`. You should see 3 items listed as "Up".

---
## Phase 4: Configure the AI Model

We need to download the "Brain" (Gemma 3) and configure its memory.

**Choose ONLY ONE path below based on your hardware.**

### Path A: Standard (GPU VRAM = 12GB+)
*Best for RTX 3060, 4060 Ti, 5060 Ti, 3090, 4090.*

1.  **Download the 12B Model:**
    ```bash
    docker exec -it ollama ollama pull gemma3:12b-it-qat
    ```

2.  **Enter the Container:**
    ```bash
    docker exec -it ollama bash
    ```

3.  **Create the Config:**
    *Identify your Context Limit below. Copy the code block, replace `12000` with your value, and paste it into the container window.*

    | Your Card | Value |
    | :--- | :--- |
    | 12 GB VRAM | `12000` |
    | 16 GB VRAM | `50000` |
    | 24 GB VRAM | `131072` |

    ```bash
    cat > Modelfile <<EOF
    FROM gemma3:12b-it-qat
    PARAMETER num_ctx 12000
    PARAMETER num_gpu 99
    PARAMETER temperature 0.8
    PARAMETER top_k 64
    PARAMETER top_p 0.95
    PARAMETER repeat_penalty 1.0
    PARAMETER min_p 0.0
    EOF
    ```

4.  **Activate and Exit:**
    *(Run these two commands one by one)*.

    ```bash
    ollama create gemma3-prod -f Modelfile
    ```

    ```bash
    exit
    ```

### Path B: Higher Performance (Combined GPU VRAM = 24GB+)
*For RTX 5090, Dual GPU (12/16GB x2), or Enterprise Cards.*
*Note: Higher VRAM allows this larger version of Gemma 3 to run, but if its answers are too slow, use Path A*

1.  **Download the 27B Model:**
    ```bash
    docker exec -it ollama ollama pull gemma3:27b-it-qat
    ```

2.  **Enter the Container:**
    ```bash
    docker exec -it ollama bash
    ```

3.  **Create the Config:**
    *Identify your Context Limit below. Copy the code block, replace `30000` with your value, and paste it into the container window.*

    | Your Card | Value |
    | :--- | :--- |
    | 24 GB VRAM (Total) | `30000` |
    | 32 GB+ VRAM (Total) | `131072` |

    ```bash
    cat > Modelfile <<EOF
    FROM gemma3:27b-it-qat
    PARAMETER num_ctx 30000
    PARAMETER num_gpu 99
    PARAMETER temperature 0.8
    PARAMETER top_k 64
    PARAMETER top_p 0.95
    PARAMETER repeat_penalty 1.0
    PARAMETER min_p 0.0
    EOF
    ```

4.  **Activate and Exit:**
    *(Run these two commands one by one)*.

    ```bash
    ollama create gemma3-prod -f Modelfile
    ```

    ```bash
    exit
    ```

---

## Phase 5: Networking & Auto-Start (Windows)

These steps make the website accessible on your network and ensure it starts automatically.

> **Important:** This application runs as a **User Task**, not a System Service.
> This means the application will ONLY start **after** a specific user logs into Windows. It will not run while the computer is sitting at the Lock Screen after a reboot.
> *Tip for Dedicated Machines:* You can configure Windows to automatically log in a specific user on boot (search "netplwiz auto login") if you want a true "Appliance" feel.

**1. Open Windows Firewall**
Open **PowerShell (Admin)** in Windows and paste:

```powershell
New-NetFirewallRule -DisplayName "EphemerAl Port 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

**2. Create the Startup Script**
1.  Open **Notepad** in Windows.
2.  Paste the code below:

    ```powershell
    $wslIP = (wsl -- hostname -I).Split()[0]
    netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0 2>$null
    netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=$wslIP
    wsl -- sleep infinity
    ```
3.  Save the file as: `C:\Scripts\Start-EphemerAl.ps1`
    *(Create the Scripts folder on your C: drive if it doesn't exist)*.

**3. Schedule it to Run**
1.  Search Windows for **Task Scheduler** -> Right-click **Run as Administrator**.
2.  Click **Create Task** (Right sidebar).
3.  **General:** Name it `Ephemeral Auto-Start`. Select **Run only when user is logged on** AND **Run with highest privileges**.
4.  **Triggers:** New -> Begin the task: **At log on**. Delay task for: **30 seconds**.
5.  **Actions:** New -> Program/script: `powershell.exe`.
    Add arguments:
    `-ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Scripts\Start-EphemerAl.ps1"`
6.  Click **OK**.

---

## ✅ Success!

1.  Reboot your computer.
2.  Log in to Windows and wait 30 seconds.
3.  **Find your IP Address:**
    Open PowerShell and type `ipconfig`. Look for the **IPv4 Address** (e.g., `192.168.1.50`).
4.  **Test from another computer:**
    On a different device connected to the same network (WiFi/LAN), open a browser and type:
    `http://<YOUR_IP_ADDRESS>:8501`
    *(Example: http://192.168.1.50:8501)*

**Troubleshooting:**
If the page loads locally (`http://localhost:8501`) but not from another computer, ensure your computer is set to **"Private Network"** in Windows Network Settings, or double-check the Firewall Rule command in Phase 5.
