import os
import base64
import hashlib
import pathlib
import re
import string
import time
import uuid
import logging
from datetime import datetime, tzinfo
from html import escape as html_escape
from typing import Union, Tuple, List, Dict, Optional

import streamlit as st
import streamlit.components.v1 as components
import requests
import pytz
from tika import parser
from openai import OpenAI

# EphemerAl main Streamlit application.
# - Provides an ephemeral chat UI for working with uploaded documents and images.
# - Talks to an LLM backend and an Apache Tika server over HTTP endpoints configured via environment variables.
# - Uses Streamlit's in-memory session_state only, this script does not write chat content or uploads to disk.

APP_VERSION = "1.8.1"

# Prefix used for synthetic context blocks injected into user messages.
# We use a flag (_synthetic) to identify these, not string matching.
CONTEXT_PREFIX = "Context:\n"

# TTL for session-scoped Tika parse cache (seconds)
TIKA_CACHE_TTL_S = 3600

# Default approximation for a single image input (overridden if model metadata provides a value)
IMG_TOKEN_COST_DEFAULT = 2048

# Token estimation behavior
TOKEN_HEURISTIC_CHARS_PER_TOKEN = 3.5
TOKEN_CACHE_MAX_ENTRIES = 256
TOKENIZE_TIMEOUT_S = 2.0  # keep UI snappy; budgeting degrades silently if tokenize is slow/unavailable

# Debug mode (shows technical status in sidebar, and error detail expanders)
DEBUG_MODE = os.getenv("EPHEMERAL_DEBUG", "0").strip().lower() in {"1", "true", "yes", "y", "on"}

# Feature toggle (operator-only)
ENABLE_TOKEN_BUDGETING = os.getenv("ENABLE_TOKEN_BUDGETING", "1").strip().lower() not in {"0", "false", "no"}

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="EphemerAl",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── Anti-caching meta tags ────────────────────────────────────────
st.markdown(
    """
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    """,
    unsafe_allow_html=True,
)


def load_css(path: str = "theme.css") -> None:
    """Load optional CSS overrides to customize Streamlit's default look."""
    css_path = pathlib.Path(path)
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


load_css()

# ── Optional device detection ─────────────────────────────────────
try:
    from streamlit_browser_engine import device  # type: ignore

    HAS_DEVICE_DETECTION = True
except ImportError:
    HAS_DEVICE_DETECTION = False
    device = None  # type: ignore

# ── Backend configuration ─────────────────────────────────────────
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemma3-prod")
TIKA_URL = os.getenv("TIKA_URL", "http://tika-server:9998")
TIKA_TIMEOUT_S = int(os.getenv("TIKA_TIMEOUT_S", "15"))
DEFAULT_UPLOAD_PROMPT = os.getenv("DEFAULT_UPLOAD_PROMPT", "Please analyze the uploaded files.")
LLM_SUPPORTS_VISION = os.getenv("LLM_SUPPORTS_VISION")


def _ollama_base_url() -> str:
    """
    Convert an OpenAI-style base URL like http://host:11434/v1 into the native Ollama base http://host:11434.
    If /v1 isn't present, returns the URL without trailing slash.
    """
    return LLM_BASE_URL.rstrip("/").split("/v1")[0]


# ── Health checks (cached to reduce UI jank) ──────────────────────
@st.cache_data(ttl=5, show_spinner=False)
def tika_alive() -> bool:
    """Lightweight health check for the Tika server."""
    try:
        base = TIKA_URL.rstrip("/")
        endpoints = (f"{base}/tika", f"{base}/version", base)
        for url in endpoints:
            r = requests.get(url, timeout=2)
            if r.ok:
                return True
        return False
    except Exception:
        return False


@st.cache_data(ttl=5, show_spinner=False)
def llm_alive() -> bool:
    """
    Lightweight health check for the LLM backend.
    Tries OpenAI-compatible /models endpoint first, then falls back to Ollama /api/tags.
    Treats 401/403 as "alive" since auth errors prove the service is reachable.
    """
    try:
        base_url = LLM_BASE_URL.rstrip("/")

        if base_url.endswith("/v1"):
            models_url = base_url + "/models"
        else:
            models_url = base_url + "/v1/models"

        r = requests.get(models_url, timeout=2)
        if r.status_code in (200, 401, 403):
            return True

        r2 = requests.get(_ollama_base_url() + "/api/tags", timeout=2)
        return r2.ok
    except Exception:
        return False


