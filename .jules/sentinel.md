## 2024-05-23 - Denial of Service via Large File Upload
**Vulnerability:** The application was vulnerable to Denial of Service (DoS) via memory exhaustion because it read the entire content of uploaded files into memory (`f.getvalue()`) before checking their size, despite a warning for large images.
**Learning:** Checking file size *after* reading content defeats the purpose of the check for DoS protection. `streamlit.uploaded_file_manager.UploadedFile` exposes `.size` which should be checked *before* any read operations.
**Prevention:** Always validate input size limits before allocating memory or processing data. Used `MAX_UPLOAD_SIZE_MB = 50` to strictly enforce the limit.
