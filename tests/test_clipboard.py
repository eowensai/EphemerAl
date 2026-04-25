import base64
import re
from types import SimpleNamespace


def _decode_iframe_src(src: str) -> str:
    prefix = "data:text/html;charset=utf-8;base64,"
    assert src.startswith(prefix)
    return base64.b64decode(src[len(prefix):]).decode("utf-8")


def _capture_rendered_html(monkeypatch, render_call):
    from ephemeral import clipboard

    captured = {}

    def fake_iframe(src, **kwargs):
        captured["src"] = src
        captured["kwargs"] = kwargs

    monkeypatch.setattr(clipboard, "st", SimpleNamespace(iframe=fake_iframe))

    render_call(clipboard)

    assert captured["kwargs"]["width"] == "stretch"
    return _decode_iframe_src(captured["src"])


def _css_block(html: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{(?P<body>.*?)\}", html, flags=re.S)
    assert match, f"Missing CSS block for {selector}"
    return match.group("body")


def test_sidebar_copy_button_preserves_hover_style(monkeypatch):
    html = _capture_rendered_html(
        monkeypatch,
        lambda clipboard: clipboard.render_copy_button("plain text", "<p>rich html</p>"),
    )

    hover = _css_block(html, "#copy-btn:hover")

    assert "background: #f7f9fe" in hover
    assert "box-shadow: 0 2px 8px" not in hover
    assert "rgba(50, 68, 118, 0.14)" not in hover


def test_turn_copy_button_preserves_hover_style(monkeypatch):
    html = _capture_rendered_html(
        monkeypatch,
        lambda clipboard: clipboard.render_turn_copy_button("plain text", "<p>rich html</p>", "msg-1"),
    )

    hover = _css_block(html, "#turn-copy-btn-msg-1:hover")

    assert "background: #ffffff" in hover
    assert "box-shadow: 0 2px 8px rgba(50, 68, 118, 0.14)" in hover


def test_clipboard_cascade_is_present(monkeypatch):
    html = _capture_rendered_html(
        monkeypatch,
        lambda clipboard: clipboard.render_copy_button("plain text", "<p>rich html</p>"),
    )

    assert "navigator.clipboard" in html
    assert "ClipboardItem" in html
    assert 'document.execCommand("copy")' in html
    assert "event.clipboardData.setData" in html
    assert "copySelectionFrom" in html
    assert "copyPlain" in html


def test_legacy_streamlit_components_iframe_is_not_used():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    clipboard_text = (repo_root / "ephemeral" / "clipboard.py").read_text(encoding="utf-8")

    assert "st.iframe(" in clipboard_text
    assert "st.components.v1.iframe" not in clipboard_text
    assert "streamlit.components.v1" not in clipboard_text
