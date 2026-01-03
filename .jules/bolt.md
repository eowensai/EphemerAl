## 2025-01-03 - Cache Expensive UI Components in Streamlit
**Learning:** Streamlit re-executes the entire script on every interaction. Expensive string manipulations (like generating export formats for a chat history) inside the loop—especially those in the sidebar—will run on every single user interaction, causing latency.
**Action:** Use `st.session_state` to implement manual caching for expensive UI generation steps that don't need to change on every frame, using simple keys like `len(messages)` for invalidation.
