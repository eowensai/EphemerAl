import os, base64, pathlib
from datetime import datetime

import streamlit as st
import requests, pytz
from tika import parser
from openai import OpenAI

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="EphemerAl",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── Anti-caching meta tags (hint browsers not to cache this page) ─
st.markdown(
    """
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    """,
    unsafe_allow_html=True,
)

def load_css(path="theme.css"):
    css_path = pathlib.Path(path)
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
load_css()

try:
    from streamlit_browser_engine import device
    HAS_DEVICE_DETECTION = True
except ImportError:
    HAS_DEVICE_DETECTION = False
    device = None

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
MODEL_NAME   = os.getenv("LLM_MODEL_NAME", "gemma3-prod")
TIKA_URL     = os.getenv("TIKA_URL", "http://tika-server:9998")

def tika_alive():
    try:
        return requests.get(TIKA_URL, timeout=2).ok
    except Exception:
        return False
TIKA_OK = tika_alive()

def llm_alive():
    try:
        base = LLM_BASE_URL.split("/v1")[0]
        return requests.get(base + "/api/tags", timeout=2).ok
    except Exception:
        return False

TIMEZONE = pytz.timezone("America/Los_Angeles")
def timestamp_local():
    now = datetime.now(TIMEZONE)
    fmt = "%-I:%M %p on %A, %B %-d, %Y"
    if os.name == "nt":
        fmt = fmt.replace("%-I", "%#I").replace("%-d", "%#d")
    return now.strftime(fmt)

tmpl_path = pathlib.Path(__file__).parent / "system_prompt_template.md"
if tmpl_path.exists():
    import string
    SYSTEM_TMPL = string.Template(tmpl_path.read_text(encoding="utf-8"))
else:
    # Fallback system prompt if file is missing
    import string
    SYSTEM_TMPL = string.Template(
        "You are a helpful AI assistant. The current local time is ${current_time_local}. "
        "Answer concisely and accurately based on the context provided."
    )


# ── Cached Tika parsing ───────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Parsing document…")
def parse_with_tika(data: bytes, filename: str) -> str:
    """Parse document bytes with Tika. Results cached for 1 hour."""
    return parser.from_buffer(data, serverEndpoint=TIKA_URL).get("content", "").strip()


# ── Cached OpenAI client ──────────────────────────────────────────
@st.cache_resource
def get_llm_client():
    """Return a cached OpenAI client instance."""
    return OpenAI(base_url=LLM_BASE_URL, api_key="not-needed")


st.session_state.setdefault("messages", [])
st.session_state.setdefault("show_welcome", True)

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    try:
        logo_path = pathlib.Path("static/ephemeral_logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    except Exception:
        st.markdown("**EphemerAl**")

    if not llm_alive():
        st.error("⚠️ LLM backend offline")
    if not TIKA_OK:
        st.warning("⚠️ Document parsing offline")
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
def render_content(content):
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                if not part["text"].startswith("Context:"):
                    st.markdown(part["text"])
            elif part.get("type") == "image":
                try:
                    st.image(part["data"], width=180)
                except Exception:
                    st.error(f"Failed to display {part.get('filename','image')}")
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
    files     = prompt_in.files if hasattr(prompt_in, "files") else []

    with st.chat_message("user"):
        st.markdown(user_text)

    parts, doc_ctx = [], []
    for f in files:
        if f.type.startswith("image/"):
            if f.size > 50 * 1024 * 1024:
                st.warning(f"📷 {f.name} is {f.size/1e6:.1f} MB – may be slow to process")

            f.seek(0)
            img_bytes = f.getvalue()
            parts.append({"type": "text", "text": f"📷 *{f.name}*"})
            parts.append({
                "type": "image",
                "data": img_bytes,
                "mime_type": f.type,
                "filename": f.name,
            })
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

    if doc_ctx:
        parts.insert(0, {"type": "text", "text": "Context:\n" + "\n\n".join(doc_ctx)})
    parts.append({"type": "text", "text": user_text})
    content_for_llm = parts if len(parts) > 1 else user_text

    st.session_state.messages.append({"role": "user", "content": content_for_llm})

    # ── LLM payload ───────────────────────────────────────────────
    sys_prompt = SYSTEM_TMPL.safe_substitute(current_time_local=timestamp_local())

    messages_for_api = []
    for msg in st.session_state.messages:
        if isinstance(msg["content"], list):
            api_parts = []
            for part in msg["content"]:
                if part.get("type") == "text":
                    api_parts.append(part)
                elif part.get("type") == "image":
                    if "b64" not in part:
                        part["b64"] = base64.b64encode(part["data"]).decode()
                    api_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{part.get('mime_type','image/jpeg')};base64,{part['b64']}"
                        },
                    })
                elif part.get("type") == "image_url":
                    api_parts.append(part)
            messages_for_api.append({"role": msg["role"], "content": api_parts})
        else:
            messages_for_api.append(msg)

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
            st.rerun()
        except Exception as e:
            st.error(f"❌ LLM Error: {e}")
