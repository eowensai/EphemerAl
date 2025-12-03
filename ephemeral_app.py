import os, base64, pathlib, string
from datetime import datetime, tzinfo
from typing import Union

import streamlit as st
import requests, pytz
from tika import parser
from openai import OpenAI

# EphemerAl main Streamlit application.
# - Provides an ephemeral chat UI for working with uploaded documents and images.
# - Talks to an LLM backend and an Apache Tika server over HTTP endpoints configured via environment variables.
# - Uses Streamlit's in-memory session_state only; this script does not write chat content or uploads to disk.

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

try:
    from streamlit_browser_engine import device
    HAS_DEVICE_DETECTION = True
except ImportError:
    # Device detection is optional; the app still works without it.
    HAS_DEVICE_DETECTION = False
    device = None

# HTTP endpoints and model name are configurable so the app can talk to different
# backends (e.g. local Docker containers or remote services).
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemma3-prod")
TIKA_URL = os.getenv("TIKA_URL", "http://tika-server:9998")


def tika_alive() -> bool:
    """Lightweight health check for the Tika server at TIKA_URL."""
    try:
        return requests.get(TIKA_URL, timeout=2).ok
    except Exception:
        return False


TIKA_OK = tika_alive()


def llm_alive() -> bool:
    """Lightweight health check for the LLM backend derived from LLM_BASE_URL."""
    try:
        base = LLM_BASE_URL.split("/v1")[0]
        return requests.get(base + "/api/tags", timeout=2).ok
    except Exception:
        return False


def get_local_timezone() -> tzinfo:
    """
    Resolve the timezone used for UI timestamps and the system prompt.

    Priority:
      1. EPHEMERAL_TIMEZONE env var (e.g. "America/Los_Angeles") if set and valid.
      2. The system's local timezone as reported by datetime.now().astimezone().
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
                # If Streamlit is not ready yet, ignore the warning.
                pass
    return datetime.now().astimezone().tzinfo


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


# ── Cached Tika parsing ───────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Parsing document…")
def parse_with_tika(data: bytes, filename: str) -> str:
    """
    Parse document bytes with Tika via TIKA_URL.

    Results are cached by Streamlit for 1 hour (per unique (data, filename) input),
    which avoids repeatedly parsing the same file in one session.
    """
    return parser.from_buffer(data, serverEndpoint=TIKA_URL).get("content", "").strip()


# ── Cached OpenAI client ──────────────────────────────────────────
@st.cache_resource
def get_llm_client() -> OpenAI:
    """
    Return a cached OpenAI client instance.

    The client is configured to talk to LLM_BASE_URL (typically an Ollama‑compatible
    endpoint). The api_key value is a placeholder because most local backends
    ignore it, but the OpenAI client requires something to be set.
    """
    return OpenAI(base_url=LLM_BASE_URL, api_key="not-needed")


# Initialize in-memory conversation state. Streamlit clears this when the browser
# session ends or when we explicitly clear it; there is no persistent database.
st.session_state.setdefault("messages", [])
st.session_state.setdefault("show_welcome", True)

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    # Try to show a local logo first; fall back to text branding if the image is
    # missing or cannot be loaded.
    try:
        logo_path = pathlib.Path("static/ephemeral_logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    except Exception:
        st.markdown("**EphemerAl**")

    # Basic health indicators for the backends this UI depends on.
    if not llm_alive():
        st.error("⚠️ LLM backend offline")
    if not TIKA_OK:
        st.warning("⚠️ Document parsing offline")

    # New Conversation clears all session_state (messages + welcome banner).
    if st.button("New Conversation", key="sidebar_new", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── Welcome banner ────────────────────────────────────────────────
if st.session_state.show_welcome:
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
          I understand image files and most (100+!) document types.<br>
          <div style="text-align:center;margin:0.7rem 0;font-size:7px;color:#6B5B95;letter-spacing:10px;">• • •</div>
          Conversations are erased when you refresh, hit "New Conversation", or close your browser.<br>
          <div style="text-align:center;margin:0.7rem 0;font-size:7px;color:#6B5B95;letter-spacing:10px;">• • •</div>
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
    """
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                # Hide the synthetic "Context:" block from display; it is meant
                # only for the model, not the human user.
                if not part["text"].startswith("Context:"):
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
    with st.chat_message(m["role"]):
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

    with st.chat_message("user"):
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
            if not TIKA_OK:
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
    # will be sent to the model as a synthetic "Context:" block.
    if doc_ctx:
        parts.insert(0, {"type": "text", "text": "Context:\n" + "\n\n".join(doc_ctx)})
    parts.append({"type": "text", "text": user_text})
    content_for_llm = parts if len(parts) > 1 else user_text

    st.session_state.messages.append({"role": "user", "content": content_for_llm})

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
                    api_parts.append(part)
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
            messages_for_api.append(msg)

    # Prepend the system message so the backend sees the time-aware instructions.
    payload = [{"role": "system", "content": sys_prompt}, *messages_for_api]

    # ── Call LLM ───────────────────────────────────────────────────
    with st.chat_message("assistant"), st.spinner("Thinking…"):
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
            st.session_state.messages.append({"role": "assistant", "content": acc})
            # Rerun to re-render full history with the new assistant message.
            st.rerun()
        except Exception as e:
            st.error(f"❌ LLM Error: {e}")
