## 2024-05-23 - DoS Prevention via File Size Limits
**Vulnerability:** The application previously warned about large files (>50MB) but proceeded to read them entirely into memory (`f.getvalue()`). This created a Denial of Service (DoS) vulnerability where an attacker could exhaust the server's memory by uploading multiple large files (up to the default Streamlit limit of 200MB).
**Learning:** Always validate input size *before* processing or loading it into memory. Warnings are insufficient for resource protection; hard limits are required. Streamlit's `UploadedFile` object is already on the server, but `f.getvalue()` creates a new byte copy in Python memory, doubling the impact.
**Prevention:**
1. Define a strict `MAX_UPLOAD_SIZE_MB`.
2. Check `f.size` before calling `f.getvalue()` or any processing function.
3. Skip processing and return an error if the limit is exceeded.
