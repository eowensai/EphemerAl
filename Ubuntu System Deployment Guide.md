# EphemerAl: System Deployment Guide (Linux)

## System Requirements

This guide installs EphemerAl on Ubuntu Server (headless, no GUI required). Assumes SSH or local terminal access with `sudo`.

Supported OS

* Ubuntu 22.04 LTS or 24.04 LTS, fully updated

Hardware

* NVIDIA GPU with a working Linux driver

  * Minimum practical VRAM: 12GB (Gemma 3 12B QAT)
  * Recommended VRAM: 24GB+ total (Gemma 3 27B QAT and/or large context)
* CPU/RAM: 8+ threads, 32GB RAM recommended
* Disk: 50GB+ free space (models are large)

Security reality check

* The Streamlit UI has no built-in authentication. Treat port 8501 as LAN-only, or put it behind a VPN or reverse proxy with auth before exposing it beyond your trusted network.
* By default in this stack, Ollama (11434) and Tika (9998) bind to localhost only and are not reachable from your LAN.
* This is intentional because Docker-published ports can bypass ufw rules in common configurations.

## Phase 1: Install the Foundation (NVIDIA Drivers)

Goal: the host OS must have a working NVIDIA driver before Docker can use the GPU.

1. Update the system

```bash
sudo apt update && sudo apt full-upgrade -y
```

2. Install required utilities

```bash
sudo apt install -y build-essential ca-certificates curl git gnupg ufw ubuntu-drivers-common mokutil
```

3. Confirm an NVIDIA GPU is present

```bash
lspci | grep -i nvidia
```

Expected: one or more lines showing your NVIDIA GPU model. If nothing appears, you do not have an NVIDIA GPU (or it is not detected), and this guide does not apply.

4. Check Secure Boot status

```bash
sudo mokutil --sb-state
```

Expected: `SecureBoot enabled` or `SecureBoot disabled`.

On Ubuntu, `mokutil --sb-state` is a standard way to check Secure Boot state.

If Secure Boot is enabled, NVIDIA kernel modules may not load until Secure Boot is disabled in BIOS or you complete MOK enrollment during the driver installation flow.

5. Install the recommended NVIDIA driver

```bash
sudo ubuntu-drivers autoinstall
```

6. Reboot

```bash
sudo reboot
```

7. Verify the GPU is visible on the host

```bash
nvidia-smi
```

Expected: a table showing your GPU model and driver version.

If `nvidia-smi` fails, check whether the kernel module loaded:

```bash
lsmod | grep -E '^nvidia'
```

If no nvidia modules appear and Secure Boot is enabled, you need to either disable Secure Boot in BIOS or complete MOK enrollment. Do not continue until `nvidia-smi` succeeds.

## Phase 2: Install the Engine (Docker + NVIDIA Container Toolkit)

Goal: Docker runs, your user can run Docker commands, containers can access the GPU.

1. Install Docker Engine

```bash
curl -fsSL https://get.docker.com | sudo sh
```

2. Enable Docker and start it

```bash
sudo systemctl enable --now docker
```

3. Add your user to the docker group

```bash
sudo usermod -aG docker $USER
```

4. Refresh permissions

Log out and back in (SSH reconnect), then:

```bash
cd ~
```

5. Confirm Docker and Compose are available

```bash
docker --version
docker compose version
```

If `docker compose` fails:

```bash
sudo apt install -y docker-compose-plugin
docker compose version
```

