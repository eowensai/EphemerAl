import base64
from html import escape as html_escape

import streamlit as st


def _normalize_id(raw_id: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in raw_id)


def _render_copy_iframe(
    *,
    button_id: str,
    plain_id: str,
    rich_id: str,
    button_markup: str,
    hover_css: str,
    button_css: str,
    active_css: str,
    copied_css: str,
    failed_css: str,
    extra_css: str,
    export_text_plain: str,
    export_html: str,
    success_label: str,
    success_flash_ms: int,
    failure_label: str,
    failure_flash_ms: int,
    restore_mode: str,
    height: int,
) -> None:
    safe_plain = html_escape(export_text_plain)

    iframe_html = f"""
        <meta charset=\"utf-8\" />
        <style>
          html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
          }}
          {extra_css}
          #{button_id} {{
            {button_css}
          }}
          #{button_id}:hover {{
            {hover_css}
          }}
          #{button_id}:active {{
            {active_css}
          }}
          #{button_id}.copied {{
            {copied_css}
          }}
          #{button_id}.failed {{
            {failed_css}
          }}
        </style>

        {button_markup}

        <textarea id=\"{plain_id}\"
                  style=\"position:absolute; left:-9999px; top:-9999px;\">{safe_plain}</textarea>

        <div id=\"{rich_id}\"
             contenteditable=\"true\"
             style=\"position:absolute; left:-9999px; top:-9999px; width:900px;\">
          {export_html}
        </div>

        <script>
          const btn = document.getElementById("{button_id}");
          const plain = document.getElementById("{plain_id}");
          const rich = document.getElementById("{rich_id}");
          const originalLabel = btn.textContent;
          const originalHtml = btn.innerHTML;

          function flash(stateClass, label, ms) {{
            btn.disabled = true;
            btn.classList.add(stateClass);
            btn.textContent = label;

            window.setTimeout(() => {{
              btn.disabled = false;
              btn.classList.remove(stateClass);
              if ("{restore_mode}" === "html") {{
                btn.innerHTML = originalHtml;
              }} else {{
                btn.textContent = originalLabel;
              }}
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

          function copyWithExecHtml() {{
            let copied = false;
            const onCopy = (event) => {{
              try {{
                event.preventDefault();
                event.clipboardData.setData("text/plain", plain.value);
                event.clipboardData.setData("text/html", rich.innerHTML);
                copied = true;
              }} catch (e) {{
                copied = false;
              }}
            }};

            document.addEventListener("copy", onCopy, {{ once: true }});
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(rich);
            selection.removeAllRanges();
            selection.addRange(range);
            rich.focus();

            try {{
              document.execCommand("copy");
            }} catch (e) {{
              copied = false;
            }}

            selection.removeAllRanges();
            return copied;
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

          async function copyWithClipboardApi() {{
            if (!navigator.clipboard || !window.ClipboardItem) {{
              return false;
            }}

            try {{
              const item = new ClipboardItem({{
                "text/plain": new Blob([plain.value], {{ type: "text/plain;charset=utf-8" }}),
                "text/html": new Blob([rich.innerHTML], {{ type: "text/html;charset=utf-8" }}),
              }});
              await navigator.clipboard.write([item]);
              return true;
            }} catch (e) {{
              return false;
            }}
          }}

          btn.addEventListener("click", async () => {{
            const modernOk = await copyWithClipboardApi();
            const eventOk = modernOk ? true : copyWithExecHtml();
            const richOk = eventOk ? true : copySelectionFrom(rich);
            const ok = richOk || copyPlain();

            if (ok) {{
              flash("copied", "{success_label}", {success_flash_ms});
            }} else {{
              flash("failed", "{failure_label}", {failure_flash_ms});
            }}
          }});
        </script>
        """
    iframe_src = "data:text/html;charset=utf-8;base64," + base64.b64encode(
        iframe_html.encode("utf-8")
    ).decode("ascii")
    st.iframe(iframe_src, height=height, width="stretch")


