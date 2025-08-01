import os, base64, pathlib, string
from datetime import datetime

import streamlit as st
import requests, pytz
from tika import parser
from openai import OpenAI

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="EphemerAl",                     # CUSTOMIZE: Change this to your app’s name
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css(path="theme.css"):
    p = pathlib.Path(path)
    if p.exists():
        st.markdown(f"<style>{p.read_text()}</style>", unsafe_allow_html=True)
load_css()

# ── Constants ─────────────────────────────────────────────────────
LLM_BASE_URL     = os.getenv("LLM_BASE_URL",   "http://ollama:11434/v1")
MODEL_NAME       = os.getenv("LLM_MODEL_NAME", "gemma3-12b-prod")  
                                              # CUSTOMIZE: If you want to use Gemma 3 27B, change '12b' to '27b'  
TIKA_URL         = os.getenv("TIKA_URL",       "http://tika-server:9998")

# ── Helpers ───────────────────────────────────────────────────────
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

# ── Timezone configuration ────────────────────────────────────────
# CUSTOMIZE - Set your local timezone here for LLM system prompt use. Replace "America/Los_Angeles" with your own if not in Pacific.
# You can find the correct string at https://data.iana.org/time-zones/data/zone.tab
# Eastern: "America/New_York"
# Central: "America/Chicago"
# Mountain: "America/Denver"

TIMEZONE = pytz.timezone("America/Los_Angeles")  # CUSTOMIZE: e.g. "Europe/Berlin", "Australia/Sydney", etc.

def timestamp_local():
    now = datetime.now(TIMEZONE)  # uses the TIMEZONE constant above
    fmt = "%-I:%M %p on %A, %B %-d, %Y"
    if os.name == "nt":
        # On Windows, use %#I and %#d instead of %-I and %-d
        fmt = fmt.replace("%-I", "%#I").replace("%-d", "%#d")
    return now.strftime(fmt)

# ── System prompt template ────────────────────────────────────────
# Load your external prompt template; this will throw an error if the file is missing
tmpl_path   = pathlib.Path(__file__).parent / "system_prompt_template.md"
SYSTEM_TMPL = string.Template(
    tmpl_path.read_text(encoding="utf-8")
)

# ── Session defaults ──────────────────────────────────────────────
st.session_state.setdefault("messages", [])
st.session_state.setdefault("show_welcome", True)

# ── Sidebar ───────────────────────────────────────────────────────
# Logo requirements: PNG, JPG/JPEG, GIF
with st.sidebar:
    st.image("static/ephemeral_logo.png", use_container_width=True)  # CUSTOMIZE: Use your own logo file
    if not llm_alive():
        st.error("⚠️ LLM backend offline")
    if not TIKA_OK:
        st.warning("⚠️ Document parsing offline")
    if st.button("New Conversation", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── Welcome banner ────────────────────────────────────────────────
if st.session_state.show_welcome:
    st.markdown(
        "<div class='welcome-text'>"
        "<span style='font-size:1.6em;font-weight:600;'>Welcome&nbsp;to</span> "
        "<span class='ephemer'>Ephemer</span><span class='al'>Al</span>"    # CUSTOMIZE name after 'Welcome to:' in conversation window. Default = two tone, all text can be in a single class to avoid.
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="right-align-block">
          I understand images and most document types. Attach one per message.<br>
          <div style="text-align:center;margin:0.7rem 0;font-size:7px;color:#6B5B95;letter-spacing:10px;">• • •</div>
          Conversations are erased when you refresh or hit “New Conversation.”<br>
          <div style="text-align:center;margin:0.7rem 0;font-size:7px;color:#6B5B95;letter-spacing:10px;">• • •</div>
          I try to be helpful, but sometimes I’m wrong. Please double‑check important answers!
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Chat history renderer ─────────────────────────────────────────
def last_user_text(parts):
    """Return last text part that is NOT the auto-generated Context blob."""
    txts = [p["text"] for p in parts
            if isinstance(p, dict) and p.get("type") == "text"]
    for t in reversed(txts):
        if not t.startswith("Context:"):
            return t
    return txts[-1] if txts else ""

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if isinstance(m["content"], str):
            st.markdown(m["content"])
        else:
            st.markdown(last_user_text(m["content"]))

# ── Chat input handling ───────────────────────────────────────────
prompt_in = st.chat_input("Ask me anything…", accept_file=True)
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
        data = f.getvalue()
        if f.type.startswith("image/"):
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{f.type};base64,"
                                       f"{base64.b64encode(data).decode()}"}
            })
        else:
            if not TIKA_OK:
                st.warning(f"📄 Parsing unavailable for {f.name}")
                continue
            with st.spinner(f"Parsing {f.name}…"):
                try:
                    txt = parser.from_buffer(
                        data, serverEndpoint=TIKA_URL).get("content", "").strip()
                    if txt:
                        doc_ctx.append(f"--- {f.name} ---\n{txt}")
                except Exception as e:
                    st.error(f"❌ {f.name}: {e}")

    if doc_ctx:
        parts.insert(0, {"type": "text", "text": "Context:\n" + "\n\n".join(doc_ctx)})
    parts.append({"type": "text", "text": user_text})
    content_for_llm = parts if len(parts) > 1 else user_text

    st.session_state.messages.append({"role": "user", "content": content_for_llm})

    # ── LLM call ──────────────────────────────────────────────────
    sys_prompt = SYSTEM_TMPL.safe_substitute(
        current_time_local=timestamp_local()
    )
    payload = [{"role": "system", "content": sys_prompt},
               *st.session_state.messages]

    with st.chat_message("assistant"), st.spinner("Thinking…"):
        try:
            client = OpenAI(base_url=LLM_BASE_URL, api_key="not-needed")
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
            st.session_state.messages.append(
                {"role": "assistant", "content": acc})
            st.rerun()
        except Exception as e:
            st.error(f"❌ LLM Error: {e}")