def get_local_timezone() -> tzinfo:
    """
    Resolve the timezone used for UI timestamps and the system prompt.
    Priority:
      1. EPHEMERAL_TIMEZONE env var if valid.
      2. The system's local timezone.
    """
    env_tz = os.getenv("EPHEMERAL_TIMEZONE")
    if env_tz:
        try:
            return pytz.timezone(env_tz)
        except Exception:
            if DEBUG_MODE:
                try:
                    st.warning(
                        f"EPHEMERAL_TIMEZONE={env_tz!r} is not a valid timezone, falling back to system time."
                    )
                except Exception:
                    pass

    sys_tz = datetime.now().astimezone().tzinfo
    return sys_tz or pytz.UTC


TIMEZONE = get_local_timezone()


def timestamp_local() -> str:
    """Return a human-readable local timestamp string."""
    now = datetime.now(TIMEZONE)
    fmt = "%-I:%M %p on %A, %B %-d, %Y"
    if os.name == "nt":
        fmt = fmt.replace("%-I", "%#I").replace("%-d", "%#d")
    return now.strftime(fmt)


tmpl_path = pathlib.Path(__file__).parent / "system_prompt_template.md"
if tmpl_path.exists():
    SYSTEM_TMPL = string.Template(tmpl_path.read_text(encoding="utf-8"))
else:
    SYSTEM_TMPL = string.Template(
        "You are a helpful AI assistant. The current local time is ${current_time_local}. "
        "Answer concisely and accurately based on the context provided."
    )


# ── Session-scoped Tika parsing cache ─────────────────────────────
def _get_tika_cache() -> dict:
    """Return the session-scoped Tika parse cache, creating if needed."""
    return st.session_state.setdefault("_tika_cache", {})


def parse_with_tika(data: bytes, filename: str) -> str:
    """
    Parse document bytes with Tika via TIKA_URL.
    Cached per-session by content hash (SHA-256) with TTL.
    """
    key = hashlib.sha256(data).hexdigest()
    cache = _get_tika_cache()
    now = time.time()

    expired = [k for k, (ts, _) in cache.items() if now - ts > TIKA_CACHE_TTL_S]
    for k in expired:
        del cache[k]

    if key in cache:
        return cache[key][1]

    with st.spinner(f"Reading {filename}…"):
        try:
            parsed = parser.from_buffer(
                data,
                serverEndpoint=TIKA_URL,
                requestOptions={"timeout": TIKA_TIMEOUT_S},
            )
        except TypeError:
            parsed = parser.from_buffer(data, serverEndpoint=TIKA_URL)

    text = (parsed.get("content") or "").strip()
    if text:
        cache[key] = (now, text)

    return text


# ── Cached OpenAI client ──────────────────────────────────────────
@st.cache_resource
def get_llm_client() -> OpenAI:
    """Return a cached OpenAI client instance configured for the backend."""
    return OpenAI(base_url=LLM_BASE_URL, api_key="not-needed")


# ── Ollama model metadata ─────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _ollama_show() -> Optional[Dict]:
    """Cached wrapper for Ollama /api/show. Returns JSON dict on success, else None."""
    try:
        show_url = f"{_ollama_base_url()}/api/show"
        resp = requests.post(show_url, json={"model": MODEL_NAME}, timeout=2)
        if resp.ok:
            return resp.json()
    except Exception as e:
        logging.debug("Ollama /api/show probe failed: %s", e)
    return None


@st.cache_data(ttl=60, show_spinner=False)
def model_supports_images() -> bool:
    """
    Return True if the configured model appears to support vision inputs.

    Uses:
      1) LLM_SUPPORTS_VISION env var if provided.
      2) Ollama /api/show capabilities (preferred).
      3) Ollama model_info heuristics as a fallback.
    """
    if LLM_SUPPORTS_VISION is not None:
        return LLM_SUPPORTS_VISION.strip().lower() in {"1", "true", "yes", "y", "on"}

    payload = _ollama_show()
    if not payload:
        return False

    capabilities = payload.get("capabilities")
    if isinstance(capabilities, list) and "vision" in capabilities:
        return True

    model_info = payload.get("model_info") or {}
    for key in model_info.keys():
        if not isinstance(key, str):
            continue
        key_lower = key.lower()
        if "vision" in key_lower or "clip" in key_lower or "projector" in key_lower:
            return True

    return False


