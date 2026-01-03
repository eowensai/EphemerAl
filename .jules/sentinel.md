## 2024-05-23 - [DoS Prevention]
**Vulnerability:** Unrestricted file uploads could lead to memory exhaustion (DoS).
**Learning:** Streamlit's `accept_file="multiple"` combined with `f.getvalue()` reads entire files into memory. Without application-level limits, a user can upload massive files (within server limits) that crash the app logic or backend services like Tika.
**Prevention:** Check `f.size` before reading content. Implement strict application-level limits (e.g., 200MB) for all file types, not just images.
