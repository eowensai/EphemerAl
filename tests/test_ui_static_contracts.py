from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_requirements_pin_streamlit_156():
    requirements_text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit==1.56.0" in requirements_text


def test_theme_css_keeps_root_and_chat_role_selectors():
    css = (REPO_ROOT / "theme.css").read_text(encoding="utf-8")
    assert ":root {" in css
    assert '[class*="st-key-user-"]' in css
    assert '[class*="st-key-assistant-"]' in css


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


def test_docker_service_name_defaults_are_preserved():
    config_text = (REPO_ROOT / "ephemeral/config.py").read_text(encoding="utf-8")
    assert 'LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")' in config_text
    assert 'TIKA_URL = os.getenv("TIKA_URL", "http://tika-server:9998")' in config_text
