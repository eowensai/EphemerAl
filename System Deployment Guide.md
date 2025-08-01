| Placeholder     | Meaning                                                            |
| --------------- | ------------------------------------------------------------------ |
| `<USER>`        | The Linux username you create on first launch of Ubuntu 24.04      |
| `<PROJECT_DIR>` | `/home/<USER>/ephemeral-llm` = The folder that will hold your app  |
| `<HOST_IP>`     | The Windows host’s LAN IP (run `ipconfig` in cmd to find it)       |

---

## 1  Initial System Setup
All commands are meant to be copy/pasted into the application defined (#Admin PowerShell, #Inside WSL, etc).
Commands separated by a blank line mean the first should be pasted and run (enter key), then followed by the next one, etc.

**Purpose:** Install required Windows features and Ubuntu 24.04 under WSL2.
Run in an **Administrator PowerShell** window: Win button -> type 'powershell' -> click the 'run as administrator' option.
```powershell
# Admin PowerShell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

Reboot Windows, then install Ubuntu 24.04 into WSL:

```powershell
# Admin PowerShell
wsl --install -d Ubuntu-24.04
```

On first launch, WSL prompts you to create a Unix user. Use any short name and write it down. 

---

## 2  WSL Environment Configuration

**Purpose:** Update Ubuntu, install build tools.

If you were asked to create an account, you're already 'within' WSL and can skip the next command.
If it didn't automatically launch, type the following command:

```powershell
# Admin PowerShell
wsl -d Ubuntu-24.04 
```

```bash
# Inside WSL
sudo apt update

sudo apt full-upgrade -y

sudo apt install -y build-essential curl
```

---

## 3  Docker + NVIDIA Container Toolkit

**Purpose:** Install Docker Engine and enable GPU acceleration.

```bash
# Inside WSL - wait out 20s timer about 'docker desktop' upon the curl command execution
curl -fsSL https://get.docker.com | sudo sh

sudo systemctl enable --now docker

# Reminder to replace '<USER> with the account name generated previously:
sudo usermod -aG docker <USER>                     

exit
```

Re-enter WSL to install NVIDIA Container Toolkit:

```powershell
# Admin PowerShell
wsl -d Ubuntu-24.04
```

```bash
# Inside WSL
distribution=$(. /etc/os-release; echo ${ID}${VERSION_ID})

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
 | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
 | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
 | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update && sudo apt install -y nvidia-container-toolkit
```

Apply Docker configuration for GPU access:

```bash
# Inside WSL - Copy/run everything below (down to, and including, "EOF") as a single command
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

Restart Docker:

```bash
# Inside WSL
sudo systemctl restart docker
```

---

### 4  Application Project Setup

**Purpose:** Install project files.

```bash
# Inside WSL
cd ~

git clone https://github.com/eowensai/EphemerAl.git ~/ephemeral-llm

cd ephemeral-llm
```

**Review and Customize** 
Everyone is going to have a different equipment and goals. This step is to review the default settings and modify for yours.

```bash
# Inside WSL - replace <FILENAME> with the file being opened
nano <FILENAME>
```

The following files have settings to review 

* `docker-compose.yml` - Review "#CUSTOMIZE" comments to modify for your hardware.
* `ephemeral_app.py` - Review "#CUSTOMIZE" comments to modify branding and time zone.
* `theme.css` - Review "#CUSTOMIZE" comments to modify colors and (optional) add text logo.
* `system_prompt_template.md` - Instructions sent to LLM each conversation - Modify for your goals/environment.

To save: Close via Ctrl+X -> 'Yes' -> hit enter to accept filename
To exit without save: Ctrl+X -> 'No' (if asked)

**Modify Logo (optional)** It should be a 240x240 pixel, transparent-background PNG. The default placeholder is ephemeral_logo.png.

The site will fail to load without a logo file defined and in place. 

If a logo isn't desired, I'd generate an empty png that's just a transparent background and save + overwrite ephemeral_logo.png.

---

### 5  Build & Deploy Containers

```bash
# Inside WSL
docker compose up -d --build
```

#### Download base model inside the `ollama` container

```bash
# Inside WSL - Change 12b to 27b if desired and understand hardware requirements
docker exec -it ollama ollama pull gemma3:12b-it-qat
```

#### Create production Modelfile

```bash
# Inside WSL - This command puts you inside Ollama and results in a prompt like 'root@f4b449c261f7:/#'
docker exec -it ollama bash
```

The amount of context (ctx), which is a measure of how much information the model can remember in a conversation, depends on your GPU(s).
**Identify the conservative ctx value for your system and replace "XXXXX" with it in the following command**
You can choose to use lower values, or experiment with higher ones.  **Rerun this 'Create production Modelfile' section to update the value.**

| VRAM (GB) | Gemma 3 12B | Gemma 3 27B |
|-----------|-------------|-------------|
| 12        | 12000       | NA          |
| 16        | 50000       | NA          |
| 24        | 131072      | 30000 *     |
| 32        | 131072      | 75000 *     |

"*" = Ollama doesn't split Gemma 3 27b well between multiple cards, so 2x 12gb or 2x 16gb gpus may need lower values.  Start smaller (even as low as 1000), look at gpu memory usage in task manager for both cards. Increase until memory in one of the cards is 0.5 to 1.0GB from full.

Copy the whole command (starting with "cat") and paste into the Ollama prompt to have it generate the config file.

```bash
# Inside Ollama - Note 12b or 27b in model name - and replace XXXXX
cat > Modelfile <<EOF
FROM gemma3:12b-it-qat
PARAMETER num_ctx XXXXX
PARAMETER num_gpu 99
PARAMETER temperature 1.0
PARAMETER top_k 64
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.0
PARAMETER min_p 0.0
EOF
```

```bash
# Inside Ollama - Note 12b or 27b
ollama create gemma3-12b-prod -f Modelfile

exit
```

**Firewall rule (run once to share website to other computers on your network)**

```powershell
# Admin PowerShell - Open another Powershell terminal and paste in this single command:
New-NetFirewallRule -DisplayName "EphemerAl Port 8501" -Direction Inbound `
  -Protocol TCP -LocalPort 8501 -Action Allow
```

---

### 6  Verification

* Open a browser in Windows and visit **http://localhost:8501**.

* If unreachable, run:

  ```powershell
  netstat -ano | findstr :8501
  ```

  You should see `0.0.0.0:8501 … LISTENING`. If it shows `127.0.0.1`, ensure the **IP Helper** service is running, then reboot.

---

### 7  Networking & Auto‑Start (Windows)

A dedicated desktop was built to house this application, and I wanted the website and its services to start whenever the machine was rebooted.
The best I've been able to get working is to configure a local admin 'AI' account in windows that auto logs in (use google/ai for instructions), triggering WSL (and the applications) to start automatically via the following script.

If you prefer to log in manually, I still recommend setting this up as it checks the networking of WSL at start (WSL can change IP address per boot and this script updates the connection to the Windows host IP address).

#### Startup script

```powershell
# Admin PowerShell - Feel free to modify this path where you want the script to live in Windows.
notepad c:\Scripts\Start-EphemerAl.ps1
```

Paste in the 4 lines of code from the github repostory

```bash
# Admin PowerShell - The following is the contents of Start-EphemerAl.ps1 as of launch of this repository. Check online to verify:
$wslIP = (wsl -- hostname -I).Split()[0]
netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0 2>$null
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=$wslIP
wsl -- sleep infinity
```

Save and close Notepad


**Create the Scheduled Task:**

Open Task Scheduler: windows button -> 'task scheduler' -> Run as administrator

In the Action menu in the top left, click 'Create Task'

**General Tab:**

Name: Ephemeral WSL Auto-Launcher

Select: "Run only when user is logged on"

Check: "Run with highest privileges"

**Triggers Tab:**

Click 'New', then in the dropdown at the top next to Begin the task:, select "At log on".

Set a delay of 30 seconds: check the box next to 'Delay task for' and select 30 seconds from the dropdown.

Click 'OK'

**Actions Tab:**

Click 'New', then in the 'Program/script:' field enter 
```
powershell.exe
```

In the 'Add arguments (optional):' field enter: 
```
-ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Scripts\Start-EphemerAl.ps1"
```

 Click 'OK'
 
**Settings Tab:**

Uncheck 'Stop the task if it runs longer than...'

Click 'OK'

**Congrats!  Upon reboot and login, WSL2 and all the applications should start up automatically. They are not visible on the desktop**

**Access the Interface**

From the server:
```
http://localhost:8501
```

From another machine on your network: 
```
#Replace <windows_host_ip_address> with the correct IP:
http://<windows_host_ip_address>:8501
```

**Note**

I haven't tried it, but to avoid a logged in computer, you could Google the powershell command to lock the desktop and add that to the end of the Start-EphemerAl.ps1 script.

---