@st.cache_data(ttl=60, show_spinner=False)
def get_model_ctx() -> Optional[int]:
    """Return the model context size, if discoverable via /api/show."""
    payload = _ollama_show()
    if not payload:
        return None

    parameters = payload.get("parameters")
    if isinstance(parameters, str):
        match = re.search(r"\bnum_ctx\s+(\d+)", parameters)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                pass

    model_info = payload.get("model_info") or {}

    for key in ("num_ctx", "context_length"):
        value = model_info.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)

    for key, value in model_info.items():
        if isinstance(key, str) and key.endswith(".context_length"):
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)

    return None


@st.cache_data(ttl=60, show_spinner=False)
def get_image_token_cost() -> int:
    """Return tokens-per-image if provided by model metadata, else default."""
    payload = _ollama_show()
    if not payload:
        return IMG_TOKEN_COST_DEFAULT

    model_info = payload.get("model_info") or {}
    for key, value in model_info.items():
        if not isinstance(key, str):
            continue
        if key.endswith("mm.tokens_per_image"):
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)

    return IMG_TOKEN_COST_DEFAULT


# ── Token counting ────────────────────────────────────────────────
def _heuristic_token_estimate(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / TOKEN_HEURISTIC_CHARS_PER_TOKEN))


def _get_token_cache() -> Dict[str, int]:
    return st.session_state.setdefault("_token_count_cache", {})


def count_text_tokens(text: str) -> int:
    """
    Best-effort token count for text.

    If ENABLE_TOKEN_BUDGETING is on, we try Ollama /api/tokenize.
    If unavailable or slow, we silently fall back to a heuristic.

    UX rule: this function must not show user-facing warnings.
    """
    if not text:
        return 0

    cache = _get_token_cache()
    if len(cache) > TOKEN_CACHE_MAX_ENTRIES:
        cache.clear()

    key = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    if key in cache:
        return cache[key]

    if not ENABLE_TOKEN_BUDGETING:
        n = _heuristic_token_estimate(text)
        cache[key] = n
        return n

    if st.session_state.get("tokenizer_available") is False:
        n = _heuristic_token_estimate(text)
        cache[key] = n
        return n

    tokenize_url = f"{_ollama_base_url()}/api/tokenize"
    try:
        resp = requests.post(
            tokenize_url,
            json={"model": MODEL_NAME, "content": text},
            timeout=TOKENIZE_TIMEOUT_S,
        )

        if resp.status_code == 404:
            st.session_state["tokenizer_available"] = False
            n = _heuristic_token_estimate(text)
            cache[key] = n
            return n

        resp.raise_for_status()
        payload = resp.json()

        tokens = payload.get("tokens")
        if isinstance(tokens, list):
            n = len(tokens)
        elif isinstance(tokens, int):
            n = tokens
        elif isinstance(tokens, str) and tokens.isdigit():
            n = int(tokens)
        else:
            st.session_state["tokenizer_available"] = False
            n = _heuristic_token_estimate(text)

        st.session_state["tokenizer_available"] = True
        cache[key] = n
        return n
    except Exception:
        st.session_state["tokenizer_available"] = False
        n = _heuristic_token_estimate(text)
        cache[key] = n
        return n


# ── Chat message wrapper for CSS styling ──────────────────────────
def styled_chat_message(role: str, message_id: str = None):
    """Return a chat_message wrapped in a keyed container for CSS styling."""
    key = f"{role}-{message_id}" if message_id else f"{role}-{uuid.uuid4()}"
    return st.container(key=key).chat_message(role)


def build_message_text(messages: List[dict]) -> str:
    """Flatten message content into text for token estimation."""
    chunks: List[str] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "text":
                    text = part.get("text")
                    if text:
                        chunks.append(text)
        else:
            if content:
                chunks.append(str(content))
    return "\n".join(chunks)


