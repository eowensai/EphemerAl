## 2026-01-06 - Secure Error Handling in Streamlit
**Vulnerability:** Raw exception messages were directly displayed to users via `st.error(f"{e}")`. This could leak internal paths, IP addresses, or stack traces (e.g., `requests.exceptions.ConnectionError` revealing backend URLs).
**Learning:** Streamlit apps often default to showing raw errors for developer convenience, but this is a security risk in production. `st.error` does not automatically sanitize input.
**Prevention:** Use Python's `logging` module to capture full tracebacks (`exc_info=True`) server-side, and display only generic "An error occurred" messages to the user.
