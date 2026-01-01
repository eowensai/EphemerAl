import os
import base64
import hashlib
import pathlib
import re
import string
import time
import uuid
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
# Prefix used for synthetic context blocks injected into user messages.
# We use a flag (_synthetic) to identify these, not string matching.
CONTEXT_PREFIX = "Context:\n"

# TTL for session-scoped Tika parse cache (seconds)
TIKA_CACHE_TTL_S = 3600

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="EphemerAl",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── Anti-caching meta tags ────────────────────────────────────────
# These headers ask the browser not to cache this page. This helps reduce the
# chance that chat content or uploaded documents remain in browser cache on
# shared machines, but it still depends on how the browser honors cache hints.
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


# ── Health checks (cached to reduce UI jank) ──────────────────────
@st.cache_data(ttl=5, show_spinner=False)
def tika_alive() -> bool:
    """
    Lightweight health check for the Tika server at TIKA_URL.
    Cached for 5 seconds to avoid repeated network calls on reruns.
    """
    try:
        return requests.get(TIKA_URL, timeout=2).ok
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
        if r.status_code in (200, 401, 403):
            return True
        
        # Ollama fallback - strip /v1 if present and try /api/tags
        # Note: split("/v1")[0] returns the whole string if /v1 isn't present
        ollama_base = base_url.split("/v1")[0]
        r2 = requests.get(ollama_base + "/api/tags", timeout=2)
        return r2.ok
    except Exception:
        return False


def get_local_timezone() -> tzinfo:
    """
    Resolve the timezone used for UI timestamps and the system prompt.

    Priority:
      1. EPHEMERAL_TIMEZONE env var (e.g. "America/Los_Angeles") if set and valid.
      2. The system's local timezone as reported by datetime.now().astimezone().

    This matches the older fork behavior and makes the docker-compose comment about
    EPHEMERAL_TIMEZONE functional.
    """
    env_tz = os.getenv("EPHEMERAL_TIMEZONE")
    if env_tz:
        try:
            return pytz.timezone(env_tz)
        except Exception:
            # If the configured value is invalid, log a warning in the UI if possible,
            # then fall back to the system local timezone.
            try:
                st.warning(
                    f"EPHEMERAL_TIMEZONE={env_tz!r} is not a valid timezone; "
                    "falling back to system local timezone."
                )
            except Exception:
                pass

    sys_tz = datetime.now().astimezone().tzinfo
    return sys_tz or pytz.UTC


TIMEZONE = get_local_timezone()


def timestamp_local() -> str:
    """
    Return a human-readable local timestamp string.

    Uses TIMEZONE resolved at startup. Format is adjusted slightly for Windows
    because strftime flags differ between platforms.
    """
    now = datetime.now(TIMEZONE)
    fmt = "%-I:%M %p on %A, %B %-d, %Y"
    if os.name == "nt":
        # Windows strftime does not support %-I / %-d, so use %# variants.
        fmt = fmt.replace("%-I", "%#I").replace("%-d", "%#d")
    return now.strftime(fmt)


tmpl_path = pathlib.Path(__file__).parent / "system_prompt_template.md"
if tmpl_path.exists():
    # If a template file is present, use it so operators can adjust tone/content
    # without modifying this code.
    SYSTEM_TMPL = string.Template(tmpl_path.read_text(encoding="utf-8"))
else:
    # Fallback system prompt if the template file is missing.
    SYSTEM_TMPL = string.Template(
        "You are a helpful AI assistant. The current local time is ${current_time_local}. "
        "Answer concisely and accurately based on the context provided."
    )


# ── Session-scoped Tika parsing cache ─────────────────────────────
# We cache parsed document text per-session (not globally) to honor the app's
# "ephemeral" privacy posture. Keyed by SHA-256 of file bytes.
def _get_tika_cache() -> dict:
    """Return the session-scoped Tika parse cache, creating if needed."""
    return st.session_state.setdefault("_tika_cache", {})


