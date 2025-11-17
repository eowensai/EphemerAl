# EphemerAl – Uber Backlog & Design Context
_Last updated: 2025-11-16_

## 1. What EphemerAl Is
EphemerAl is a self-hosted, local-only chat interface for LLMs, designed to run on a single box and serve multiple staff over a LAN. [https://github.com/eowensai/EphemerAl](https://github.com/eowensai/EphemerAl)

**Core properties:**
* Runs on the org’s hardware, not in the cloud.
* Uses Ollama to serve Gemma 3 models (4B/12B/27B, QAT variants when possible).
* Web UI is built in Streamlit; users access it via browser.
* Apache Tika extracts text from uploaded documents (PDF, Office, etc).
* Ephemeral by default: chat history lives only in memory and is cleared on refresh / “New Conversation”.
* Multimodal: users can upload images and documents along with text questions.

**Primary target audiences:**
* Schools / districts who want to discuss student data (IEPs, assessment results) without sending anything to third-party clouds.
* Small businesses who want internal AI assistance without per-user SaaS licensing.

### 1.1 Key user stories
* A teacher uploads a PDF of a reading passage and asks for differentiated questions for three reading levels.
* A special ed coordinator uploads IEPs and asks for suggested goals aligned to certain standards.
* An HR person uploads a policy document and asks for a summary and FAQ draft.
* A small biz owner uploads a contract and asks for a plain-language summary and risk flags.

## 2. Design Principles
These principles should guide all future changes (including tasks in the JSON backlog):

### Local only by default
* No calls to external APIs from the app, LLM, or document stack unless explicitly behind an opt-in “web augmentation” feature.
* Users and orgs run the system on their own hardware and network.

### Ephemeral by default
* No automatic conversation persistence.
* Any saving is explicit, opt-in, and clearly signaled in the UI.
* Logs must never contain PII or full prompts.

### Institution ready
* Must be acceptable in environments with FERPA/COPPA/GDPR/HR constraints.
* Clear separation between “School Mode (strict)” and “Business Mode (permissive)”.
* Strong default stance: privacy-first, safety-aware, and conservative.

### Single box, low ops
* Designed for a single machine (Windows + WSL today, future native Windows/macOS/ Linux variants).
* Admin is moderately technical, not a DevOps pro.
* Security and maintenance workflows must be realistic for one person with limited time.

### Simple UX, low cognitive load
* One main page, one primary task: chat with local AI + docs/images.
* Teachers should not need to think about models, context windows, or embeddings.
* Admin complexity is hidden behind config files and optional dashboards.

### Extensible architecture
* Backlog is designed to support evolution to:
* Better RAG (retrieval-augmented generation).
* Local safety / moderation.
* Packaging for Windows/macOS beyond WSL.
* Optional web augmentation via SearXNG.

## 3. Architecture Snapshot
**High-level components:**
* **UI:** Streamlit app (`ephemeral_app.py`) running in a container.
* **LLM backend:** Ollama (Gemma 3 family), running in a GPU-enabled container (or native on host in some packaging variants).
* **Document parsing:** Apache Tika server in its own container for 100+ file types.
* **Container orchestration:** Docker Compose (currently Linux in WSL2), with future variants for native Windows/macOS.
* **Security & network edge (planned):**
    * Caddy reverse proxy with TLS (mkcert), rate limiting, and structured logging.
    * Optional basic auth / IP gating at proxy layer.
* **Observability (planned):**
    * Netdata for host + GPU metrics.
* **Safety & moderation (planned):**
    * A central `SafetyService` module that handles:
    * Regex-based PII detection.
    * Optional Presidio NER PII enrichment.
    * Profanity/toxicity filtering.
    * NSFW image detection.

## 4. Audience Specific Requirements
### 4.1 Schools
#### Student data privacy
* No central logging or saving of student PII by default.
* School IT is the data controller; this project is only code, not a service.
* Must be configurable to a “strict” profile that:
    * Disables server-side conversation saving entirely.
    * Enforces conservative logging (metadata-only, no prompts or content).
    * Enforces short idle timeouts on shared devices.

#### Content safety
* Education-aware profanity/toxicity filtering.
* Strong NSFW image detection on uploads.
* Optional blocking of unsafe queries / outputs rather than just warning.

#### Accessibility
* Keyboard-only usage must be possible.
* Screen-reader users should be able to:
    * Discover the main regions (navigation, chat content, input form).
    * Hear new assistant messages announced without losing focus.
* WCAG 2.1 AA is the long-term target.

#### Shared device risk
* Auto-logout / auto-clear on inactivity.
* Guidance for OS-level kiosk/shared PC mode (Windows shared PC, browser profiles, etc).

### 4.2 Small businesses
* Less regulated than schools, but similar needs:
    * Local-only for client data and HR docs.
    * Option to save some conversations (e.g., HR templates, contract reviews) in “permissive mode”.
    * Templates for business tasks (emails, policies, proposals).
* Will value:
    * Clear backups and restore procedures.
    * A basic health/status dashboard.
    * Straightforward updates with low risk of breaking production.

## 5. Research Highlights (Appendices A–H)
These are human-readable digests of the eight deep-research docs that informed the backlog. They exist so future AIs (and humans) can reason about “why” beyond the individual tasks.

### Appendix A – Security & Maintenance (Self-Hosted AI Server)
* **Three-layer defense:**
    * **Host:** hardened Linux (Ubuntu/Debian), automatic security updates (unattended-upgrades), firewall, logrotate, backups.
    * **Container:** pinned images (no `:latest`), Tika version ≥ 3.2.2 to avoid known XXE/CVE, Docker logging configured to avoid disk fill.
    * **Network:** all internal services (Ollama, Tika, Streamlit UI) hidden behind an authenticating reverse proxy; nothing directly exposed on LAN/internet.
* **Update strategy:**
    * OS security updates: automated.
    * Container/app updates: notified, but human-approved (e.g., via Wud + docker-socket-proxy).
    * Periodic checks with `pip-audit` against `requirements.txt`.
* **Operational cadence:**
    * **Weekly:** check Wud, logs, container health.
    * **Monthly:** full `apt upgrade`, major container updates, `docker prune`.
* This maps to tasks like CFG-03, OPS-01, OPS-02, DEV-03, and the security-profile tasks under SEC-* and PROXY-*.

### Appendix B – Reverse Proxy & Observability
* **Reverse proxy choice: Caddy**
    * Simpler than Nginx/Traefik for solo-maintainer.
    * Handles TLS, basic auth, rate limiting, and structured logging via one `Caddyfile`.
    * Works well with local `mkcert` CA certificates.
* **Network topology:**
    * Caddy runs with `network_mode: host`, terminates TLS, and reverse-proxies to Streamlit on `localhost:8501`.
    * Ollama and Tika remain internal; only the UI is reachable via HTTPS.
    * Optional basic auth and IP-based rules for small LAN deployments.
* **Observability:**
    * Netdata container also runs in `network_mode: host` and `pid: host` for full host + GPU metrics.
    * Optionally exposed via Caddy with its own VHost and auth.
* This underpins PROXY-01, PROXY-02, PROXY-03 and connects to the security profile in SEC-*.

### Appendix C – Packaging & Distribution
* **WSL2-first is not ideal long term**
    * Requires admin rights, multiple reboots.
    * Confusing for Windows-centric admins.
    * AMD GPU support is better via native Windows Ollama than via WSL.
* **Windows direction (Epic):**
    * Native Ollama on Windows as the LLM service.
    * Containerized UI via a light engine (e.g., Rancher Desktop) connecting to `host.docker.internal:11434`.
    * Installer with pre-checks, optional silent install, and a small service that manages lifecycle.
* **macOS direction (Epic):**
    * Native Ollama app with Metal acceleration.
    * Tauri-based shell wrapping the web UI as a native `.app`.
    * Signed, notarized DMG distribution, with built-in updater.
* This is captured as “platform epics” PLAT-02 and PLAT-03, with current WSL docs reframed by PLAT-01.

### Appendix D – Accessibility (WCAG 2.1 AA)
* Streamlit’s “re-run on every interaction” model makes accessibility tricky:
    * Focus tends to jump to the top on each submit or state change.
    * DOM structure is `div` soup without clear landmarks.
    * Live regions often get torn down and rebuilt.
* **The accessibility strategy:**
    * **CSS layer**
        * Visually hidden utility classes.
        * High-contrast focus outlines.
        * Ensured color contrast for text and chat bubbles.
    * **Semantic structure**
        * Persistent ARIA landmarks:
        * `role="navigation"` for sidebar.
        * `role="main"` for chat content.
        * A clearly labeled chat input region (`role="form"` or similar).
        * A persistent `aria-live` region for announcing new messages and errors.
    * **JS “a11y corrector” component**
        * Injected via `st.components.v1.html`.
        * Runs on every re-render to:
        * Restore focus to the chat input.
        * Re-apply ARIA labels to input, send button, and file upload.
        * Write the last assistant message into the live region.
* This informs UI-03 and interacts with basic UI tasks like UI-01, UI-02, UI-05.

### Appendix E – On-Prem Content Moderation & PII Filtering
* **Goal:** fully local moderation pipeline with two gates (input and output), tunable by profile.
* **PII detection:**
    * **First line:** fast regex-based engine (e.g., DataFog or custom) for structured PII (emails, phone numbers, SSNs, credit cards, IPs).
    * **Optional upgrade:** Presidio/NER for unstructured PII (names, locations).
* **Text safety:**
    * Wordlist-based profanity filter (with strong customization).
    * Lightweight ML classifier for nuanced toxicity detection.
* **Image safety:**
    * Lightweight NSFW classifier (e.g., `nude.py` / NudeNet or similar CPU-friendly model).
* **Policy abstraction:**
    * A `SafetyPolicy` object per profile (strict vs permissive) feeding into a central `SafetyService`.
* This is embodied in SAFETY-01 through SAFETY-04 (plus SAFETY-02.5 for the optional Presidio layer) and used by RAG tasks (e.g., RAG-04 web augmentation).

### Appendix F – Privacy & Compliance Modes
* EphemerAl is code, not a SaaS service:
    * The deploying organization is the data controller.
    * Compliance is highly dependent on configuration and hosting environment.
* **Two high-level profiles:**
    * **1. Strict (“School Mode”)**
        * No server-side conversation saving.
        * Logging limited to high-level metadata with no PII.
        * App expects to sit behind an authenticated proxy or password gating.
        * Short idle timeouts; strongly recommended for shared devices.
    * **2. Permissive (“SMB/HR Mode”)**
        * Allows optional conversation saving (explicit opt-in per thread).
        * May allow richer debugging logs, but still PII-avoiding by default.
        * Longer session timeouts if appropriate; still encourages human review of important decisions.
* This is what SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, and UI-06 are about.

### Appendix G – RAG (Retrieval-Augmented Generation)
* **Constraints:**
    * Single server, ephemeral per session.
    * No persistent vector DB; everything lives in memory.
    * Existing Tika integration for extraction.
* **Recommended pattern:**
    * **Chunking:**
        * Use recursive text splitting on Tika’ed text into ~1–2k character chunks with overlap.
    * **Embeddings:**
        * Use a small local embedding model (e.g., `embedding-gemma` via Ollama).
    * **Index:**
        * Build a FAISS HNSW index per session in memory.
    * **Retrieval:**
        * For each user query, embed the question, retrieve top-K chunks, and inject them into the prompt as context.
* All RAG state is stored in `st.session_state` and discarded at session end.
* This is implemented gradually by RAG-01.1–RAG-01.5, plus RAG-02 (citations & preview), RAG-03 (optional hierarchical summarization), and DOC-03 (OCR fallback that feeds into the same pipeline).

### Appendix H – LLM Defaults & Hardware-Aware Settings
* **LLM baseline:**
    * Use Gemma 3 QAT models where possible (`*-it-qat` variants) for quality vs VRAM tradeoff.
    * Pick model and context length based on VRAM (NVIDIA) or unified memory (Apple Silicon).
* **Guidelines:**
    * **24 GB NVIDIA:** Gemma 3 27B QAT, moderate ctx.
    * **16–12 GB NVIDIA:** Gemma 3 12B QAT, 4–8k ctx.
    * **≤ 8 GB:** 4B QAT with smaller ctx.
* **For Apple Silicon:**
    * **32 GB:** 27B QAT with conservative ctx.
    * **16–24 GB:** 12B with medium ctx.
    * **8 GB:** 4B QAT with small ctx.
* **Vision:**
    * Disabled by default due to extra VRAM overhead.
    * When enabled, auto-reduce `num_ctx` and mark as “experimental”.
* This is informs LLM-01, LLM-02, LLM-03, and LLM-04.

## 6. Backlog (Machine Readable JSON)
The JSON below is the canonical backlog: each item has an ID, name, value score, difficulty score, estimated time, rationale, and dependencies. This is what you should feed to other models when you want prioritization, scheduling, or “pick a task for this weekend” type help. The JSON backlog uses a simple schema so both humans and tooling can reason about it.

### Core fields
**id**
* String identifier like "RAG-01.3"
* Pattern: `CATEGORY-NN[.substep]`
* Used for dependencies and cross-referencing in docs.

**title**
* Short human-readable label for the task.
* 1–2 lines max, no line breaks.

**value\_to\_user\_base**
* Integer from 0 to 100.
* “How much does this help EphemerAl’s *actual* target users (schools + SMBs) if implemented correctly?”
* **Anchor points:**
    * **0–20:** Almost no noticeable user benefit, very internal / plumbing only.
    * **30–40:** Nice to have, polishing or niche use cases.
    * **50–60:** Solid improvement, users will notice but can live without it.
    * **7S0–80:** High value, directly improves core workflows or trust.
    * **90–100:** Critical or flagship features (security must-haves, RAG core, auth, etc.).

**difficulty\_to\_vibe\_code**
* Integer from 0 to 100.
* “How hard is this for one non-coder vibe-coding with AI help?”
* **Think relative complexity, not exact hours:**
    * **0–10:** Trivial config / copy-paste change.
    * **20–30:** Small, localized change (one file, limited edge cases).
    * **40–50:** Medium feature or refactor, multiple files, some design choices.
    * **60–70:** Large feature or risky refactor, multiple moving parts.
    * **80–100:** Epic level, multi-technology, or long-running work.

**time\_to\_vibe\_code\_and\_test**
* Integer from 0 to 100.
* “Relative time/effort for implementation *plus* basic testing, assuming you’re working a couple of hours here and there.”
* This is *ordinal*, not literal hours:
    * **~10–20:** One short evening.
    * **~30–40:** A few evenings / one good weekend.
    * **~50–60:** Several weeks of part-time effort.
    * **~70–80:** Multi-week project with iteration and debugging.
    * **~90–100:** Multi-month, epic-level effort.

**value\_rationale**
* Free-text explanation of why the feature matters for schools/SMBs.

**difficulty\_rationale**
* Free-text explanation of what makes this task easy/hard (tech, risk, unknowns).

**time\_rationale**
* Free-text explanation of why the estimated time score is what it is (testing complexity, number of environments, etc.).

**depends\_on**
* List of other task IDs (strings).
* Semantics: “These tasks should be *effectively done* before this one is tackled.”
* Used by planners to:
    * Avoid building on missing foundations.
    * Detect epics and natural ordering.
* Should *not* contain cycles (A depends on B, B depends on A).


<<<<<<<<COPY/PASTE Below this line>>>>>>

```json
{
  "tasks": [
    {
      "id": "CFG-01",
      "title": "Centralize configuration into `.env`",
      "value_to_user_base": 80,
      "value_rationale": "A single env-based configuration surface makes it much easier for school IT and SMB admins to tune models, privacy modes, and features without editing Python or Compose files, which directly reduces misconfiguration risk.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "This requires auditing existing config usage, introducing dotenv loading, and updating Compose and app references, but the codebase is relatively small and the patterns are straightforward.",
      "time_to_vibe_code_and_test": 30,
      "time_rationale": "Implementation plus testing across a few deployment variants should fit into one or two focused evenings of part-time work.",
      "depends_on": []
    },
    {
      "id": "CFG-02",
      "title": "Add container healthchecks and startup ordering",
      "value_to_user_base": 75,
      "value_rationale": "Reliable startup behavior avoids confusing failures where teachers see a broken UI because Ollama or Tika are still coming up, improving trust in the tool.",
      "difficulty_to_vibe_code": 30,
      "difficulty_rationale": "Healthchecks and depends_on wiring in Compose plus a simple app health endpoint are conceptually simple but require care to handle edge cases cleanly.",
      "time_to_vibe_code_and_test": 25,
      "time_rationale": "Can likely be implemented and smoke-tested with a few container restarts and failure simulations in a single short session.",
      "depends_on": []
    },
    {
      "id": "CFG-03",
      "title": "Harden Docker images and logging",
      "value_to_user_base": 90,
      "value_rationale": "Pinning image versions, avoiding known Tika CVEs, and configuring log rotation directly reduce operational and security risk for schools and SMBs running this long term.",
      "difficulty_to_vibe_code": 40,
      "difficulty_rationale": "Requires understanding Docker image tags, host-level daemon configuration, and documenting the changes clearly, but involves little application logic.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Updating Compose, daemon.json, and docs plus verifying rotations and pinned tags in a test environment is a couple of evenings of part-time effort.",
      "depends_on": []
    },
    {
      "id": "CFG-04",
      "title": "Multi-stage app Dockerfile & non-root runtime",
      "value_to_user_base": 70,
      "value_rationale": "Smaller, non-root images reduce attack surface and make deployments more robust, which matters in adversarial document environments like schools.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Designing a clean multi-stage Dockerfile, handling build-time dependencies, and correctly switching to a non-root user without breaking file permissions takes some Docker expertise.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Expect multiple build-run cycles and adjustments to get the image lean and working across environments, likely spanning a few evenings.",
      "depends_on": []
    },
    {
      "id": "CFG-05",
      "title": "Streamlit server configuration file",
      "value_to_user_base": 70,
      "value_rationale": "Centralizing server-level settings like upload size, CORS, and XSRF reduces subtle production issues and aligns runtime behavior with documented expectations for admins.",
      "difficulty_to_vibe_code": 30,
      "difficulty_rationale": "Creating config.toml and threading key values through env variables is straightforward, though it requires reading Streamlit docs carefully to avoid surprises.",
      "time_to_vibe_code_and_test": 25,
      "time_rationale": "Implementing the config file and verifying behavior for uploads and CORS across a couple of browsers should fit in roughly one evening.",
      "depends_on": ["CFG-01"]
    },
    {
      "id": "SEC-01",
      "title": "Implement `EPHEMERAL_PROFILE` (strict vs permissive modes)",
      "value_to_user_base": 95,
      "value_rationale": "A clear strict versus permissive profile switch lets schools pick a FERPA-friendly posture while SMBs can enable more convenience, making the product viable in regulated environments.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "This touches startup logic, logging, session behavior, and UI flags, so it requires a careful pass over multiple parts of the app to avoid inconsistent modes.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Designing profiles, implementing them, and then manually testing both modes for regressions will likely take several focused evenings.",
      "depends_on": []
    },
    {
      "id": "SEC-02",
      "title": "Logging policy and implementation (no content logging)",
      "value_to_user_base": 90,
      "value_rationale": "Strong guarantees that prompts, document text, and PII never hit logs are central to trust for school districts and HR-heavy SMBs.",
      "difficulty_to_vibe_code": 40,
      "difficulty_rationale": "Implementing a wrapper with structured logging and redaction is conceptually simple but demands careful review of all logging call sites to ensure nothing leaks.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Coding the wrapper is quick but exhaustively testing log output under failures and different profiles takes another evening or two.",
      "depends_on": ["SEC-01"]
    },
    {
      "id": "SEC-03",
      "title": "Conversation saving as explicit opt-in (permissive mode)",
      "value_to_user_base": 70,
      "value_rationale": "Server-side transcript saving is valuable in permissive deployments where staff want to reuse outputs, while explicit opt-in keeps ephemerality by default intact.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Requires UI controls, session wiring, secure file handling, optional encryption, and careful interaction with profile logic, which adds moving parts.",
      "time_to_vibe_code_and_test": 50,
      "time_rationale": "Designing the UX, implementing, and then validating correct behavior in both profiles with multiple conversations will span several evenings or a couple of weekends.",
      "depends_on": ["SEC-01"]
    },
    {
      "id": "SEC-04",
      "title": "Auth integration strategy (proxy-first, app fallback)",
      "value_to_user_base": 95,
      "value_rationale": "Reliable authentication that integrates with existing SSO is critical for most school and SMB deployments, and a fallback password mode still covers small internal use.",
      "difficulty_to_vibe_code": 60,
      "difficulty_rationale": "Designing app behavior that cooperates with reverse proxies, implementing a password gate, and documenting multiple auth patterns takes nontrivial security and deployment knowledge.",
      "time_to_vibe_code_and_test": 60,
      "time_rationale": "End-to-end testing across proxy and fallback modes, including misconfiguration scenarios, will likely require multiple weekends of part-time effort.",
      "depends_on": ["SEC-01"]
    },
    {
      "id": "SEC-05",
      "title": "Shared device protections (auto-logout & kiosk guidance)",
      "value_to_user_base": 85,
      "value_rationale": "Automatic timeouts and guidance for kiosk or shared PC setups directly mitigate the risk of sensitive student or HR content being visible to the wrong person.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "Implementing session idle tracking in Streamlit and documenting OS-level measures is moderate complexity but confined to a few code paths and docs.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Coding the timeout and verifying it behaves correctly under normal use and long idles, plus writing guidance, should take a few evenings.",
      "depends_on": ["SEC-01"]
    },
    {
      "id": "PROXY-01",
      "title": "Add Caddy reverse proxy service",
      "value_to_user_base": 85,
      "value_rationale": "A TLS-terminating front door with rate limiting and proper logging makes EphemerAl safer to expose on school or SMB networks and simplifies admin workflows.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Requires adding and wiring a new service in Compose, writing a nontrivial Caddyfile, handling mkcert certificates, and ensuring headers and ports are correct.",
      "time_to_vibe_code_and_test": 45,
      "time_rationale": "Standing up Caddy, iterating on config, and validating TLS, logs, and proxy behavior on different clients will likely take several evenings.",
      "depends_on": []
    },
    {
      "id": "PROXY-02",
      "title": "Optional IP-aware basic auth at proxy",
      "value_to_user_base": 70,
      "value_rationale": "IP-aware basic auth gives smaller deployments a simple way to protect access without deploying a full SSO stack, which is common in SMBs and small schools.",
      "difficulty_to_vibe_code": 30,
      "difficulty_rationale": "This is primarily Caddyfile work plus some documentation about password hashing and rotation, which is reasonably straightforward once Caddy is in place.",
      "time_to_vibe_code_and_test": 25,
      "time_rationale": "Implementing rules and validating from LAN and non-LAN addresses can fit into a single short working session.",
      "depends_on": ["PROXY-01"]
    },
    {
      "id": "PROXY-03",
      "title": "Add Netdata for host & GPU observability",
      "value_to_user_base": 70,
      "value_rationale": "An easy dashboard for CPU, GPU, and container health helps admins debug complaints that the system is slow without deep observability expertise.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "Adding Netdata to Compose with host networking and wiring optional proxying is mostly configuration work but touches host resources and permissions.",
      "time_to_vibe_code_and_test": 30,
      "time_rationale": "Deploying Netdata, tuning its mounts, and confirming useful metrics show up is a couple of evenings of part-time effort.",
      "depends_on": ["PROXY-01"]
    },
    {
      "id": "LLM-01",
      "title": "Hardware auto-detection and model defaults",
      "value_to_user_base": 80,
      "value_rationale": "Automatically choosing safe model and context defaults based on hardware greatly reduces out-of-memory errors for non-expert admins.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Requires shelling out to detect VRAM and RAM in different environments, mapping that into sensible defaults, and integrating with config without breaking overrides.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Designing the mapping and testing across at least CPU-only, midrange GPU, and high-end setups will likely take several evenings.",
      "depends_on": []
    },
    {
      "id": "LLM-02",
      "title": "Context length guardrail & trimming",
      "value_to_user_base": 85,
      "value_rationale": "Preventing context overruns protects users from confusing failures when combining long conversations with large documents or web context.",
      "difficulty_to_vibe_code": 50,
      "difficulty_rationale": "Integrating a tokenizer, estimating token counts, and implementing safe trimming that preserves recent and relevant context is moderately complex application logic.",
      "time_to_vibe_code_and_test": 45,
      "time_rationale": "Expect multiple test cycles with different document sizes and histories to confirm behavior, which likely spans a few evenings.",
      "depends_on": []
    },
    {
      "id": "LLM-03",
      "title": "System prompt templating & deployment modes",
      "value_to_user_base": 75,
      "value_rationale": "Tailoring the system prompt to education versus business contexts helps align model behavior with policy expectations without changing models.",
      "difficulty_to_vibe_code": 30,
      "difficulty_rationale": "Extending the existing templating and adding a simple mode selector is fairly straightforward but must be wired cleanly into config and startup.",
      "time_to_vibe_code_and_test": 25,
      "time_rationale": "Updating the template, adding variables, and validating outputs in both modes should fit into about an evening of work.",
      "depends_on": ["SEC-01"]
    },
    {
      "id": "LLM-04",
      "title": "Vision toggle with safe defaults",
      "value_to_user_base": 60,
      "value_rationale": "Vision support is attractive but not essential for most users, and making it opt-in with safe defaults prevents stability issues on smaller GPUs.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "Requires wiring config or UI flags, choosing conservative context settings for vision modes, and updating docs and warnings, but little deep algorithm work.",
      "time_to_vibe_code_and_test": 30,
      "time_rationale": "Implementing toggles and validating behavior on both vision-enabled and text-only setups can be done in a couple of evenings.",
      "depends_on": ["LLM-01"]
    },
    {
      "id": "LLM-05",
      "title": "Optional dynamic model selection via UI",
      "value_to_user_base": 65,
      "value_rationale": "Allowing advanced users to switch between smaller and larger models without restart is convenient but most classroom users can live with one well-chosen default.",
      "difficulty_to_vibe_code": 40,
      "difficulty_rationale": "Involves querying Ollama, managing state in Streamlit, handling model load failures, and designing a sidebar UI without confusing novices.",
      "time_to_vibe_code_and_test": 45,
      "time_rationale": "Design, implementation, and thorough testing with multiple installed models and failure modes will span several evenings.",
      "depends_on": []
    },
    {
      "id": "RAG-01",
      "title": "Epic: Basic in-memory RAG pipeline for uploads",
      "value_to_user_base": 95,
      "value_rationale": "A solid RAG pipeline is central to answering questions over long policies, IEPs, and contracts, which is a core use case for schools and SMBs.",
      "difficulty_to_vibe_code": 75,
      "difficulty_rationale": "Coordinating extraction, chunking, embedding, indexing, and prompt injection in a robust way requires careful design across multiple modules.",
      "time_to_vibe_code_and_test": 80,
      "time_rationale": "Even broken into sub-tasks, achieving a stable pipeline and iterating on edge cases across different document types will take many weeks of part-time work.",
      "depends_on": []
    },
    {
      "id": "RAG-01.1",
      "title": "Tika integration & text extraction",
      "value_to_user_base": 80,
      "value_rationale": "Reliable text extraction from many document formats is a prerequisite for any document-aware assistance teachers and staff will rely on.",
      "difficulty_to_vibe_code": 40,
      "difficulty_rationale": "Abstracting Tika into a clean helper with proper error handling is moderate complexity but builds on the existing Tika usage.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Implementing the abstraction and testing across a handful of representative documents should take a couple of evenings.",
      "depends_on": []
    },
    {
      "id": "RAG-01.2",
      "title": "Text chunking",
      "value_to_user_base": 85,
      "value_rationale": "Chunking is a key step that makes large documents queryable without blowing context limits, which directly improves real-world usefulness.",
      "difficulty_to_vibe_code": 40,
      "difficulty_rationale": "Choosing chunk sizes, overlaps, and implementing or integrating a splitter is moderate effort but the algorithmic patterns are well known.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Coding the splitter and validating chunk quality on diverse documents can be done over a couple of evenings.",
      "depends_on": ["RAG-01.1"]
    },
    {
      "id": "RAG-01.3",
      "title": "Embedding & vector store",
      "value_to_user_base": 90,
      "value_rationale": "Embeddings plus FAISS indexing are what make retrieval over many chunks fast and scalable for multiple large documents.",
      "difficulty_to_vibe_code": 60,
      "difficulty_rationale": "Integrating a local embedding model, managing FAISS indexes per session, and handling failure modes requires more advanced understanding of both LLM and vector tooling.",
      "time_to_vibe_code_and_test": 55,
      "time_rationale": "Expect several evenings or a couple of weekends to wire this up, tune parameters, and test performance on realistic document loads.",
      "depends_on": ["RAG-01.1", "RAG-01.2"]
    },
    {
      "id": "RAG-01.4",
      "title": "Retriever logic",
      "value_to_user_base": 85,
      "value_rationale": "The retriever is what turns the index into relevant context for each question, directly affecting answer quality for end users.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Query embedding, FAISS search, and metadata handling are straightforward conceptually but must be implemented carefully to avoid mismatches and bugs.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Coding and iterating on retrieval quality with different k values and documents will likely take a few evenings.",
      "depends_on": ["RAG-01.3"]
    },
    {
      "id": "RAG-01.5",
      "title": "Prompt wiring with retrieved chunks",
      "value_to_user_base": 90,
      "value_rationale": "Injecting only relevant chunks instead of entire documents makes answers grounded and keeps context usage under control, which users will feel as reliability.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Requires modifying prompt construction and ensuring chat history, context chunks, and system instructions interact cleanly without breaking existing flows.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Implementing the wiring and then testing on multiple conversation and document combinations should take several evenings.",
      "depends_on": ["RAG-01.4"]
    },
    {
      "id": "RAG-02",
      "title": "Expose citations & doc preview",
      "value_to_user_base": 80,
      "value_rationale": "Clickable citations and previews build trust by letting teachers and staff see exactly where answers came from in uploaded documents.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Involves UI changes, passing metadata through the pipeline, and building a mini viewer, which is moderate but not trivial work.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Designing the UI elements and validating them across different screen sizes and document types will require a few evenings.",
      "depends_on": ["RAG-01.4", "RAG-01.5"]
    },
    {
      "id": "RAG-03",
      "title": "Optional hierarchical summarization (deep mode)",
      "value_to_user_base": 60,
      "value_rationale": "Deep summarization helps with very large collections and big-picture questions, but many deployments can live without it initially.",
      "difficulty_to_vibe_code": 55,
      "difficulty_rationale": "Building and managing multi-level summaries with extra LLM calls and integrating them into retrieval logic adds nontrivial complexity and cost tuning.",
      "time_to_vibe_code_and_test": 55,
      "time_rationale": "Designing the hierarchy, implementing, and then evaluating quality and performance will take multiple weekends of part-time work.",
      "depends_on": ["RAG-01.2", "RAG-01.3", "RAG-01.4", "RAG-01.5"]
    },
    {
      "id": "RAG-04",
      "title": "Optional web augmentation via local search gateway (SearXNG)",
      "value_to_user_base": 80,
      "value_rationale": "Breaking the knowledge cutoff via a local search gateway provides high value for some curricula and business questions while preserving a privacy-respecting architecture.",
      "difficulty_to_vibe_code": 70,
      "difficulty_rationale": "Requires adding and configuring SearXNG, integrating web results into the RAG pipeline, and enforcing safety checks on outbound and inbound content.",
      "time_to_vibe_code_and_test": 75,
      "time_rationale": "End-to-end design, integration, and careful testing under strict and permissive profiles will likely span many weeks of part-time work.",
      "depends_on": ["SAFETY-01", "SAFETY-02", "SAFETY-03", "RAG-01.3", "RAG-01.4", "RAG-01.5"]
    },
    {
      "id": "DOC-01",
      "title": "Non-image upload limits & error handling",
      "value_to_user_base": 80,
      "value_rationale": "Clear limits and friendly errors for large or broken documents prevent confusing failures and protect the system from being overwhelmed.",
      "difficulty_to_vibe_code": 30,
      "difficulty_rationale": "Aligning app-side size checks with Streamlit config and wrapping Tika failures in user-friendly messages is conceptually straightforward.",
      "time_to_vibe_code_and_test": 25,
      "time_rationale": "Implementing the checks and testing with oversized, valid, and corrupt documents can be done in about an evening.",
      "depends_on": ["CFG-05"]
    },
    {
      "id": "DOC-02",
      "title": "Image resizing & base64 caching",
      "value_to_user_base": 65,
      "value_rationale": "Downscaling and caching images reduces memory and bandwidth issues when staff upload screenshots or photos, improving stability on modest hardware.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "Integrating Pillow, deciding resizing thresholds, and managing base64 storage in session state is moderate implementation work.",
      "time_to_vibe_code_and_test": 30,
      "time_rationale": "Coding the pipeline and testing with various resolutions and multiple simultaneous images should take a couple of evenings.",
      "depends_on": []
    },
    {
      "id": "DOC-03",
      "title": "Optional OCR fallback for scanned PDFs",
      "value_to_user_base": 75,
      "value_rationale": "OCR support for scanned forms and photocopied documents is very useful in education and HR workflows where such PDFs are common.",
      "difficulty_to_vibe_code": 60,
      "difficulty_rationale": "Integrating an OCR engine, managing timeouts, and feeding results into the RAG pipeline with appropriate metadata requires significant work and tuning.",
      "time_to_vibe_code_and_test": 60,
      "time_rationale": "Choosing an OCR tool, integrating, and testing on a wide variety of scanned documents will likely take multiple weekends of part-time effort.",
      "depends_on": ["RAG-01.1", "RAG-01.2", "RAG-01.3", "RAG-01.4", "RAG-01.5"]
    },
    {
      "id": "UI-01",
      "title": "Fix chat input overlay issue",
      "value_to_user_base": 50,
      "value_rationale": "Fixing the input overlay bug improves everyday usability and reduces user frustration during long prompts, though it does not change core capabilities.",
      "difficulty_to_vibe_code": 15,
      "difficulty_rationale": "This is primarily a CSS and layout tweak using more stable selectors, with minimal logic changes.",
      "time_to_vibe_code_and_test": 15,
      "time_rationale": "Can likely be implemented and verified across common browsers in a single short session.",
      "depends_on": []
    },
    {
      "id": "UI-02",
      "title": "Remove remote Google Fonts in privacy-strict mode",
      "value_to_user_base": 70,
      "value_rationale": "Eliminating external font calls is important for environments that require completely offline behavior or strict outbound traffic control.",
      "difficulty_to_vibe_code": 20,
      "difficulty_rationale": "Adjusting CSS to remove or conditionally disable remote fonts and rely on system fonts is straightforward but must be tested visually.",
      "time_to_vibe_code_and_test": 15,
      "time_rationale": "Updating theme.css and verifying the look in strict and permissive modes should fit within a single evening.",
      "depends_on": []
    },
    {
      "id": "UI-03",
      "title": "Basic accessibility (WCAG) pass: ARIA structure & focus",
      "value_to_user_base": 80,
      "value_rationale": "Improving keyboard and screen reader accessibility is significant for staff with disabilities and aligns with school accessibility obligations.",
      "difficulty_to_vibe_code": 55,
      "difficulty_rationale": "Implementing ARIA landmarks, live regions, focus management, and CSS utilities in a rerun-heavy Streamlit environment is nontrivial.",
      "time_to_vibe_code_and_test": 55,
      "time_rationale": "Designing, implementing, and testing with keyboard-only navigation and at least one screen reader will take multiple weekends of part-time effort.",
      "depends_on": []
    },
    {
      "id": "UI-04",
      "title": "Domain-specific prompt templates",
      "value_to_user_base": 70,
      "value_rationale": "Built-in templates reduce prompt paralysis and showcase useful patterns for teachers and business users, increasing perceived value.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "Requires designing a small template library, building a sidebar selector, and wiring it into the chat input without overcomplicating the UI.",
      "time_to_vibe_code_and_test": 30,
      "time_rationale": "Implementing the data structure, UI, and basic testing with a handful of templates can be done over a couple of evenings.",
      "depends_on": []
    },
    {
      "id": "UI-05",
      "title": "Graceful error handling for backend failures",
      "value_to_user_base": 85,
      "value_rationale": "Replacing stack traces with friendly, actionable messages significantly improves the experience for non-technical staff when services go down.",
      "difficulty_to_vibe_code": 40,
      "difficulty_rationale": "Requires identifying common failure modes, wrapping calls in appropriate try blocks, and ensuring profile-aware messaging throughout the app.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Implementing handlers and then deliberately breaking services in test environments to verify messaging will take several evenings.",
      "depends_on": ["SEC-01"]
    },
    {
      "id": "UI-06",
      "title": "Export current conversation to Markdown (ephemeral client-side)",
      "value_to_user_base": 80,
      "value_rationale": "Client-side export lets users keep key outputs like lesson plans or contract drafts without changing the server's ephemerality posture.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "Building a Markdown representation of chat history and wiring it into a download button is moderate effort but conceptually clear.",
      "time_to_vibe_code_and_test": 30,
      "time_rationale": "Implementing the export and testing it across browsers and profiles should fit into a couple of evenings.",
      "depends_on": []
    },
    {
      "id": "SAFETY-01",
      "title": "Implement pluggable SafetyService scaffolding",
      "value_to_user_base": 90,
      "value_rationale": "A centralized safety and policy engine is foundational for enforcing PII filtering, profanity rules, and web safety consistently across the app.",
      "difficulty_to_vibe_code": 55,
      "difficulty_rationale": "Designing policies, interfaces, and integration points into the chat loop requires careful thought to avoid tight coupling and regressions.",
      "time_to_vibe_code_and_test": 50,
      "time_rationale": "Architecture design, implementation, and regression testing of basic flows will likely take multiple evenings or a couple of weekends.",
      "depends_on": []
    },
    {
      "id": "SAFETY-02",
      "title": "Local PII detection (regex-based)",
      "value_to_user_base": 85,
      "value_rationale": "Fast regex-based detection of structured PII covers a large portion of privacy risk and is especially important in education and HR contexts.",
      "difficulty_to_vibe_code": 50,
      "difficulty_rationale": "Selecting or curating regexes, integrating a high-performance engine, and tuning false positive behavior is moderately complex work.",
      "time_to_vibe_code_and_test": 45,
      "time_rationale": "Implementing detectors and testing across representative prompts and documents will span several evenings.",
      "depends_on": ["SAFETY-01"]
    },
    {
      "id": "SAFETY-02.5",
      "title": "Optional NER-based PII detection (Presidio)",
      "value_to_user_base": 70,
      "value_rationale": "Adding NER-based detection improves recall for names and locations, which some high-sensitivity deployments will value.",
      "difficulty_to_vibe_code": 60,
      "difficulty_rationale": "Integrating Presidio and spaCy, managing models, and fitting them cleanly into the existing safety pipeline introduces significant dependency and performance complexity.",
      "time_to_vibe_code_and_test": 60,
      "time_rationale": "Installing models, optimizing performance, and validating behavior across many examples will likely take multiple weekends of part-time effort.",
      "depends_on": ["SAFETY-01", "SAFETY-02"]
    },
    {
      "id": "SAFETY-03",
      "title": "Local profanity / toxicity filter",
      "value_to_user_base": 80,
      "value_rationale": "Blocking or warning on inappropriate language is especially important for classroom use and HR-adjacent scenarios.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Combining wordlist filters with a simple classifier and exposing profile-dependent actions is moderate work with policy and tuning aspects.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Implementing and iterating on allow and deny lists plus classifier thresholds across test prompts will take several evenings.",
      "depends_on": ["SAFETY-01"]
    },
    {
      "id": "SAFETY-04",
      "title": "NSFW image classifier (education-first default)",
      "value_to_user_base": 80,
      "value_rationale": "Local NSFW image detection reduces the risk of inappropriate images in school environments without sending data to external services.",
      "difficulty_to_vibe_code": 55,
      "difficulty_rationale": "Selecting a lightweight model or library, integrating it into the upload path, and handling false positives and negatives requires care.",
      "time_to_vibe_code_and_test": 50,
      "time_rationale": "Experimenting with classifiers, tuning thresholds, and testing with diverse benign and problematic images will span multiple evenings or weekends.",
      "depends_on": ["SAFETY-01"]
    },
    {
      "id": "PLAT-01",
      "title": "Move away from WSL-first messaging",
      "value_to_user_base": 60,
      "value_rationale": "Clarifying that WSL2 is one path rather than the only path avoids scaring off admins who prefer native Windows or macOS options.",
      "difficulty_to_vibe_code": 15,
      "difficulty_rationale": "This is primarily editing README and deployment docs to adjust framing and expectations.",
      "time_to_vibe_code_and_test": 15,
      "time_rationale": "Can be written and reviewed in a single short documentation session.",
      "depends_on": []
    },
    {
      "id": "PLAT-02",
      "title": "Epic: Windows hybrid packaging concept",
      "value_to_user_base": 90,
      "value_rationale": "A more native Windows experience with an installer and managed services would make EphemerAl accessible to many more school and SMB admins.",
      "difficulty_to_vibe_code": 85,
      "difficulty_rationale": "Designing a hybrid architecture, installer flow, service management, and integration with native Ollama is a large cross-cutting engineering effort.",
      "time_to_vibe_code_and_test": 90,
      "time_rationale": "Even at the design and prototyping level, this will span months of part-time work and require numerous iterations and test deployments.",
      "depends_on": ["PLAT-01"]
    },
    {
      "id": "PLAT-03",
      "title": "Epic: macOS Apple Silicon native client design",
      "value_to_user_base": 85,
      "value_rationale": "A native macOS app with Metal-accelerated Ollama fits many school fleets and removes Docker friction on that platform.",
      "difficulty_to_vibe_code": 85,
      "difficulty_rationale": "Defining a Tauri-based app, integrating with Ollama.app, and planning signing, notarization, and update flows is a major multi-technology design challenge.",
      "time_to_vibe_code_and_test": 90,
      "time_rationale": "Like the Windows epic, this will take months of part-time exploration and prototyping before reaching a stable design.",
      "depends_on": ["PLAT-01"]
    },
    {
      "id": "OPS-01",
      "title": "Security & maintenance runbook",
      "value_to_user_base": 80,
      "value_rationale": "A realistic maintenance checklist helps moderately technical admins keep the system secure over time without guessing or over-engineering.",
      "difficulty_to_vibe_code": 30,
      "difficulty_rationale": "This is mostly thoughtful documentation that synthesizes existing security and ops practices into concrete steps.",
      "time_to_vibe_code_and_test": 30,
      "time_rationale": "Gathering, structuring, and reviewing the runbook should take a few focused documentation sessions.",
      "depends_on": []
    },
    {
      "id": "OPS-02",
      "title": "Backups and restore testing",
      "value_to_user_base": 85,
      "value_rationale": "Clear backup and restore procedures protect organizations from data loss and make recovery from failures far less painful.",
      "difficulty_to_vibe_code": 35,
      "difficulty_rationale": "Requires identifying key assets, scripting or documenting backup steps, and designing simple restore tests, but involves little complex code.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Writing the guidance and performing at least one test restore in a lab environment will likely take several evenings.",
      "depends_on": []
    },
    {
      "id": "DEV-01",
      "title": "Minimal pytest suite & CI smoke test",
      "value_to_user_base": 75,
      "value_rationale": "Basic tests and CI catch regressions before they reach admins, improving reliability despite limited developer time.",
      "difficulty_to_vibe_code": 40,
      "difficulty_rationale": "Setting up pytest, crafting a few focused tests, and wiring GitHub Actions requires some tooling knowledge but is contained in scope.",
      "time_to_vibe_code_and_test": 35,
      "time_rationale": "Initial test creation and getting CI green will likely take a few evenings of setup and iteration.",
      "depends_on": []
    },
    {
      "id": "DEV-02",
      "title": "Epic: Code modularization",
      "value_to_user_base": 85,
      "value_rationale": "Splitting the monolithic app into modules makes future features like advanced RAG and safety much easier to implement and maintain.",
      "difficulty_to_vibe_code": 70,
      "difficulty_rationale": "Requires refactoring core logic into multiple files while preserving behavior and managing imports, which can easily introduce subtle bugs.",
      "time_to_vibe_code_and_test": 70,
      "time_rationale": "Planning and executing the refactor across several modules will take many evenings and require repeated regression testing.",
      "depends_on": []
    },
    {
      "id": "DEV-02.1",
      "title": "Refactor configuration into `config.py`",
      "value_to_user_base": 75,
      "value_rationale": "Centralizing configuration logic, including profiles and hardware-aware defaults, makes the system easier to reason about and adjust.",
      "difficulty_to_vibe_code": 45,
      "difficulty_rationale": "Requires moving env loading, derived settings, and profile handling out of the main app and ensuring all call sites use the new interface.",
      "time_to_vibe_code_and_test": 40,
      "time_rationale": "Refactoring and then testing configuration-dependent features across profiles will take several evenings.",
      "depends_on": ["CFG-01"]
    },
    {
      "id": "DEV-02.2",
      "title": "Refactor LLM client into `llm_client.py`",
      "value_to_user_base": 80,
      "value_rationale": "Encapsulating LLM interactions enables easier evolution of chat, embeddings, and model management without touching UI code.",
      "difficulty_to_vibe_code": 50,
      "difficulty_rationale": "Involves designing a clean client API, moving all LLM calls, and ensuring streaming or error handling behavior remains correct.",
      "time_to_vibe_code_and_test": 45,
      "time_rationale": "Refactor and regression testing of chat and embedding flows will likely consume multiple evenings.",
      "depends_on": []
    },
    {
      "id": "DEV-02.3",
      "title": "Refactor RAG pipeline into `docs_rag.py`",
      "value_to_user_base": 80,
      "value_rationale": "Isolating the RAG pipeline into its own module makes it easier to extend for OCR, web augmentation, and new retrieval strategies.",
      "difficulty_to_vibe_code": 60,
      "difficulty_rationale": "Requires moving extraction, chunking, embedding, retrieval, and web augmentation into a coherent module without breaking existing behavior.",
      "time_to_vibe_code_and_test": 55,
      "time_rationale": "The refactor, combined with testing across various document workflows, will span several evenings or a couple of weekends.",
      "depends_on": ["RAG-01.1", "RAG-01.2", "RAG-01.3", "RAG-01.4", "RAG-01.5"]
    },
    {
      "id": "DEV-02.4",
      "title": "Refactor safety pipeline into `safety.py`",
      "value_to_user_base": 80,
      "value_rationale": "Centralizing SafetyService and all detectors simplifies reasoning about safety behavior and supports future policy changes.",
      "difficulty_to_vibe_code": 60,
      "difficulty_rationale": "Moving multiple detectors and policies into one module, with a small public interface for the UI, is a nontrivial but well-bounded refactor.",
      "time_to_vibe_code_and_test": 55,
      "time_rationale": "Refactoring plus regression testing of safety behavior on input, output, and web snippets will take several evenings or weekends.",
      "depends_on": ["SAFETY-01", "SAFETY-02", "SAFETY-03", "SAFETY-04"]
    },
    {
      "id": "DEV-03",
      "title": "`pip-audit` integration",
      "value_to_user_base": 70,
      "value_rationale": "Regularly detecting vulnerable Python dependencies improves long-term security posture for self-hosted deployments.",
      "difficulty_to_vibe_code": 25,
      "difficulty_rationale": "Adding a simple script or Make/Invoke task and optionally wiring a CI job is low-complexity tooling work.",
      "time_to_vibe_code_and_test": 20,
      "time_rationale": "Implementation and a couple of trial runs to confirm reports work should fit into one or two short sessions.",
      "depends_on": []
    }
  ]
}
```

