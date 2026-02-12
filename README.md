# EphemerAl: A Simple Self-Hosted Chat Interface for Local AI with Ollama that Accepts Documents and Images

EphemerAl is a lightweight, open-source web interface for interacting with local LLMs on native Windows infrastructure. I designed it for my day job to help keep our team's sensitive info off cloud services, and to provide a modern AI experience to staff without the per-user cost required to achieve equivalent capabilities online. Responses can be enhanced with documents, images, and user prompts during each conversation.

While it wasn't built for broad distribution, I'm sharing this generalized version in case it helps others looking for a local-only, account-free, multimodal LLM interface.

[View the full source code on GitHub](https://github.com/eowensai/EphemerAl)

![A screenshot of EphemerAl, a self-hosted AI assistant for local LLM document Q&A and image analysis using Ollama](Ephemeral%20Screenshot.jpg)

---

## Core Features

- **Local AI Interaction:** Real-time conversations powered by your Ollama-hosted model.
- **Document and Image Uploads:** Submit one or more files (including PDFs, documents, and spreadsheets; 100+ formats via Apache Tika).
- **Multimodal Functionality:** Use vision-capable models to combine text and image inputs.
- **Customizable Interface:** Add your own branding and adjust visuals with Streamlit.
- **Ephemeral Sessions:** Chat content is cleared when you refresh, start a new conversation, or close your browser.

## Privacy Notes

EphemerAl is designed to minimize data retention:

- **No database:** Conversations live in Streamlit process memory (`st.session_state`) for your browser session and are not persisted to disk by this app.
- **Session-scoped caching:** Document parsing results are cached per-session for performance, but cleared when you start a new conversation or close your browser.
- **Service log files:** Windows services write operational logs to `C:\EphemerAl\logs\` for startup diagnostics and error messages. These logs are not designed to capture conversation content, but administrators can review and clear them periodically for data hygiene.

Note that browser caching behavior depends on your browser settings and cache-control headers. For maximum privacy on shared machines, use private/incognito browsing or clear browser data after use.

## Technical Stack

EphemerAl uses a native Windows service architecture:

- **Frontend:** Streamlit app (`ephemeral_app.py`) running on Python.
- **LLM backend:** Ollama running natively on Windows.
- **Document parser:** Apache Tika Server running from a Java JAR.
- **Service management:** NSSM (Non-Sucking Service Manager) for startup and recovery behavior across reboots.

## System Requirements

Recommended baseline:

- **Operating System:** Windows 11 Pro or Enterprise, fully updated.
- **Graphics Processing Unit:** NVIDIA GPU (or equivalent capable hardware) sized for your chosen model.
- **Runtime dependencies:** Python 3.11+, Java 21+, Ollama, and NSSM installed on Windows.

## Getting Started

For complete setup and operations steps, follow the [System Deployment Guide](System%20Deployment%20Guide.md).

## Accessing the EphemerAl website

- **Local Access:** http://localhost:8501
- **Network Access:** http://windows_host_ip_address:8501

## Support

This project is provided as a resource for the community as-is. I hope it solves a problem or provides value outside my environment.

If you run into issues, consider submitting error details, including screenshots and system files, to an AI assistant for guidance. This isn't meant to be snark, it's amazing how well the big reasoning models can troubleshoot.

**License:**

MIT - (At least the parts of this stack that are mine to license)
