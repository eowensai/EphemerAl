# EphemerAl – Project Roadmap & Design Context
_Last updated: 2025-11-18_

## 1. The "Why"
EphemerAl fills a specific gap between technical tools (LM Studio) and expensive SaaS products (ChatGPT Enterprise/OpenWebUI).

**The Problems We Solve:**
1.  **The "Cloud Risk":** Schools and businesses are terrified of pasting PII (IEPs, contracts) into ChatGPT.
2.  **The "SaaS Tax":** "Good" AI costs $20/user/month. For a department of 50, that is unsustainable. EphemerAl creates a fixed cost based on hardware you already own.
3.  **The "Snooping" Factor:** Staff are hesitant to use AI if they think their boss will audit their chat history. Ephemerality guarantees a safe, judgment-free sandbox for drafting and brainstorming.

**The Solution:**
A local-only, single-server appliance. It holds no memory, costs nothing per user, and strictly keeps data on the LAN.

## 2. Design Principles

### Practical Privacy
*   We aren't paranoid; we are prudent. Data should never leave the network.
*   We don't store logs because we don't need them, and they are a liability.
*   **Ephemeral by Default:** When the tab closes, the session is gone. This protects the user (from snooping) and the org (from data retention policies).

### Low Friction, High Utility
*   **No Accounts:** We don't manage users. If you are on the network, you can use the tool.
*   **Simple UI:** One page. Chat + Attachments. No complex settings menus for the end user.
*   **Context Stuffing:** We use massive context windows (128k+) to let users "chat with documents" without complex databases.

### "One Box" Deployment
*   Designed to run on a single high-performance workstation (e.g., a gaming PC or workstation with NVIDIA GPU).
*   Administered by a "Power User," not necessarily a DevOps Engineer.

---

## 3. Architecture Snapshot
*   **Frontend:** Streamlit (Python) – Stateless, simple web interface.
*   **Backend:** Ollama – Manages the Gemma 3 models.
*   **Parsing:** Apache Tika (Legacy) / Python Native (Future) – Extracts text from files.
*   **Infrastructure:** Docker Compose – currently running via WSL2 on Windows.

---

## 4. Roadmap & Backlog

### ✅ Completed Capabilities (The "V1" Baseline)
- [x] **Multi-File Uploads:** Users can attach multiple docs/images at once.
- [x] **Forensic Ephemerality:** RAM-disk usage for temp files, logs disabled, anti-caching headers.
- [x] **Telemetry Disabled:** No shouting out to Streamlit servers.
- [x] **Context Injection:** Full text of documents is injected into the system prompt.

### 🛠️ Immediate Priorities (Quality of Life)
*Focus: Making the current tool nicer to use and easier to tweak.*

- [ ] **Show Parsed Text (UI Expander):**
    *   *Why:* Users blind-trust that the AI read their file. We should show the extracted text in a collapsed window so they can verify it.
- [ ] **Markdown Export:**
    *   *Why:* Since we delete everything on refresh, users need a "Save Receipt" button to download their work/chat history as a text file before they leave.
- [ ] **Centralized Config (`.env`):**
    *   *Why:* Currently, you have to edit `docker-compose.yml` to change the model name. Moving this to a `.env` file makes it safer for non-coders.

### 📦 Deployment & Packaging (The "Installer" Goal)
*Focus: Lowering the barrier to entry so a Principal or Office Manager can set this up.*

- [ ] **"Easy Start" Script:**
    *   *Why:* `docker compose up -d` is scary for some. A double-clickable batch file that checks if Docker is running and launches the app would be a huge win.
- [ ] **Update Utility:**
    *   *Why:* A script to "Pull latest updates" so the admin doesn't have to know git commands.
- [ ] **Hardware Auto-Detect:**
    *   *Why:* The app should default to "12B Model" if it detects 16GB VRAM, or "27B Model" if it detects 24GB+, rather than crashing.

### 🏗️ Architecture & Optimization
*Focus: Making the backend more efficient.*

- [ ] **Native Python Parsing (De-Tika):**
    *   *Why:* Running a Java server (Tika) consumes ~1GB RAM. Switching to Python libraries (MarkItDown) frees that RAM up for the AI model.
- [ ] **Context Trimming:**
    *   *Why:* If a user uploads a 500-page book, we need to gracefully truncate it or warn them, rather than crashing the container with an Out Of Memory error.

### 🛑 Out of Scope (The "Use OpenWebUI" Bucket)
*Features we intentionally will NOT build.*

*   **User Accounts / Passwords:** Use your network security (VPN/LAN) for access control.
*   **Chat History Database:** Defeats the purpose of the tool.
*   **Web Search:** Keeps the tool strictly offline and predictable.
*   **Complex Vector RAG:** We will rely on Gemma's long context window instead of managing a vector database.