# ── Copy helpers (sidebar-only) ───────────────────────────────────
def _extract_export_info(content: Union[str, list]) -> Tuple[List[str], List[str], str]:
    """
    Extract (doc_lines, img_lines, message_text) from message content.

    Notes:
    - We do NOT export the full extracted document text from Context:, only filenames and counts.
    - Synthetic context parts (marked with _synthetic flag) are parsed for metadata only.
    """
    doc_lines: List[str] = []
    img_lines: List[str] = []
    text_chunks: List[str] = []

    if not isinstance(content, list):
        return doc_lines, img_lines, "" if content is None else str(content)

    doc_seen = set()
    img_seen = set()
    img_marker_names: List[str] = []

    for part in content:
        ptype = part.get("type")

        if ptype == "text":
            text = part.get("text", "")

            if part.get("_synthetic"):
                ctx = text[len(CONTEXT_PREFIX) :] if text.startswith(CONTEXT_PREFIX) else text
                blocks = re.split(r"(?m)^---\s*(.+?)\s*---\s*$", ctx)
                for i in range(1, len(blocks), 2):
                    fname = (blocks[i] or "").strip()
                    extracted = blocks[i + 1] if i + 1 < len(blocks) else ""
                    char_count = len((extracted or "").strip())
                    if fname and fname not in doc_seen:
                        doc_seen.add(fname)
                        doc_lines.append(f"- 📄 {fname} ({char_count:,} characters extracted)")

            elif text.startswith("📄 *") and text.endswith("*"):
                fname = text[len("📄 *") : -1].strip()
                if fname and fname not in doc_seen:
                    doc_seen.add(fname)
                    doc_lines.append(f"- 📄 {fname}")

            elif text.startswith("📷 *") and text.endswith("*"):
                fname = text[len("📷 *") : -1].strip()
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

        elif ptype == "image_url":
            fname = (part.get("filename") or "image").strip()
            if fname and fname not in img_seen:
                img_seen.add(fname)
                img_lines.append(f"- 📷 {fname}")

    for fname in img_marker_names:
        if fname not in img_seen:
            img_seen.add(fname)
            img_lines.append(f"- 📷 {fname}")

    message_text = "\n\n".join(text_chunks).strip()
    return doc_lines, img_lines, message_text


