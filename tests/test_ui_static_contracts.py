from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_requirements_pin_streamlit_156():
    requirements_text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit==1.56.0" in requirements_text


def test_theme_css_keeps_root_and_chat_role_selectors():
    css = (REPO_ROOT / "theme.css").read_text(encoding="utf-8")
    assert ":root {" in css
    assert '[class*="st-key-user-"]' in css
    assert '[class*="st-key-user_"]' in css
    assert '[class*="st-key-assistant-"]' in css
    assert '[class*="st-key-assistant_"]' in css


def test_theme_css_has_streamlit_156_chat_input_contract_selectors():
    css = (REPO_ROOT / "theme.css").read_text(encoding="utf-8")
    assert '[data-testid="stChatInput"]' in css
    assert '[data-testid="stChatInputTextArea"]' in css
    assert '[data-testid="stChatInputSubmitButton"]' in css


def test_theme_css_supports_sidebar_new_key_variants():
    css = (REPO_ROOT / "theme.css").read_text(encoding="utf-8")
    assert '[class*="st-key-sidebar_new"] .stButton > button' in css
    assert '[class*="st-key-sidebar-new"] .stButton > button' in css


def test_theme_css_keeps_compact_right_aligned_user_message_contract():
    css = (REPO_ROOT / "theme.css").read_text(encoding="utf-8")
    assert '[class*="st-key-user-"] [data-testid="stChatMessage"]' in css
    assert "margin-left: auto;" in css
    assert "width: fit-content;" in css


def test_theme_css_targets_chat_message_container_for_avatar_ordering():
    css = (REPO_ROOT / "theme.css").read_text(encoding="utf-8")
    assert '[class*="st-key-user-"] [data-testid="stChatMessage"],' in css
    assert '[class*="st-key-user-"] [data-testid="stChatMessage"] > div' not in css
    assert 'flex-direction: row-reverse;' in css


def test_theme_css_has_no_external_font_or_cdn_imports():
    css = (REPO_ROOT / "theme.css").read_text(encoding="utf-8").lower()
    forbidden_patterns = [
        "@import url(",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "cdnjs.cloudflare.com",
        "cdn.jsdelivr.net",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in css


def test_streamlit_156_api_cleanup_contracts():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert "streamlit.components.v1" not in app_text
    assert "use_container_width=" not in app_text


def test_welcome_state_copy_contracts():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert "Attach files, not just prompts" in app_text
    assert "Local and session-only" in app_text
    assert "Verify important answers" in app_text
    assert "Images, PDFs, Office files, spreadsheets, text, and more." in app_text
    assert "No account or saved chat history in this app. New Chat clears messages and uploads." in app_text
    assert (
        "This local model has no live web access and may be wrong, especially on current facts." in app_text
    )


def test_new_chat_labels_and_placeholder_contracts():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert "Ask a question or attach files..." in app_text
    assert "New Chat" in app_text
    assert "🔄 New Chat" in app_text


def test_docker_service_name_defaults_are_preserved():
    config_text = (REPO_ROOT / "ephemeral/config.py").read_text(encoding="utf-8")
    assert 'LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")' in config_text
    assert 'TIKA_URL = os.getenv("TIKA_URL", "http://tika-server:9998")' in config_text


def test_ghost_doc_cleanup_uses_attachment_metadata_not_marker_text():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert 'part.get("_attachment", {}).get("kind") == "document"' in app_text
    assert 'part.get("_attachment", {}).get("name") in dropped_set' in app_text
    assert 'startswith("\U0001f4c4 *")' not in app_text


def test_sidebar_logo_loading_is_cached_with_mime_aware_data_uri():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert "@st.cache_data(show_spinner=False)" in app_text
    assert "def _load_logo_data(" in app_text
    assert "logo = _load_logo_data(APP_LOGO_PATH)" in app_text
    assert 'data:{logo.mime_type};base64,{logo.b64}' in app_text


def test_clipboard_module_is_used():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert "from ephemeral.clipboard import render_copy_button, render_turn_copy_button" in app_text
    assert "def render_copy_button(" not in app_text
    assert "def render_turn_copy_button(" not in app_text


def test_sidebar_state_uses_streamlit_156_pixel_width_contract():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert "initial_sidebar_state=304" in app_text
    assert "HTTP status code" not in app_text
    assert 'initial_sidebar_state="auto"' not in app_text
    assert "initial_sidebar_state='auto'" not in app_text


def test_vision_support_check_uses_current_files_and_history_guard():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert "def _message_has_image(" in app_text
    assert "has_image_files" in app_text
    assert "has_image_history" in app_text
    assert '_message_has_image(m.get("content"))' in app_text
    assert "has_image_files or has_image_history" in app_text
    assert "cached_vision" not in app_text


def test_text_only_mode_omits_image_parts_from_api_payload():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert 'elif ptype == "image":' in app_text
    assert 'elif ptype == "image_url":' in app_text
    assert "if vision_supported:" in app_text
    assert '{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}' in app_text
