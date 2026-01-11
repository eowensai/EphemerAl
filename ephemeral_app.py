diff --git a/ephemeral_app.py b/ephemeral_app.py
index 12c51735996a23ca56b57bbcd50da1cf577b46af..c7b0b33d286fd1c32f6172bc83fd7e7b8e07a262 100644
--- a/ephemeral_app.py
+++ b/ephemeral_app.py
@@ -1,33 +1,34 @@
 import os
 import base64
 import hashlib
 import pathlib
 import re
 import string
 import time
 import uuid
+import logging
 from datetime import datetime, tzinfo
 from html import escape as html_escape
 from typing import Union, Tuple, List
 
 import streamlit as st
 import streamlit.components.v1 as components
 import requests
 import pytz
 from tika import parser
 from openai import OpenAI
 
 # EphemerAl main Streamlit application.
 # - Provides an ephemeral chat UI for working with uploaded documents and images.
 # - Talks to an LLM backend and an Apache Tika server over HTTP endpoints configured via environment variables.
 # - Uses Streamlit's in-memory session_state only; this script does not write chat content or uploads to disk.
 #
 # Privacy notes:
 # - Document parsing is cached per-session only (not shared across users/sessions).
 # - "New Conversation" clears all session state including parse cache.
 # - Browser caching depends on cache-control headers and browser behavior.
 # - Docker container logs may capture tracebacks; set logging driver to "none" for hardened deployments.
 
 APP_VERSION = "1.8.0"
 
 # ── Constants ────────────────────────────────────────────────────────
