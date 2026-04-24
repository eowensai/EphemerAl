import os
import base64
import pathlib
import string
import uuid
import logging
from datetime import datetime, tzinfo
from html import escape as html_escape
from typing import Union, Tuple, List, Dict, Optional

import streamlit as st
import streamlit.components.v1 as components
import pytz
from ephemeral.config import (
    APP_VERSION,
    CONTEXT_PREFIX,
    DEBUG_MODE,
    ENABLE_TOKEN_BUDGETING,
    LLM_BASE_URL,
    LLM_CONTEXT_TOKENS,
    LLM_MAX_TOKENS,
    LLM_MODEL_NAME,
    LLM_OUTPUT_RESERVE_TOKENS,
    LLM_PRESENCE_PENALTY,
    LLM_REASONING_EFFORT,
    LLM_SHOW_REASONING,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    TIKA_URL,
)
from ephemeral.export import (
    _extract_export_info,
    _inline_md_to_html,
    _md_to_html_basic,
    build_conversation_html,
    build_conversation_markdown,
    build_message_text,
)
from ephemeral.stream_filter import ThinkStreamFilter, strip_think_blocks
from ephemeral.token_budget import _heuristic_token_estimate
from ephemeral.tika_client import parse_with_tika, tika_alive
from ephemeral.llm_client import (
    count_text_tokens,
    get_image_token_cost,
    get_llm_client,
    get_model_ctx,
    llm_alive,
    model_supports_images,
)

# EphemerAl main Streamlit application.
# - Provides an ephemeral chat UI for working with uploaded documents and images.
# - Talks to an LLM backend and an Apache Tika server over HTTP endpoints configured via environment variables.
# - Uses Streamlit's in-memory session_state only, this script does not write chat content or uploads to disk.

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="EphemerAl",
    layout="wide",
    initial_sidebar_state="auto",
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
DEFAULT_UPLOAD_PROMPT = os.getenv("DEFAULT_UPLOAD_PROMPT", "Please analyze the uploaded files.")


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
    # Default system template is model-agnostic and omits <|think|>.
    # Request defaults also set reasoning_effort to "none"; keep the think-block
    # filter as defense-in-depth even when reasoning visibility is toggled.
    SYSTEM_TMPL = string.Template(tmpl_path.read_text(encoding="utf-8"))
else:
    SYSTEM_TMPL = string.Template(
        "You are a helpful AI assistant. The current local time is ${current_time_local}. "
        "Answer concisely and accurately based on the context provided."
    )


