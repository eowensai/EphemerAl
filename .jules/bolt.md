# Performance Learnings: Hybrid WSL/Windows Architecture

## Moving Ollama to Windows Native
Migrating the `ollama` backend from a Docker container inside WSL2 to a native Windows installation significantly improves performance for prompt processing.
*   **Problem:** Ollama running in Docker inside WSL2 often defaulted to CPU inference or suffered from overhead, leading to multi-minute delays.
*   **Solution:** Native Windows execution allows direct access to the GPU driver stack without virtualization overhead.
*   **Networking:** This architecture requires the Windows Ollama instance to listen on `0.0.0.0` (`setx OLLAMA_HOST "0.0.0.0" /m`) and the WSL application to connect via the nameserver IP in `/etc/resolv.conf`.
*   **Docker Config:** To reliably resolve the Windows host IP, the Streamlit application container uses `network_mode: "host"`.