6. Install the NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```

```bash
sudo apt update && sudo apt install -y nvidia-container-toolkit
```

If `apt update` fails with "Conflicting values set for option Signed-By", you have older NVIDIA repo entries. Find and remove them:

```bash
grep -l "nvidia.github.io" /etc/apt/sources.list.d/* | grep -v nvidia-container-toolkit.list
```

Remove any files that command lists, then rerun `sudo apt update`.

7. Configure Docker to use the NVIDIA runtime

Back up daemon.json if it exists:

```bash
sudo test -f /etc/docker/daemon.json && sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%F)
```

Now configure using NVIDIA's recommended `nvidia-ctk` flow:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
```

This is NVIDIA's documented approach for configuring Docker to use the NVIDIA runtime.

Verify the runtime was registered:

```bash
docker info 2>/dev/null | grep -i nvidia
```

Expected: a line mentioning `nvidia` in the available runtimes. If nothing appears, the configuration did not take effect.

8. Restart Docker

```bash
sudo systemctl restart docker
```

9. Verify GPU access inside Docker

```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

Expected: the same `nvidia-smi` output, but from inside a container. If this fails, stop and fix GPU-in-Docker before continuing.

## Phase 3: Deploy EphemerAl

1. Clone the repo

```bash
git clone https://github.com/eowensai/EphemerAl.git ~/ephemeral-llm
```

2. Enter the folder

```bash
cd ~/ephemeral-llm
```

3. Check for port conflicts

```bash
sudo ss -lntp | grep -E ':(8501|11434|9998)\b'
```

If any ports are in use (common if you have native Ollama installed), either stop that service or change the compose file's published ports.

4. Start the stack

```bash
docker compose up -d --build
```

5. Validate containers are up

```bash
docker compose ps
```

Expected: `ollama`, `tika-server`, `ephemeral-app` are Up.

6. Verify Compose requested GPU access for Ollama

```bash
docker inspect ollama --format '{{json .HostConfig.DeviceRequests}}'
```

Expected: a JSON array containing `nvidia` or GPU device info. If it returns `null` or `[]`, Compose did not request a GPU, and Ollama will run on CPU only (very slow). This can happen with older docker compose versions that ignore `deploy` blocks.

7. Validate service endpoints locally

Ollama:

```bash
curl -s http://localhost:11434/api/tags
```

Expected: JSON with a `models` list. It may be empty before Phase 4.

Tika:

```bash
curl -s http://localhost:9998/version
```

Expected: a version string like `Apache Tika 3.x.x`.

UI:

```bash
curl -I http://localhost:8501 2>/dev/null | head -1
```

Expected: `HTTP/1.1 200 OK`. Redirects like `302` or `307` can also be acceptable depending on Streamlit behavior.

8. Confirm listening addresses

```bash
sudo ss -lntp | grep -E ':(8501|11434|9998)\b'
```

Expected:

* 11434 and 9998 bound to `127.0.0.1`
* 8501 bound to `0.0.0.0`

Note: the UI may show "model not found" until Phase 4 completes.

**Troubleshooting tip:** The compose file disables logs for Ollama and Tika for privacy. If something fails during first-run debugging, run `docker compose up` without `-d` to see real-time output, or temporarily change the logging driver in docker-compose.yml to `local`.

## Phase 4: Configure the AI Model (Gemma 3)

Goal: download a model, then create the stable model name EphemerAl expects: `gemma3-prod`.

Before pulling models, verify Docker has enough disk space. Models are 7GB+ and live in Docker's data directory:

```bash
df -h /var/lib/docker
```

If `/var` is on a small partition, consider moving Docker's data root or using a bind mount to a larger disk.

Choose one path.

### Path A: Standard (12GB+ VRAM)

1. Pull the model

```bash
docker exec -it ollama ollama pull gemma3:12b-it-qat
```

2. Open a shell in the container

```bash
docker exec -it ollama bash
```

If bash is missing:

```bash
docker exec -it ollama sh
```

3. Create the Modelfile

`num_ctx` is context length in tokens. Higher values use more VRAM. If the model becomes unstable, reduce `num_ctx`, then recreate the model.

| VRAM   | Suggested num_ctx |
| ------ | ----------------- |
| 12 GB  | 12000             |
| 16 GB  | 50000             |
| 24 GB+ | 131072            |

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

4. Create the production model name

```bash
ollama create gemma3-prod -f Modelfile
```

5. Verify it exists

```bash
ollama list | grep -E "gemma3-prod|gemma3"
```

Expected: a line containing `gemma3-prod` with size and modification date.

6. Exit

```bash
exit
```

Skip Path B.

### Path B: Higher Performance (24GB+ total VRAM)

1. Pull the model

```bash
docker exec -it ollama ollama pull gemma3:27b-it-qat
```

2. Open a shell

```bash
docker exec -it ollama bash
```

(or `sh` if needed)

3. Create the Modelfile

| Total VRAM | Suggested num_ctx |
| ---------- | ----------------- |
| 24 GB      | 30000             |
| 32 GB+     | 131072            |

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

4. Create the production model name

```bash
ollama create gemma3-prod -f Modelfile
```

5. Verify

```bash
ollama list | grep -E "gemma3-prod|gemma3"
```

6. Exit

```bash
exit
```

Model maintenance

* To change `num_ctx`:

```bash
docker exec -it ollama ollama rm gemma3-prod
```

Then rerun the Modelfile and create steps.

## Phase 5: Network Access (LAN)

Goal: expose only the UI on port 8501 to your LAN.

1. Find your server IP address

```bash
hostname -I
```

Pick the IP that matches your LAN subnet.

2. If you are connected via SSH, allow SSH before enabling ufw

```bash
sudo ufw allow OpenSSH
```

3. Allow LAN access to the UI

Most home networks:

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8501 proto tcp
```

If your LAN uses 10.x:

```bash
sudo ufw allow from 10.0.0.0/8 to any port 8501 proto tcp
```

4. Enable the firewall

```bash
sudo ufw enable
```

5. Verify

```bash
sudo ufw status verbose
```

6. Test locally

```bash
curl -I http://localhost:8501 2>/dev/null | head -1
```

7. Test from another device on your LAN

```text
http://<YOUR_SERVER_IP>:8501
```

8. Negative test: confirm Ollama and Tika are not reachable from your LAN

From another LAN device, these should fail:

```bash
curl -m 2 -sS http://<YOUR_SERVER_IP>:11434/api/tags
curl -m 2 -sS http://<YOUR_SERVER_IP>:9998/version
```

If either succeeds, your compose file is publishing those ports beyond localhost and should be corrected.

**Note:** ufw rules may not reliably restrict Docker-published ports because Docker manipulates iptables directly. If you need strict enforcement, configure the DOCKER-USER iptables chain or place the UI behind a reverse proxy with authentication.

## Phase 6: Survive Reboots (Auto-Start)

Current behavior

* The compose file uses `restart: unless-stopped`.
* Containers restart on crash and generally come back after reboot if they were running before shutdown.
* If you manually stop a container, `unless-stopped` keeps it stopped until you start it again.

Option A: rely on Docker restart policies
Do nothing extra.

Option B: appliance mode via systemd
This forces the stack up at boot, runs as your user (not root), and avoids user-edit placeholders.

1. Create the service file

This includes safety checks and bakes the correct paths and username into the unit file.

```bash
DOCKER_BIN="$(command -v docker)"
EPH_DIR="$HOME/ephemeral-llm"
EPH_USER="$(id -un)"

echo "docker path: $DOCKER_BIN"
echo "user: $EPH_USER"
test -x "$DOCKER_BIN" || { echo "docker not found"; exit 1; }
test -d "$EPH_DIR" || { echo "missing $EPH_DIR, did you clone the repo?"; exit 1; }

sudo tee /etc/systemd/system/ephemeral.service > /dev/null <<EOF
[Unit]
Description=EphemerAl Docker Compose Stack
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=$EPH_USER
WorkingDirectory=$EPH_DIR
ExecStart=$DOCKER_BIN compose up -d
ExecStop=$DOCKER_BIN compose stop
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
```

2. Verify the paths and user systemd will use

```bash
grep -E 'User=|WorkingDirectory|Exec(Start|Stop)=' /etc/systemd/system/ephemeral.service
```

3. Enable the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ephemeral.service
```

**Important:** On some systems, `systemctl daemon-reload` can cause running GPU containers to lose GPU access (NVML errors). The reboot in step 4 clears this, but if you ever run `daemon-reload` later without rebooting, restart the stack afterward:

```bash
sudo systemctl restart ephemeral.service
```

4. Reboot and confirm

```bash
sudo reboot
```

After reboot:

```bash
curl -I http://localhost:8501 2>/dev/null | head -1
```

## Phase 7: Linux-Specific Fragility (Prevent & Fix)

### Issue A: Network interface name changes

If your NIC name changes, static IP config can break.

Optional prevention: pin a stable interface name via Netplan match on MAC.

```bash
ip -br link
ls /etc/netplan/
sudo nano /etc/netplan/01-netcfg.yaml
```

**Warning:** The example below renames your interface to `lan0`. If you do not want to rename it, use your existing interface name from `ip -br link` (such as `eno1` or `enp3s0`) instead of `lan0` in both the key and `set-name` fields. Only use `set-name` if you deliberately want a stable, predictable name.

Example (with deliberate rename to `lan0`):

```yaml
network:
  version: 2
  ethernets:
    lan0:
      match:
        macaddress: "aa:bb:cc:dd:ee:ff"
      set-name: lan0
      dhcp4: true
```

Example (keeping your existing interface name, e.g. `enp3s0`):

```yaml
network:
  version: 2
  ethernets:
    enp3s0:
      match:
        macaddress: "aa:bb:cc:dd:ee:ff"
      dhcp4: true
```

Apply:

```bash
sudo netplan apply
```

### Issue B: NVIDIA driver updates break GPU access in containers

Recovery:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

### Issue C: systemctl daemon-reload causes GPU loss in running containers

On systems where systemd manages cgroups, running `daemon-reload` can cause containers to lose GPU access with NVML errors.

Recovery:

```bash
cd ~/ephemeral-llm
docker compose down
docker compose up -d
```

Or if using the systemd service:

```bash
sudo systemctl restart ephemeral.service
```

### Issue D: Model pull fails with "digest mismatch"

This can occur if a previous pull was interrupted or if there is a bug in the Ollama version.

Recovery:

```bash
docker exec -it ollama sh -c 'rm -rf /root/.ollama/models/blobs/*'
docker exec -it ollama ollama pull gemma3:12b-it-qat
```

If the error persists, try updating the Ollama image tag in docker-compose.yml to a newer version and redeploy.

## Success Check

From another device on your LAN:

```text
http://<YOUR_SERVER_IP>:8501
```

## Stopping and Starting

If you installed the systemd service

```bash
sudo systemctl stop ephemeral.service
sudo systemctl start ephemeral.service
```

Manual management

Pause the stack (keeps containers, does not remove them):

```bash
cd ~/ephemeral-llm && docker compose stop
```

Resume:

```bash
cd ~/ephemeral-llm && docker compose start
```

Teardown (removes containers, keeps named volumes unless you add `-v`):

```bash
cd ~/ephemeral-llm && docker compose down
```

## Troubleshooting

| Symptom                               | Likely cause                                         | Fix                                                                                                                   |
| ------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `nvidia-smi` fails on host            | Driver not installed or Secure Boot blocking modules | Reinstall driver, reboot, check `lsmod \| grep nvidia` and `sudo mokutil --sb-state`                                  |
| GPU works on host but not in Docker   | NVIDIA runtime not configured                        | `sudo nvidia-ctk runtime configure --runtime=docker`, restart Docker, rerun CUDA `nvidia-smi` test                    |
| `docker inspect ollama` shows null DeviceRequests | Compose did not request GPU               | Verify docker compose version supports `deploy.resources`, or add `runtime: nvidia` to ollama service                 |
| UI reachable locally but not from LAN | Firewall or wrong IP                                 | `hostname -I`, verify ufw rules, verify network profile                                                               |
| Ollama or Tika reachable from LAN     | Ports published beyond localhost                     | Fix compose ports to bind `127.0.0.1` only, recheck `ss -lntp`, run negative tests                                    |
| UI says model not found               | `gemma3-prod` not created                            | Run `docker exec -it ollama ollama list`, redo Phase 4                                                                |
| Containers don't start after reboot   | systemd service not enabled or wrong paths           | `systemctl status ephemeral.service`, verify `WorkingDirectory`, `User`, and `ExecStart`                              |
| NVML errors after daemon-reload       | GPU access lost due to cgroup changes                | Restart the stack: `docker compose down && docker compose up -d`                                                      |
| Model pull fails with digest mismatch | Interrupted download or Ollama bug                   | Clear blobs: `docker exec ollama sh -c 'rm -rf /root/.ollama/models/blobs/*'`, retry pull                             |
| Port already in use on compose up     | Native Ollama or other service using port            | Stop conflicting service or change published ports in compose file                                                    |
| apt update Signed-By conflict         | Old NVIDIA repo entries                              | Find and remove old files: `grep -l nvidia.github.io /etc/apt/sources.list.d/*`                                       |