# ── Chat message wrapper for CSS styling ──────────────────────────
def styled_chat_message(role: str, message_id: str = None):
    """Return a chat_message wrapped in a keyed container for CSS styling."""
    key = f"{role}-{message_id}" if message_id else f"{role}-{uuid.uuid4()}"
    return st.container(key=key).chat_message(role)


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
            color: #1E242B;
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

    if st.button("New Conversation", key="sidebar_new", use_container_width=True, help="Clears chat history and starts fresh"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.messages:
        export_md = build_conversation_markdown(st.session_state.messages)
        export_html = build_conversation_html(st.session_state.messages)
        render_copy_button(export_md, export_html)

    if DEBUG_MODE:
        with st.expander("System status", expanded=False):
            dbg_model_ctx = get_model_ctx()
            dbg_effective_ctx = dbg_model_ctx if dbg_model_ctx else 32768
            dbg_usable_ctx = int(dbg_effective_ctx * 0.95)
            dbg_reserved_ctx = min(LLM_OUTPUT_RESERVE_TOKENS, int(dbg_effective_ctx * 0.25))
            dbg_budget_ctx = max(4096, dbg_usable_ctx - dbg_reserved_ctx)
            st.caption(f"App version: {APP_VERSION}")
            st.caption(f"Model: {LLM_MODEL_NAME}")
            st.caption(f"LLM base URL: {LLM_BASE_URL}")
            st.caption(
                "Context budget: "
                f"{dbg_budget_ctx:,} tokens"
                + (f" (model ctx: {dbg_model_ctx:,})" if dbg_model_ctx else " (fallback model ctx: 32,768)")
            )
            st.caption(
                "Request settings: "
                f"temperature={LLM_TEMPERATURE}, top_p={LLM_TOP_P}, "
                f"presence_penalty={LLM_PRESENCE_PENALTY}, reasoning_effort={LLM_REASONING_EFFORT!r}"
            )
            st.caption(
                "LLM_MAX_TOKENS: "
                + (str(LLM_MAX_TOKENS) if LLM_MAX_TOKENS is not None else "not set (max_tokens omitted)")
            )

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

if prompt_in is not None:
    if st.session_state.show_welcome:
        st.session_state.show_welcome = False

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
    effective_ctx = model_ctx if model_ctx else 32768
    usable_ctx = int(effective_ctx * 0.95)
    reserved_ctx = min(LLM_OUTPUT_RESERVE_TOKENS, int(effective_ctx * 0.25))
    max_ctx = max(4096, usable_ctx - reserved_ctx)
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

    # If still too large even after dropping docs, remove the just-appended oversized
    # user turn so it doesn't poison subsequent requests, then respond as assistant and stop.
    if prompt_token_estimate > max_ctx:
        if st.session_state.messages:
            last_msg = st.session_state.messages[-1]
            if last_msg.get("role") == "user" and last_msg.get("id") == user_msg_id:
                st.session_state.messages.pop()

        assistant_msg_id = str(uuid.uuid4())
        error_text = (
            "That request is too large for this AI model right now, so I omitted that oversized request "
            "from conversation history to keep this session usable. "
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
                        mime = part.get("mime_type", "image/jpeg")
                        api_parts.append(
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
                        )

                elif ptype == "image_url":
                    if vision_supported:
                        api_parts.append(part)

            # Some backends/models are stricter about content arrays:
            # - If all parts are text, send a plain string.
            # - If no parts remain, send a text placeholder instead of an empty array.
            if not api_parts:
                messages_for_api.append({"role": msg["role"], "content": "(Attachment omitted.)"})
                continue

            if all(part.get("type") == "text" for part in api_parts):
                combined_text = "\n\n".join(part.get("text", "") for part in api_parts).strip()
                messages_for_api.append({"role": msg["role"], "content": combined_text or "(Attachment omitted.)"})
                continue

            messages_for_api.append({"role": msg["role"], "content": api_parts})
        else:
            messages_for_api.append({"role": msg["role"], "content": msg["content"]})

    payload = [{"role": "system", "content": sys_prompt}, *messages_for_api]

    assistant_msg_id = str(uuid.uuid4())

    with styled_chat_message("assistant", assistant_msg_id):
        with st.spinner("Generating…"):
            try:
                client = get_llm_client()
                request_kwargs = {
                    "model": LLM_MODEL_NAME,
                    "messages": payload,
                    "stream": True,
                    "temperature": LLM_TEMPERATURE,
                    "top_p": LLM_TOP_P,
                    "presence_penalty": LLM_PRESENCE_PENALTY,
                    "extra_body": {"reasoning_effort": LLM_REASONING_EFFORT},
                }
                if LLM_MAX_TOKENS is not None:
                    request_kwargs["max_tokens"] = LLM_MAX_TOKENS

                # Try include_usage if supported, fall back otherwise.
                try:
                    stream = client.chat.completions.create(
                        **request_kwargs,
                        stream_options={"include_usage": True},
                    )
                except TypeError:
                    stream = client.chat.completions.create(**request_kwargs)
                except Exception as e:
                    if "stream_options" in str(e) or "include_usage" in str(e):
                        stream = client.chat.completions.create(**request_kwargs)
                    else:
                        raise

                acc = ""
                box = st.empty()
                used_usage_from_backend = False
                stream_filter = ThinkStreamFilter()

                for chunk in stream:
                    if getattr(chunk, "choices", None):
                        delta_obj = getattr(chunk.choices[0], "delta", None)
                        delta = getattr(delta_obj, "content", None)
                        if not delta and LLM_SHOW_REASONING:
                            delta = getattr(delta_obj, "reasoning", None)
                        if delta:
                            acc += stream_filter.process_chunk(delta)
                            box.markdown(acc + "▌")

                    usage = getattr(chunk, "usage", None)
                    if usage and getattr(usage, "total_tokens", None) is not None:
                        st.session_state.last_token_count = int(usage.total_tokens)
                        used_usage_from_backend = True

                if stream_filter.in_think_block and DEBUG_MODE:
                    logging.debug("Unclosed think block detected at end of stream.")

                tail = stream_filter.finalize()
                if tail:
                    acc += tail
                elif stream_filter.in_think_block and DEBUG_MODE:
                    logging.debug(
                        "Discarding trailing stream buffer because stream ended inside a think block."
                    )

                acc = strip_think_blocks(acc)
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
                    if st.session_state.messages:
                        last_msg = st.session_state.messages[-1]
                        if last_msg.get("role") == "user" and last_msg.get("id") == user_msg_id:
                            st.session_state.messages.pop()
                    st.error(
                        "That message is too long for this AI model. "
                        "I omitted that oversized request from conversation history to keep this session usable. "
                        "Try removing a few attachments, shortening your message, or starting a new conversation."
                    )
                elif "connection" in lower or "timed out" in lower or "timeout" in lower:
                    st.error("I couldn't reach the AI service. Please try again in a moment.")
                else:
                    st.error("Something went wrong while talking to the AI service. Please try again.")

                if DEBUG_MODE:
                    with st.expander("Details for troubleshooting", expanded=False):
                        st.code(msg)