def build_conversation_markdown(messages: List[dict]) -> str:
    """Build a Markdown transcript used as plain-text clipboard fallback."""
    lines: List[str] = ["# EphemerAl Conversation", ""]

    for msg in messages:
        role = msg.get("role", "assistant")
        role_title = "User" if role == "user" else "Assistant"
        lines.append(f"**{role_title}**")

        doc_lines, img_lines, message_text = _extract_export_info(msg.get("content", ""))

        if doc_lines or img_lines:
            lines.append("")
            lines.append("Attachments:")
            lines.extend(doc_lines)
            lines.extend(img_lines)

        if message_text:
            lines.append("")
            lines.append(message_text)

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _inline_md_to_html(text: str) -> str:
    """Minimal inline Markdown -> HTML for clipboard friendliness."""
    t = html_escape(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


def _md_block_to_html(md_block: str) -> str:
    """Minimal block Markdown -> HTML for clipboard friendliness."""
    md_block = (md_block or "").replace("\r\n", "\n")
    lines = md_block.split("\n")

    out: List[str] = []
    para: List[str] = []
    in_ul = False
    in_ol = False

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append("<p>" + "<br>".join(para) + "</p>")
            para = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw in lines:
        stripped = (raw or "").strip()

        if stripped == "":
            flush_para()
            continue

        if stripped in {"---", "***", "___"}:
            flush_para()
            close_lists()
            out.append("<hr>")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            close_lists()
            level = len(m.group(1))
            out.append(f"<h{level}>" + _inline_md_to_html(m.group(2)) + f"</h{level}>")
            continue

        m = re.match(r"^[-*•]\s+(.*)$", stripped)
        if m:
            flush_para()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>" + _inline_md_to_html(m.group(1)) + "</li>")
            continue

        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            flush_para()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append("<li>" + _inline_md_to_html(m.group(1)) + "</li>")
            continue

        close_lists()
        para.append(_inline_md_to_html(stripped))

    flush_para()
    close_lists()
    return "\n".join(out)


def _md_to_html_basic(md: str) -> str:
    """Minimal Markdown -> HTML converter for copy/paste purposes."""
    md = (md or "").replace("\r\n", "\n")
    parts = md.split("```")
    out: List[str] = []

    for i, part in enumerate(parts):
        if i % 2 == 1:
            code = html_escape(part.strip("\n"))
            out.append("<pre><code>" + code + "</code></pre>")
        else:
            block_html = _md_block_to_html(part)
            if block_html.strip():
                out.append(block_html)

    return "\n".join(out).strip()


def build_conversation_html(messages: List[dict]) -> str:
    """Rich transcript as HTML for clipboard copy."""
    chunks: List[str] = ["<div>", "<p><strong>EphemerAl Conversation</strong></p>"]

    for msg in messages:
        role = msg.get("role", "assistant")
        role_title = "User" if role == "user" else "Assistant"
        chunks.append(f"<p><strong>{html_escape(role_title)}</strong></p>")

        doc_lines, img_lines, message_text = _extract_export_info(msg.get("content", ""))

        if doc_lines or img_lines:
            chunks.append("<p><strong>Attachments:</strong></p>")
            chunks.append("<ul>")
            for line in (doc_lines + img_lines):
                item = line.lstrip("- ").strip()
                chunks.append("<li>" + _inline_md_to_html(item) + "</li>")
            chunks.append("</ul>")

        if message_text:
            chunks.append(_md_to_html_basic(message_text))

        chunks.append("<hr>")

    chunks.append("</div>")
    return "\n".join(chunks).strip()


def render_copy_button(export_text_plain: str, export_html: str) -> None:
    """Sidebar-only copy button that tries rich HTML copy first, then plain text."""
    safe_plain = html_escape(export_text_plain)

    hover_tip = (
        "Copy this conversation to your clipboard. "
        "Chat content is cleared when you start a new conversation or close your browser."
    )

    components.html(
        f"""
        <style>
          html, body {{
            margin: 0;
            padding: 0;
          }}
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
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI Variable",
                "Segoe UI",
                Roboto,
                sans-serif;
            padding: 0.7rem 1rem;
            margin: 0;
            transition: all .2s;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
            border-radius: 8px;
            cursor: pointer;
            white-space: nowrap;
          }}
          #copy-btn:hover {{
            background: #E1654A;
            color: white;
            transform: translateY(-1px);
            box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
          }}
          #copy-btn:active {{
            background: #C4503A !important;
            color: white !important;
            border-color: #C4503A !important;
            transform: translateY(0);
          }}
          #copy-btn.copied {{
            background: #E1654A !important;
            color: white !important;
            border-color: #E1654A !important;
            transform: translateY(0) !important;
          }}
          #copy-btn.failed {{
            background: #B00020 !important;
            color: white !important;
            border-color: #B00020 !important;
            transform: translateY(0) !important;
          }}
        </style>

        <button id="copy-btn" title="{html_escape(hover_tip)}">Copy Conversation</button>

        <textarea id="copy-plain"
                  style="position:absolute; left:-9999px; top:-9999px;">{safe_plain}</textarea>

        <div id="copy-rich"
             contenteditable="true"
             style="position:absolute; left:-9999px; top:-9999px; width:900px;">
          {export_html}
        </div>

        <script>
          const btn = document.getElementById("copy-btn");
          const plain = document.getElementById("copy-plain");
          const rich = document.getElementById("copy-rich");
          const originalLabel = btn.textContent;

          function flash(stateClass, label, ms) {{
            btn.disabled = true;
            btn.classList.add(stateClass);
            btn.textContent = label;

            window.setTimeout(() => {{
              btn.disabled = false;
              btn.classList.remove(stateClass);
              btn.textContent = originalLabel;
            }}, ms);
          }}

          function copySelectionFrom(el) {{
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(el);
            selection.removeAllRanges();
            selection.addRange(range);
            el.focus();

            let ok = false;
            try {{
              ok = document.execCommand("copy");
            }} catch (e) {{
              ok = false;
            }}

            selection.removeAllRanges();
            return ok;
          }}

          function copyPlain() {{
            plain.focus();
            plain.select();
            let ok = false;
            try {{
              ok = document.execCommand("copy");
            }} catch (e) {{
              ok = false;
            }}
            return ok;
          }}

          btn.addEventListener("click", () => {{
            const richOk = copySelectionFrom(rich);
            const ok = richOk || copyPlain();

            if (ok) {{
              flash("copied", "Copied", 900);
            }} else {{
              flash("failed", "Copy failed", 1500);
            }}
          }});
        </script>
        """,
        height=70,
        scrolling=False,
    )


# ── Session state ─────────────────────────────────────────────────
st.session_state.setdefault("messages", [])
st.session_state.setdefault("show_welcome", True)
st.session_state.setdefault("last_token_count", 0)
st.session_state.setdefault("tokenizer_available", None)
st.session_state.setdefault("_vision_supported", None)

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    try:
        logo_path = pathlib.Path("static/ephemeral_logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    except Exception:
        st.markdown("EphemerAl")

    # Friendly status messages for non-technical users.
    if not llm_alive():
        st.error("The AI service is not available right now. Please try again in a moment.")
    if not tika_alive():
        st.info("Document reading is temporarily unavailable. You can still chat, but uploads may not be readable.")

    if st.button("New Conversation", key="sidebar_new", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    if st.session_state.messages:
        export_md = build_conversation_markdown(st.session_state.messages)
        export_html = build_conversation_html(st.session_state.messages)
        render_copy_button(export_md, export_html)

    if DEBUG_MODE:
        with st.expander("System status", expanded=False):
            st.caption(f"App version: {APP_VERSION}")
            st.caption(f"Model: {MODEL_NAME}")
            st.caption(f"LLM base URL: {LLM_BASE_URL}")

            tok_state = st.session_state.get("tokenizer_available")
            if not ENABLE_TOKEN_BUDGETING:
                st.caption("Token counting: safe estimate mode (disabled by configuration)")
            elif tok_state is True:
                st.caption("Token counting: Ollama tokenizer endpoint")
            elif tok_state is False:
                st.caption("Token counting: safe estimate mode")
            else:
                st.caption("Token counting: not checked yet")


# ── Welcome banner ────────────────────────────────────────────────
if st.session_state.show_welcome:
    wordmark_png = pathlib.Path("static/ephemeral_wordmark.png")
    wordmark_svg = pathlib.Path("static/ephemeral_wordmark.svg")
    wordmark_path = wordmark_png if wordmark_png.exists() else (wordmark_svg if wordmark_svg.exists() else None)

    if wordmark_path:
        wordmark_b64 = base64.b64encode(wordmark_path.read_bytes()).decode()
        mime_type = "image/svg+xml" if wordmark_path.suffix == ".svg" else "image/png"
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
          I can read many document types, and sometimes images (depending on the model).
          <div class="welcome-dots">•&nbsp;&nbsp;•&nbsp;&nbsp;•</div>
          Conversations are cleared when you start a new conversation or close your browser.
          <div class="welcome-dots">•&nbsp;&nbsp;•&nbsp;&nbsp;•</div>
          I try to be helpful, but I can be wrong. Please double-check important answers.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Helper: render chat content ───────────────────────────────────
def render_content(content: Union[str, list]) -> None:
    """
    Render either plain markdown or structured content (text + images).
    Synthetic context blocks (marked with _synthetic flag) are hidden from display.
    """
    if isinstance(content, list):
        for part in content:
            ptype = part.get("type")
            if ptype == "text":
                if not part.get("_synthetic"):
                    st.markdown(part.get("text", ""))
            elif ptype == "image":
                try:
                    st.image(part.get("data"), width=180)
                except Exception:
                    st.error("I couldn't display one of the images in the chat UI.")
            elif ptype == "image_url":
                try:
                    st.image(part["image_url"]["url"], width=180)
                except Exception:
                    st.error("I couldn't display one of the images in the chat UI.")
    else:
        st.markdown(content or "")


# ── Render chat history ───────────────────────────────────────────
for m in st.session_state.messages:
    with styled_chat_message(m["role"], m.get("id")):
        render_content(m["content"])


# ── Mobile convenience button ─────────────────────────────────────
if HAS_DEVICE_DETECTION and device and device.is_mobile:
    if st.button("🔄 New Conversation", key="mobile_new", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ── Chat input ───────────────────────────────────────────────────
prompt_in = st.chat_input("Ask me anything…", accept_file="multiple", key="main_chat")
prompt_in = st.session_state.pop("_first_prompt_pending", None) or prompt_in

if prompt_in is not None:
    if st.session_state.show_welcome:
        st.session_state.show_welcome = False
        st.session_state["_first_prompt_pending"] = prompt_in
        st.rerun()

    user_text = prompt_in.text if hasattr(prompt_in, "text") else prompt_in
    user_text = (user_text or "").strip()
    files = prompt_in.files if hasattr(prompt_in, "files") else []

    if not user_text and files:
        user_text = DEFAULT_UPLOAD_PROMPT

    if not user_text and not files:
        st.stop()

    user_msg_id = str(uuid.uuid4())

    with styled_chat_message("user", user_msg_id):
        st.markdown(user_text)

    sys_prompt = SYSTEM_TMPL.safe_substitute(current_time_local=timestamp_local())

    vision_supported = model_supports_images()
    prev_vision = st.session_state.get("_vision_supported")
    if prev_vision is None:
        st.session_state["_vision_supported"] = vision_supported
    elif prev_vision != vision_supported:
        st.session_state["_vision_supported"] = vision_supported
        st.session_state["last_token_count"] = 0

    model_ctx = get_model_ctx()
    if model_ctx:
        max_ctx = int(model_ctx * 0.95)
        warn_ctx = int(model_ctx * 0.85)
    else:
        max_ctx = 128000
        warn_ctx = int(max_ctx * 0.85)

    image_token_cost = get_image_token_cost() if vision_supported else 0

    parts: List[dict] = []
    doc_entries: List[dict] = []
    image_count = 0

    tika_ok = tika_alive()
    has_doc_files = any(not getattr(f, "type", "").startswith("image/") for f in files)
    if has_doc_files and not tika_ok:
        st.info(
            "I can’t read documents right now, but I can still answer questions. "
            "If you paste text from the document, I can work with that."
        )

    for f in files:
        ftype = getattr(f, "type", "")

        if ftype.startswith("image/"):
            if getattr(f, "size", 0) > 50 * 1024 * 1024:
                st.info(f"{f.name} is a large image and may take a bit to process.")

            f.seek(0)
            img_bytes = f.getvalue()
            parts.append({"type": "text", "text": f"📷 *{f.name}*"})
            parts.append(
                {
                    "type": "image",
                    "data": img_bytes,
                    "mime_type": ftype or "image/jpeg",
                    "filename": f.name,
                }
            )
            image_count += 1
            continue

        # Document-like file
        parts.append({"type": "text", "text": f"📄 *{f.name}*"})
        if not tika_ok:
            continue

        try:
            f.seek(0)
            data = f.getvalue()
            txt = parse_with_tika(data, f.name)

            if txt:
                block = f"--- {f.name} ---\n{txt}"
                doc_entries.append({"name": f.name, "block": block})
            else:
                st.info(
                    f"I couldn’t extract text from {f.name}. "
                    "If it’s a scanned PDF, try a text-based version or paste the relevant text here."
                )
        except Exception as e:
            st.info(f"I couldn’t read {f.name}. You can try uploading it again, or try a different format.")
            if DEBUG_MODE:
                with st.expander(f"Details: {f.name}", expanded=False):
                    st.code(str(e))

    def compute_pending_text(entries: List[dict]) -> str:
        """
        Pending text used for context budgeting.
        Intentionally ignores filename markers to avoid estimation drift and stale marker bugs.
        """
        chunks: List[str] = []
        if entries:
            doc_blocks = "\n\n".join(entry["block"] for entry in entries)
            chunks.append(CONTEXT_PREFIX + doc_blocks)
        if user_text:
            chunks.append(user_text)
        return "\n\n".join(chunks).strip()

    def estimate_pending_cost(entries: List[dict]) -> int:
        pending_text = compute_pending_text(entries)
        text_tokens = count_text_tokens(pending_text)
        image_tokens = (image_count * image_token_cost) if vision_supported else 0
        return text_tokens + image_tokens

    # Base tokens:
    # - If we have last_token_count from the previous turn, use it as baseline (hybrid approach).
    # - Otherwise use a quick heuristic for system + history to keep UI responsive.
    if st.session_state.last_token_count == 0:
        history_text = build_message_text(st.session_state.messages)
        base_tokens = _heuristic_token_estimate(sys_prompt) + _heuristic_token_estimate(history_text)
    else:
        base_tokens = int(st.session_state.last_token_count)

    pending_tokens = estimate_pending_cost(doc_entries)
    prompt_token_estimate = base_tokens + pending_tokens

    skipped_docs: List[str] = []
    while doc_entries and prompt_token_estimate > max_ctx:
        dropped = doc_entries.pop()
        skipped_docs.append(dropped["name"])
        pending_tokens = estimate_pending_cost(doc_entries)
        prompt_token_estimate = base_tokens + pending_tokens

    # Ghost doc cleanup: remove dropped doc markers from parts
    if skipped_docs:
        dropped_set = set(skipped_docs)
        parts = [
            part
            for part in parts
            if not (
                part.get("type") == "text"
                and part.get("text", "").strip().startswith("📄 *")
                and part.get("text", "").strip().endswith("*")
                and part.get("text", "").strip()[3:-1].strip() in dropped_set
            )
        ]

    # Build synthetic doc context
    doc_ctx_blocks: List[str] = [entry["block"] for entry in doc_entries]
    if doc_ctx_blocks:
        parts.insert(
            0,
            {
                "type": "text",
                "text": CONTEXT_PREFIX + "\n\n".join(doc_ctx_blocks),
                "_synthetic": True,
            },
        )

    if user_text:
        parts.append({"type": "text", "text": user_text})

    # Calm note about images when the model can't see them
    if image_count > 0 and not vision_supported:
        st.info("This AI can’t read images in this setup. If you describe what’s in the image, I can still help.")

    # Store the user's message in session state now (so it doesn't disappear on reruns)
    content_for_llm: Union[str, List[dict]] = parts if len(parts) > 1 else user_text
    st.session_state.messages.append(
        {
            "id": user_msg_id,
            "role": "user",
            "content": content_for_llm,
        }
    )

    # If still too large even after dropping docs, respond as assistant and stop.
    if prompt_token_estimate > max_ctx:
        assistant_msg_id = str(uuid.uuid4())
        error_text = (
            "That request is too large for this AI model right now. "
            "Try removing a few attachments, shortening your message, or starting a new conversation."
        )
        with styled_chat_message("assistant", assistant_msg_id):
            st.markdown(error_text)
        st.session_state.messages.append(
            {
                "id": assistant_msg_id,
                "role": "assistant",
                "content": error_text,
            }
        )
        st.stop()

    if skipped_docs:
        unique_docs = ", ".join(sorted(set(skipped_docs)))
        st.info(
            "To keep things within the AI’s memory, I left out these attachments: "
            f"{unique_docs}. If you need them, try uploading fewer files at once."
        )

    if prompt_token_estimate >= warn_ctx:
        st.info(
            "This conversation is getting pretty long. If the AI starts to forget earlier details, "
            "starting a new conversation usually helps."
        )

    # Convert stored messages to OpenAI-compatible payload
    messages_for_api: List[dict] = []
    for msg in st.session_state.messages:
        if isinstance(msg["content"], list):
            api_parts: List[dict] = []
            for part in msg["content"]:
                ptype = part.get("type")

                if ptype == "text":
                    api_parts.append({"type": "text", "text": part.get("text", "")})

                elif ptype == "image":
                    if vision_supported:
                        img_bytes = part.get("data") or b""
                        img_b64 = part.get("b64")
                        if not img_b64:
                            img_b64 = base64.b64encode(img_bytes).decode()
                            part["b64"] = img_b64  # cache per-session
                        mime = part.get("mime_type", "image/jpeg")
                        api_parts.append(
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
                        )

                elif ptype == "image_url":
                    if vision_supported:
                        api_parts.append(part)

            # Avoid sending empty content arrays (some backends reject them).
            if not api_parts:
                api_parts = [{"type": "text", "text": "(Attachment omitted.)"}]

            messages_for_api.append({"role": msg["role"], "content": api_parts})
        else:
            messages_for_api.append({"role": msg["role"], "content": msg["content"]})

    payload = [{"role": "system", "content": sys_prompt}, *messages_for_api]

    assistant_msg_id = str(uuid.uuid4())

    with styled_chat_message("assistant", assistant_msg_id):
        with st.spinner("Thinking…"):
            try:
                client = get_llm_client()

                # Try include_usage if supported, fall back otherwise.
                try:
                    stream = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=payload,
                        stream=True,
                        stream_options={"include_usage": True},
                    )
                except TypeError:
                    stream = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=payload,
                        stream=True,
                    )
                except Exception as e:
                    if "stream_options" in str(e) or "include_usage" in str(e):
                        stream = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=payload,
                            stream=True,
                        )
                    else:
                        raise

                acc = ""
                box = st.empty()
                used_usage_from_backend = False

                for chunk in stream:
                    if getattr(chunk, "choices", None):
                        delta = chunk.choices[0].delta.content
                        if delta:
                            acc += delta
                            box.markdown(acc + "▌")

                    usage = getattr(chunk, "usage", None)
                    if usage and getattr(usage, "total_tokens", None) is not None:
                        st.session_state.last_token_count = int(usage.total_tokens)
                        used_usage_from_backend = True

                box.markdown(acc)

                # If backend didn't provide usage totals, keep hybrid behavior with a fast estimate.
                if not used_usage_from_backend:
                    completion_est = _heuristic_token_estimate(acc)
                    st.session_state.last_token_count = int(prompt_token_estimate + completion_est)

                st.session_state.messages.append(
                    {
                        "id": assistant_msg_id,
                        "role": "assistant",
                        "content": acc,
                    }
                )
                st.rerun()

            except Exception as e:
                msg = str(e)
                lower = msg.lower()

                if "context" in lower and ("length" in lower or "too long" in lower or "maximum" in lower):
                    st.error(
                        "That message is too long for this AI model. "
                        "Try removing a few attachments, shortening your message, or starting a new conversation."
                    )
                elif "connection" in lower or "timed out" in lower or "timeout" in lower:
                    st.error("I couldn't reach the AI service. Please try again in a moment.")
                else:
                    st.error("Something went wrong while talking to the AI service. Please try again.")

                if DEBUG_MODE:
                    with st.expander("Details for troubleshooting", expanded=False):
                        st.code(msg)