def render_copy_button(export_text_plain: str, export_html: str) -> None:
    """Sidebar-only copy button that tries rich HTML copy first, then plain text."""
    hover_tip = "Copy conversation to clipboard"
    button_id = "copy-btn"
    _render_copy_iframe(
        button_id=button_id,
        plain_id="copy-plain",
        rich_id="copy-rich",
        button_markup=(
            f'<button id="{button_id}" title="{html_escape(hover_tip)}">Copy Conversation</button>'
        ),
        hover_css="""
            border-color: #b6c3df;
            background: #f7f9fe;
        """,
        button_css="""
            width: 100%;
            box-sizing: border-box;
            background: #FFFFFF;
            color: #1d2a44;
            border: 1px solid #dce2ee;
            font-weight: 400;
            font-size: 0.95rem;
            font-family:
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI Variable",
                "Segoe UI",
                Roboto,
                sans-serif;
            padding: 0;
            margin: 0;
            min-height: 54px;
            transition: all .15s ease;
            box-shadow: none;
            border-radius: 14px;
            cursor: pointer;
            white-space: nowrap;
        """,
        active_css="""
            background: #eef0ff !important;
            border-color: #99a7ff !important;
        """,
        copied_css="""
            background: #4F5BEA !important;
            color: #FFFFFF !important;
            border-color: #4F5BEA !important;
        """,
        failed_css="""
            background: #B00020 !important;
            color: white !important;
            border-color: #B00020 !important;
        """,
        extra_css="",
        export_text_plain=export_text_plain,
        export_html=export_html,
        success_label="Copied",
        success_flash_ms=900,
        failure_label="Copy failed",
        failure_flash_ms=1500,
        restore_mode="text",
        height=58,
    )


def render_turn_copy_button(export_text_plain: str, export_html: str, button_id: str) -> None:
    """Inline per-turn copy button with rich-copy fallback sequence."""
    hover_tip = "Copy this message"
    normalized_button_id = _normalize_id(button_id)
    safe_button_id = html_escape(normalized_button_id, quote=True)
    safe_hover_tip = html_escape(hover_tip)

    copy_button_id = f"turn-copy-btn-{safe_button_id}"
    _render_copy_iframe(
        button_id=copy_button_id,
        plain_id=f"turn-copy-plain-{safe_button_id}",
        rich_id=f"turn-copy-rich-{safe_button_id}",
        button_markup=(
            '<div class="turn-copy">'
            f'<button id="{copy_button_id}" title="{safe_hover_tip}" aria-label="{safe_hover_tip}">'
            '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<rect x="9" y="9" width="11" height="11" rx="2"></rect>'
            '<rect x="4" y="4" width="11" height="11" rx="2"></rect>'
            '</svg>'
            '</button>'
            '</div>'
        ),
        hover_css="""
            border-color: #b6c3df;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(50, 68, 118, 0.14);
        """,
        button_css="""
            box-sizing: border-box;
            width: 2.05rem;
            height: 2.05rem;
            display: inline-grid;
            place-items: center;
            background: linear-gradient(180deg, #ffffff 0%, #f6f8ff 100%);
            color: #1d2a44;
            border: 1px solid #dce2ee;
            border-radius: 999px;
            cursor: pointer;
            transition: all .15s ease;
        """,
        active_css="""
            background: #eef0ff !important;
            border-color: #99a7ff !important;
            box-shadow: none !important;
        """,
        copied_css="""
            background: #4F5BEA !important;
            color: #FFFFFF !important;
            border-color: #4F5BEA !important;
        """,
        failed_css="""
            background: #B00020 !important;
            color: #FFFFFF !important;
            border-color: #B00020 !important;
        """,
        extra_css=f"""
          .turn-copy {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            width: 100%;
          }}
          #{copy_button_id} svg {{
            width: 0.95rem;
            height: 0.95rem;
            stroke: currentColor;
            fill: none;
            stroke-width: 1.8;
            stroke-linecap: round;
            stroke-linejoin: round;
          }}
        """,
        export_text_plain=export_text_plain,
        export_html=export_html,
        success_label="Copied",
        success_flash_ms=850,
        failure_label="Copy failed",
        failure_flash_ms=1500,
        restore_mode="html",
        height=38,
    )
