## 2024-05-23 - Streamlit Caching Strategies
**Learning:** Streamlit reruns the entire script on every interaction. Expensive computations (like generating large strings for UI components) must be cached manually if they are not suitable for @st.cache_data (e.g. because they depend on mutable session state like chat history).
**Action:** Use a lightweight signature (e.g. length of list + last item ID) to detect state changes and memoize results in st.session_state.
