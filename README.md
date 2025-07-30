# EphemerAl

A lightweight, ephemeral (no chat history) self-hosted chat interface for interacting with local Large Language Models (LLMs).
This stack includes a clean front-end with support for document and image analysis. It was designed as a staff-training environment for people new to AI, while still providing utility for advanced users.

This was built as a passion project to meet a specific internal need. I leveraged AI to assist with coding, I'm not a developer by trade.
It wasn't designed for wide distribution, but since I couldn't find an existing solution that met our core requirements such as data security, no user accounts and multimodal input, I'm sharing a generalized version here in case it helps others with similar goals.

---

## Core Features of the solution:

* **🤖 AI Assistant:** Streaming chat interface using Google’s Gemma 3 IT QAT LLM served via Ollama.
* **📄 Document Upload:** Supports 100+ file types via Apache Tika, inserting full texts into queries.
* **🖼️ Multimodal Support:** Leverages Gemma 3's native support for images as part of queries.
* **🎨 Customizable Interface:** Clean, minimal UI with logo/image block for branding.
* **🔒 Ephemeral** No session data is stored. Everything runs locally on the server. No internet access is needed during use (though required for initial setup).

---

## Architecture

The application is fully containerized using Docker Compose and runs within Windows Subsystem for Linux (WSL2).
If you're unfamiliar with Docker or WSL2 but have Windows 11 Pro or Enterprise, you're covered, the deployment guide walks you through installing everything else.

* **Windows 11 Pro/Enterprise Host:**
   * **WSL2 (Ubuntu 24.04):**
       * **Docker Engine:** Manages containers holding supporting services.
           * **Ephemeral (`ephemeral-app`):** the Streamlit web interface
           * **Ollama Service (`ollama`):** local LLM service manager
           * **Apache Tika (`tika-server`):** document parsing engine

---

## System Requirements & Setup

Windows 11 Pro or Enterprise, fully updated
At least one discrete Nvidia GPU (30-series or newer recommended, with 12GB+ VRAM for Gemma 3 12B to perform well)
Latest WHQL Nvidia GPU driver (you can skip optional installs like the Control Panel)

## Deployment

Follow the steps in the included System Deployment Guide. Most commands can be copy/pasted into PowerShell.
The stack is configured to auto-launch at login.
A headless WSL setup was attempted but ultimately abandoned to prioritize operational use.

## Access the Interface:

From the server: open a browser and go to http://localhost:8501
From another machine on the network: go to http://<windows_host_ip_address>:8501

## Stopping the Application

Open an elevated (admin) PowerShell window on the host and run:
wsl --shutdown
To restart: either reboot and log back in, or run wsl again in PowerShell and leave the window open or minimized.

## Support

No official support is provided.
I recommend pasting error messages or issues into an AI assistant, along with a screenshot and a description of your technical level. This will help the AI tailor troubleshooting guidance more effectively.

## Known Issues

* The UI is not rendered correctly in mobile.
* Minimizing the sidebar (where the logo lives) can't be undone, you have to refresh to get it back. I chose to live with it than spend more time troubleshooting.
* User text will type under the arrow in the far right side of the text window for a bit before starting a new line.
* Attachments disappear (visually) after being submitted in a query.  Again, not a big deal to me so didn't spend more time on it.  Confirmed the full text remains in context the whole conversation (relying on Gemma 3's attention).
* There isn't a guardrail if the user submits a query larger than available ctx.  Gemma 3 supports large ctx, and I punted trying to handle this cleanly until/if it becomes a problem.