def parse_with_tika(data: bytes, filename: str) -> str:
    """
    Parse document bytes with Tika via TIKA_URL.
    
    Results are cached per-session by content hash (SHA-256) with TTL.
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
        parsed = parser.from_buffer(data, serverEndpoint=TIKA_URL)
    text = (parsed.get("content") or "").strip()
    
    # Only cache non-empty results - empty might be a transient Tika issue
    if text:
        cache[key] = (now, text)
    
    return text


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
    key = f"{role}-{message_id}" if message_id else f"{role}-{uuid.uuid4()}"
    return st.container(key=key).chat_message(role)


# ── Copy helpers (sidebar-only) ───────────────────────────────────
# We avoid downloads entirely to sidestep Chrome's insecure-download blocking on HTTP.
# We also avoid rendering a full transcript "preview" in the main pane, which duplicates
# the chat and gets clunky as conversations grow.
def _extract_export_info(content: Union[str, list]) -> Tuple[List[str], List[str], str]:
    """
    Extract (doc_lines, img_lines, message_text) from message content.

    Notes:
    - We do NOT export the full extracted document text from Context:, only filenames and counts.
    - We DO include document filenames even if Tika is offline (📄 *filename* markers).
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
            
            # Handle synthetic context blocks (flagged, not string-matched)
            if part.get("_synthetic"):
                # Parse the context block to extract filenames and char counts
                ctx = text[len(CONTEXT_PREFIX):] if text.startswith(CONTEXT_PREFIX) else text
                # Anchored regex to reduce false matches from document content
                blocks = re.split(r"(?m)^---\s*(.+?)\s*---\s*$", ctx)
                # blocks alternates: ['', 'filename1', 'content1', 'filename2', 'content2', ...]
                for i in range(1, len(blocks), 2):
                    fname = (blocks[i] or "").strip()
                    extracted = blocks[i + 1] if i + 1 < len(blocks) else ""
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
    """
    Minimal inline Markdown -> HTML for clipboard friendliness.
    """
    t = html_escape(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


def _md_block_to_html(md_block: str) -> str:
    """
    Minimal block Markdown -> HTML.
    Handles headings, lists, horizontal rules, and paragraphs.
    
    Limitations: No nested lists, no tables, no blockquotes.
    Used for clipboard-friendly export, not full rendering.
    """
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

        # Regular paragraph line
        close_lists()
        para.append(_inline_md_to_html(stripped))

    flush_para()
    close_lists()

    return "\n".join(out)


def _md_to_html_basic(md: str) -> str:
    """
    Minimal Markdown -> HTML converter for copy/paste purposes.
    Handles fenced code blocks (```), lists, headings, hr, and inline formatting.
    """
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
    """
    Rich transcript as HTML.
    This is what the copy button tries first (best chance of bullets/bold carrying into Word/Outlook).
    """
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
        "Chat content is cleared when you refresh or start a new conversation."
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

          /* Flash states */
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
            // Try rich first (better paste into Word/Outlook), then plain fallback.
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


# ── Session state (ephemeral by default) ──────────────────────────
# Initialize in-memory conversation state. Streamlit clears this when the browser
# session ends or when we explicitly clear it; there is no persistent database.
st.session_state.setdefault("messages", [])
st.session_state.setdefault("show_welcome", True)

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    # Try to show a local logo first; fall back to text branding if missing.
    try:
        logo_path = pathlib.Path("static/ephemeral_logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    except Exception:
        st.markdown("**EphemerAl**")

    # Basic health indicators for the backends this UI depends on.
    if not llm_alive():
        st.error("⚠️ LLM backend offline")
    if not tika_alive():
        st.warning("⚠️ Document parsing offline")

    # New Conversation clears all session_state (messages + welcome banner + parse cache).
    if st.button("New Conversation", key="sidebar_new", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # Copy Conversation (sidebar-only). Avoids downloads and avoids duplicating the chat in main UI.
    if st.session_state.messages:
        export_md = build_conversation_markdown(st.session_state.messages)
        export_html = build_conversation_html(st.session_state.messages)
        render_copy_button(export_md, export_html)

# ── Welcome banner ────────────────────────────────────────────────
if st.session_state.show_welcome:
    # WORDMARK DISPLAY OPTIONS:
    # Default: Image-based wordmark (static/ephemeral_wordmark.png or .svg)
    #          Supports proper gradients, scales cleanly, looks polished.
    #          Replace the image file to customize.
    #
    # Fallback: Text-based wordmark (uses solid colors from theme.css)
    #           Automatically used if wordmark image file is not present.
    #           To force text mode: delete or rename the wordmark file.

    # Check for wordmark image (supports both PNG and SVG)
    wordmark_png = pathlib.Path("static/ephemeral_wordmark.png")
    wordmark_svg = pathlib.Path("static/ephemeral_wordmark.svg")
    wordmark_path = wordmark_png if wordmark_png.exists() else (wordmark_svg if wordmark_svg.exists() else None)

    if wordmark_path:
        # Image-based wordmark
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
          Conversations are cleared when you refresh, start a new conversation, or close your browser.
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
    files = prompt_in.files if hasattr(prompt_in, "files") else []

    # Generate stable ID for user message
    user_msg_id = str(uuid.uuid4())

    with styled_chat_message("user", user_msg_id):
        st.markdown(user_text)

    parts, doc_ctx = [], []
    for f in files:
        if f.type.startswith("image/"):
            # Large images will still be accepted, but we warn that processing
            # may be slow rather than silently failing.
            if f.size > 50 * 1024 * 1024:
                st.warning(f"📷 {f.name} is {f.size/1e6:.1f} MB – may be slow to process")

            f.seek(0)
            img_bytes = f.getvalue()
            parts.append({"type": "text", "text": f"📷 *{f.name}*"})
            parts.append(
                {
                    "type": "image",
                    "data": img_bytes,
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
                    doc_ctx.append(f"--- {f.name} ---\n{txt}")
            except Exception as e:
                st.error(f"❌ {f.name}: {e}")

    # If we successfully parsed any documents, prepend them to the content that
    # will be sent to the model as a synthetic context block (flagged, not string-matched).
    if doc_ctx:
        parts.insert(0, {
            "type": "text",
            "text": CONTEXT_PREFIX + "\n\n".join(doc_ctx),
            "_synthetic": True  # Flag to identify synthetic blocks
        })
    parts.append({"type": "text", "text": user_text})

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
    for msg in st.session_state.messages:
        if isinstance(msg["content"], list):
            api_parts = []
            for part in msg["content"]:
                if part.get("type") == "text":
                    api_parts.append({"type": "text", "text": part["text"]})
                elif part.get("type") == "image":
                    # Convert raw image bytes to data: URLs that OpenAI-compatible
                    # image endpoints expect. Cache base64 on the part so repeated
                    # sends in the same session do not re-encode.
                    if "b64" not in part:
                        part["b64"] = base64.b64encode(part["data"]).decode()
                    api_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{part.get('mime_type', 'image/jpeg')};base64,{part['b64']}"
                            },
                        }
                    )
                elif part.get("type") == "image_url":
                    api_parts.append(part)
            messages_for_api.append({"role": msg["role"], "content": api_parts})
        else:
            messages_for_api.append({"role": msg["role"], "content": msg["content"]})

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
                })
                # Rerun to re-render full history with the new assistant message.
                st.rerun()
            except Exception as e:
                st.error(f"❌ LLM Error: {e}")