@@ -61,61 +62,76 @@ st.markdown(
 
 def load_css(path: str = "theme.css") -> None:
     """Load optional CSS overrides to customize Streamlit's default look."""
     css_path = pathlib.Path(path)
     if css_path.exists():
         st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
 
 
 load_css()
 
 # ── Optional device detection ─────────────────────────────────────
 # Device detection is optional; the app still works without it.
 try:
     from streamlit_browser_engine import device
     HAS_DEVICE_DETECTION = True
 except ImportError:
     HAS_DEVICE_DETECTION = False
     device = None
 
 # ── Backend configuration ─────────────────────────────────────────
 # Endpoints and model name are configurable so the app can talk to different
 # backends (e.g. local Docker containers or remote services).
 LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
 MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemma3-prod")
 TIKA_URL = os.getenv("TIKA_URL", "http://tika-server:9998")
+TIKA_TIMEOUT_S = int(os.getenv("TIKA_TIMEOUT_S", "15"))
+DOC_CONTEXT_MAX_CHARS = int(
+    os.getenv("DOC_CONTEXT_MAX_CHARS", os.getenv("MAX_CONTEXT_CHARS", "12000"))
+)
+DOC_CONTEXT_MAX_CHARS_PER_DOC = int(
+    os.getenv("DOC_CONTEXT_MAX_CHARS_PER_DOC", os.getenv("MAX_DOC_CHARS", "4000"))
+)
+DEFAULT_UPLOAD_PROMPT = os.getenv("DEFAULT_UPLOAD_PROMPT", "Please analyze the uploaded files.")
+LLM_SUPPORTS_VISION = os.getenv("LLM_SUPPORTS_VISION")
 
 
 # ── Health checks (cached to reduce UI jank) ──────────────────────
 @st.cache_data(ttl=5, show_spinner=False)
 def tika_alive() -> bool:
     """
     Lightweight health check for the Tika server at TIKA_URL.
     Cached for 5 seconds to avoid repeated network calls on reruns.
     """
     try:
-        return requests.get(TIKA_URL, timeout=2).ok
+        base = TIKA_URL.rstrip("/")
+        endpoints = (f"{base}/tika", f"{base}/version", base)
+        for url in endpoints:
+            r = requests.get(url, timeout=2)
+            if r.ok:
+                return True
+        return False
     except Exception:
         return False
 
 
 @st.cache_data(ttl=5, show_spinner=False)
 def llm_alive() -> bool:
     """
     Lightweight health check for the LLM backend.
     
     Tries OpenAI-compatible /models endpoint first, then falls back to
     Ollama-specific /api/tags. Cached for 5 seconds to reduce UI jank.
     
     Treats 401/403 as "alive" since auth errors prove the service is reachable.
     """
     try:
         # Normalize base URL - handle both "http://host:port/v1" and "http://host:port"
         base_url = LLM_BASE_URL.rstrip("/")
         
         # Try OpenAI-compatible endpoint
         if base_url.endswith("/v1"):
             models_url = base_url + "/models"
         else:
             models_url = base_url + "/v1/models"
         
         r = requests.get(models_url, timeout=2)
@@ -208,73 +224,126 @@ def parse_with_tika(data: bytes, filename: str) -> str:
     This avoids repeatedly parsing the same file within a session while
     ensuring parsed content doesn't persist across sessions or users.
     
     Args:
         data: Raw file bytes
         filename: Original filename (for logging/errors only, not part of cache key)
     
     Returns:
         Extracted text content, or empty string if parsing fails
     """
     key = hashlib.sha256(data).hexdigest()
     cache = _get_tika_cache()
     now = time.time()
     
     # Lazy TTL pruning - remove expired entries
     expired = [k for k, (ts, _) in cache.items() if now - ts > TIKA_CACHE_TTL_S]
     for k in expired:
         del cache[k]
     
     # Return cached result if available
     if key in cache:
         return cache[key][1]
     
     # Parse and cache (don't cache failures or empty results)
     with st.spinner("Parsing document…"):
-        parsed = parser.from_buffer(data, serverEndpoint=TIKA_URL)
+        parsed = parser.from_buffer(
+            data,
+            serverEndpoint=TIKA_URL,
+            requestOptions={"timeout": TIKA_TIMEOUT_S},
+        )
     text = (parsed.get("content") or "").strip()
     
     # Only cache non-empty results - empty might be a transient Tika issue
     if text:
         cache[key] = (now, text)
     
     return text
 
 
+def truncate_text(text: str, limit: int) -> Tuple[str, bool]:
+    """
+    Truncate text to a character limit, returning (text, did_truncate).
+    """
+    if limit <= 0:
+        return "", True
+    if len(text) <= limit:
+        return text, False
+    return text[:limit].rstrip() + "\n...[truncated]", True
+
+
 # ── Cached OpenAI client ──────────────────────────────────────────
 @st.cache_resource
 def get_llm_client() -> OpenAI:
     """
     Return a cached OpenAI client instance.
 
     The client is configured to talk to LLM_BASE_URL (typically an Ollama-compatible
     endpoint). The api_key value is a placeholder because most local backends
     ignore it, but the OpenAI client requires something to be set.
     """
     return OpenAI(base_url=LLM_BASE_URL, api_key="not-needed")
 
 
+@st.cache_data(ttl=60, show_spinner=False)
+def model_supports_images() -> bool:
+    """
+    Return True if the configured model is expected to support vision inputs.
+
+    Uses (in order):
+      1) LLM_SUPPORTS_VISION env var (true/false).
+      2) Ollama /api/show response (if available) for vision-related keys.
+      3) Model name heuristics for common vision-capable families.
+    """
+    if LLM_SUPPORTS_VISION is not None:
+        return LLM_SUPPORTS_VISION.strip().lower() in {"1", "true", "yes", "y"}
+
+    model_lower = (MODEL_NAME or "").lower()
+    vision_name_match = re.search(
+        r"(vision|llava|moondream|phi3-vision|qwen2-vl|gpt-4o|gpt-4v|gpt-4\.1|gemini-\d|claude-3-(opus|sonnet|haiku))",
+        model_lower,
+    )
+    if vision_name_match:
+        return True
+
+    try:
+        base_url = LLM_BASE_URL.rstrip("/").split("/v1")[0]
+        show_url = f"{base_url}/api/show"
+        resp = requests.post(show_url, json={"name": MODEL_NAME}, timeout=2)
+        if resp.ok:
+            payload = resp.json()
+            model_info = payload.get("model_info") or {}
+            for key in model_info.keys():
+                key_lower = key.lower()
+                if "vision" in key_lower or "clip" in key_lower or "projector" in key_lower:
+                    return True
+    except Exception as e:
+        logging.debug("Ollama /api/show probe failed: %s", e)
+
+    return False
+
+
 # ── Chat message wrapper for CSS styling ──────────────────────────
 # Streamlit doesn't expose the message role in CSS-selectable attributes.
 # By wrapping each chat_message in a container with a key containing the role,
 # we get a class like "st-key-user-xxx" that CSS can target.
 #
 # CSS CONTRACT: Keys are formatted as "{role}-{message_id}".
 # theme.css uses selectors like [class*="st-key-user-"] to match.
 # This pattern depends on Streamlit's internal DOM structure and should be
 # validated when upgrading Streamlit versions.
 def styled_chat_message(role: str, message_id: str = None):
     """
     Return a chat_message wrapped in a keyed container for CSS styling.
 
     Usage:
         with styled_chat_message("user", msg.get("id")):
             st.markdown("Hello!")
 
     This enables CSS selectors like [class*="st-key-user-"] to style messages
     differently based on role.
 
     Args:
         role: "user" or "assistant"
         message_id: Stable ID for this message. If None, generates a new UUID.
                     Using stable IDs reduces DOM churn across Streamlit reruns.
     """
@@ -325,50 +394,55 @@ def _extract_export_info(content: Union[str, list]) -> Tuple[List[str], List[str
                     char_count = len((extracted or "").strip())
                     if fname and fname not in doc_seen:
                         doc_seen.add(fname)
                         doc_lines.append(f"- 📄 {fname} ({char_count:,} characters extracted)")
 
             elif text.startswith("📄 *") and text.endswith("*"):
                 fname = text[len("📄 *"):-1].strip()
                 if fname and fname not in doc_seen:
                     doc_seen.add(fname)
                     doc_lines.append(f"- 📄 {fname}")
 
             elif text.startswith("📷 *") and text.endswith("*"):
                 fname = text[len("📷 *"):-1].strip()
                 if fname:
                     img_marker_names.append(fname)
 
             else:
                 if text and text.strip():
                     text_chunks.append(text.strip())
 
         elif ptype == "image":
             fname = (part.get("filename") or "image").strip()
             if fname and fname not in img_seen:
                 img_seen.add(fname)
                 img_lines.append(f"- 📷 {fname}")
+        elif ptype == "image_url":
+            fname = (part.get("filename") or "image").strip()
+            if fname and fname not in img_seen:
+                img_seen.add(fname)
+                img_lines.append(f"- 📷 {fname}")
 
     for fname in img_marker_names:
         if fname not in img_seen:
             img_seen.add(fname)
             img_lines.append(f"- 📷 {fname}")
 
     message_text = "\n\n".join(text_chunks).strip()
     return doc_lines, img_lines, message_text
 
 
 def build_conversation_markdown(messages: List[dict]) -> str:
     """
     Build a Markdown transcript used as plain-text clipboard fallback.
     """
     lines: List[str] = ["# EphemerAl Conversation", ""]
 
     for msg in messages:
         role = msg.get("role", "assistant")
         role_title = "User" if role == "user" else "Assistant"
         lines.append(f"**{role_title}**")
 
         doc_lines, img_lines, message_text = _extract_export_info(msg.get("content", ""))
 
         if doc_lines or img_lines:
             lines.append("")
@@ -535,51 +609,51 @@ def build_conversation_html(messages: List[dict]) -> str:
     chunks.append("</div>")
     return "\n".join(chunks).strip()
 
 
 def render_copy_button(export_text_plain: str, export_html: str) -> None:
     """
     Sidebar-only copy button.
 
     UI goals:
     - Match Streamlit sidebar button width (remove iframe default margins).
     - No persistent status text under the button.
     - Give subtle success feedback via a short button flash.
 
     Clipboard behavior:
     - Attempts to copy formatted HTML first (richer paste).
     - Falls back to plain text if rich copy is blocked.
     - Uses selection + document.execCommand('copy'), which tends to work more reliably on HTTP.
     
     Note: Colors are hardcoded because this runs in an iframe that can't access
     CSS variables. These must match --color-accent (#E1654A) in theme.css.
     """
     safe_plain = html_escape(export_text_plain)
 
     hover_tip = (
         "Copy this conversation to your clipboard. "
-        "Chat content is cleared when you refresh or start a new conversation."
+        "Chat content is cleared when you start a new conversation or close your browser."
     )
 
     # NOTE: Colors here must be hardcoded because this runs in an iframe.
     # Update these if you change --color-accent in theme.css.
     # Current accent: #E1654A (coral), darker: #C4503A
     components.html(
         f"""
         <style>
           html, body {{
             margin: 0;
             padding: 0;
           }}
 
           /* Match theme.css button look as closely as possible inside an iframe */
           #copy-btn {{
             width: 100%;
             box-sizing: border-box;
             background: white;
             color: #1E242B;
             border: 2px solid #E1654A;
             font-weight: 600;
             font-size: .95rem;
             font-family:
                 ui-sans-serif,
                 system-ui,
@@ -762,204 +836,242 @@ if st.session_state.show_welcome:
         st.markdown(
             f"""
             <div class='welcome-text'>
                 <span style='font-size:1.6em;font-weight:600;'>Welcome&nbsp;to</span><br>
                 <img src='data:{mime_type};base64,{wordmark_b64}'
                      class='welcome-wordmark' alt='EphemerAl'>
             </div>
             """,
             unsafe_allow_html=True,
         )
     else:
         # Text-based wordmark (fallback)
         st.markdown(
             "<div class='welcome-text'>"
             "<span style='font-size:1.6em;font-weight:600;'>Welcome&nbsp;to</span> "
             "<span class='ephemer'>Ephemer</span><span class='al'>Al</span>"
             "</div>",
             unsafe_allow_html=True,
         )
 
     st.markdown(
         """
         <div class="right-align-block">
           I understand image files and most (100+!) document types.
           <div class="welcome-dots">•&nbsp;&nbsp;•&nbsp;&nbsp;•</div>
-          Conversations are cleared when you refresh, start a new conversation, or close your browser.
+          Conversations are cleared when you start a new conversation or close your browser.
           <div class="welcome-dots">•&nbsp;&nbsp;•&nbsp;&nbsp;•</div>
           I try to be helpful, but sometimes I'm wrong. Please double-check important answers!
         </div>
         """,
         unsafe_allow_html=True,
     )
 
 # ── Helper: render chat content ───────────────────────────────────
 def render_content(content: Union[str, list]) -> None:
     """
     Render either plain markdown or structured content (text + images)
     for a single chat message.
     
     Synthetic context blocks (marked with _synthetic flag) are hidden from
     display but still sent to the model.
     """
     if isinstance(content, list):
         for part in content:
             if part.get("type") == "text":
                 # Hide synthetic context blocks (flagged, not string-matched)
                 if not part.get("_synthetic"):
                     st.markdown(part["text"])
             elif part.get("type") == "image":
+                # Legacy path: raw image bytes were stored before image_url migration.
                 try:
                     st.image(part["data"], width=180)
                 except Exception:
                     st.error(f"Failed to display {part.get('filename', 'image')}")
             elif part.get("type") == "image_url":
                 try:
                     st.image(part["image_url"]["url"], width=180)
                 except Exception:
                     st.error("Failed to display image from assistant")
     else:
         st.markdown(content)
 
 # ── Render chat history ───────────────────────────────────────────
 for m in st.session_state.messages:
     with styled_chat_message(m["role"], m.get("id")):
         render_content(m["content"])
 
 # ── Mobile button ────────────────────────────────────────────────
 if HAS_DEVICE_DETECTION and device and device.is_mobile:
     # On mobile we mirror the "New Conversation" control in the main layout
     # for easier reach.
     if st.button("🔄 New Conversation", key="mobile_new", use_container_width=True):
         st.session_state.clear()
         st.rerun()
 
 # ── Chat input ───────────────────────────────────────────────────
 # When accept_file="multiple" is enabled, st.chat_input returns an object with
 # .text and .files; for plain text it returns just a string. We normalize below.
 prompt_in = st.chat_input("Ask me anything…", accept_file="multiple", key="main_chat")
 prompt_in = st.session_state.pop("_first_prompt_pending", None) or prompt_in
 
 if prompt_in is not None:
     # The first prompt dismisses the welcome banner, then we rerun so the UI
     # re-renders without the intro text.
     if st.session_state.show_welcome:
         st.session_state.show_welcome = False
         st.session_state["_first_prompt_pending"] = prompt_in
         st.rerun()
 
     user_text = prompt_in.text if hasattr(prompt_in, "text") else prompt_in
+    user_text = (user_text or "").strip()
     files = prompt_in.files if hasattr(prompt_in, "files") else []
+    if not user_text and files:
+        user_text = DEFAULT_UPLOAD_PROMPT
 
     # Generate stable ID for user message
     user_msg_id = str(uuid.uuid4())
 
     with styled_chat_message("user", user_msg_id):
         st.markdown(user_text)
 
     parts, doc_ctx = [], []
+    doc_ctx_chars = 0
+    context_truncated = False
+    truncated_docs: List[str] = []
     for f in files:
         if f.type.startswith("image/"):
             # Large images will still be accepted, but we warn that processing
             # may be slow rather than silently failing.
             if f.size > 50 * 1024 * 1024:
                 st.warning(f"📷 {f.name} is {f.size/1e6:.1f} MB – may be slow to process")
 
             f.seek(0)
             img_bytes = f.getvalue()
+            img_b64 = base64.b64encode(img_bytes).decode()
             parts.append({"type": "text", "text": f"📷 *{f.name}*"})
             parts.append(
                 {
-                    "type": "image",
-                    "data": img_bytes,
+                    "type": "image_url",
+                    "image_url": {"url": f"data:{f.type};base64,{img_b64}"},
                     "mime_type": f.type,
                     "filename": f.name,
                 }
             )
         else:
             parts.append({"type": "text", "text": f"📄 *{f.name}*"})
             if not tika_alive():
                 st.warning(f"📄 Parsing unavailable for {f.name}")
                 continue
             try:
                 f.seek(0)
                 data = f.getvalue()
                 txt = parse_with_tika(data, f.name)
                 if txt:
-                    doc_ctx.append(f"--- {f.name} ---\n{txt}")
+                    truncated_text, did_truncate = truncate_text(txt, DOC_CONTEXT_MAX_CHARS_PER_DOC)
+                    if did_truncate:
+                        truncated_docs.append(f.name)
+                    block = f"--- {f.name} ---\n{truncated_text}"
+                    separator_len = 2 if doc_ctx else 0
+                    remaining = DOC_CONTEXT_MAX_CHARS - doc_ctx_chars - separator_len
+                    if remaining <= 0:
+                        if not context_truncated:
+                            st.warning("📄 Document context truncated to fit model limits.")
+                            context_truncated = True
+                        continue
+                    if len(block) > remaining:
+                        truncated_block, _ = truncate_text(block, remaining)
+                        doc_ctx.append(truncated_block)
+                        doc_ctx_chars += separator_len + len(truncated_block)
+                        if not context_truncated:
+                            st.warning("📄 Document context truncated to fit model limits.")
+                            context_truncated = True
+                    else:
+                        doc_ctx.append(block)
+                        doc_ctx_chars += separator_len + len(block)
             except Exception as e:
                 st.error(f"❌ {f.name}: {e}")
 
+    if truncated_docs:
+        unique_docs = ", ".join(sorted(set(truncated_docs)))
+        st.warning(
+            "📄 Truncated document text to "
+            f"{DOC_CONTEXT_MAX_CHARS_PER_DOC:,} characters per file: {unique_docs}."
+        )
+
     # If we successfully parsed any documents, prepend them to the content that
     # will be sent to the model as a synthetic context block (flagged, not string-matched).
     if doc_ctx:
         parts.insert(0, {
             "type": "text",
             "text": CONTEXT_PREFIX + "\n\n".join(doc_ctx),
             "_synthetic": True  # Flag to identify synthetic blocks
         })
-    parts.append({"type": "text", "text": user_text})
+    if user_text:
+        parts.append({"type": "text", "text": user_text})
 
     content_for_llm = parts if len(parts) > 1 else user_text
     st.session_state.messages.append({
         "id": user_msg_id,
         "role": "user",
         "content": content_for_llm
     })
 
     # ── LLM payload ───────────────────────────────────────────────
     # Render the system prompt (either from the template file or the fallback),
     # injecting a human-readable local timestamp.
     sys_prompt = SYSTEM_TMPL.safe_substitute(current_time_local=timestamp_local())
 
     messages_for_api = []
+    vision_supported = model_supports_images()
+    skipped_images = False
     for msg in st.session_state.messages:
         if isinstance(msg["content"], list):
             api_parts = []
             for part in msg["content"]:
                 if part.get("type") == "text":
                     api_parts.append({"type": "text", "text": part["text"]})
-                elif part.get("type") == "image":
-                    # Convert raw image bytes to data: URLs that OpenAI-compatible
-                    # image endpoints expect. Cache base64 on the part so repeated
-                    # sends in the same session do not re-encode.
-                    if "b64" not in part:
-                        part["b64"] = base64.b64encode(part["data"]).decode()
-                    api_parts.append(
-                        {
-                            "type": "image_url",
-                            "image_url": {
-                                "url": f"data:{part.get('mime_type', 'image/jpeg')};base64,{part['b64']}"
-                            },
-                        }
-                    )
                 elif part.get("type") == "image_url":
-                    api_parts.append(part)
+                    if vision_supported:
+                        api_parts.append(
+                            {
+                                "type": "image_url",
+                                "image_url": part["image_url"],
+                            }
+                        )
+                    else:
+                        skipped_images = True
+                        continue
             messages_for_api.append({"role": msg["role"], "content": api_parts})
         else:
             messages_for_api.append({"role": msg["role"], "content": msg["content"]})
 
+    if skipped_images:
+        st.warning(
+            "📷 Images were not sent to the model because the selected model does not appear to support vision."
+        )
+
     # Prepend the system message so the backend sees the time-aware instructions.
     payload = [{"role": "system", "content": sys_prompt}, *messages_for_api]
 
     # Generate stable ID for assistant message
     assistant_msg_id = str(uuid.uuid4())
 
     # ── Call LLM ───────────────────────────────────────────────────
     with styled_chat_message("assistant", assistant_msg_id):
         with st.spinner("Thinking…"):
             try:
                 client = get_llm_client()
                 stream = client.chat.completions.create(
                     model=MODEL_NAME,
                     messages=payload,
                     stream=True,
                 )
                 acc, box = "", st.empty()
                 for chunk in stream:
                     acc += chunk.choices[0].delta.content or ""
                     box.markdown(acc + "▌")
                 box.markdown(acc)
                 st.session_state.messages.append({
                     "id": assistant_msg_id,
                     "role": "assistant",
                     "content": acc
