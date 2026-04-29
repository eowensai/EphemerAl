from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_logo_mime_type_map_supports_expected_extensions():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert '".png": "image/png"' in app_text
    assert '".jpg": "image/jpeg"' in app_text
    assert '".jpeg": "image/jpeg"' in app_text
    assert '".webp": "image/webp"' in app_text
    assert '".svg": "image/svg+xml"' in app_text


def test_logo_rendering_uses_display_name_alt_text_and_fallback_branding():
    app_text = (REPO_ROOT / "ephemeral_app.py").read_text(encoding="utf-8")
    assert 'alt="{APP_DISPLAY_NAME} logo"' in app_text
    assert '<div class="sidebar-brand-title">{APP_DISPLAY_NAME}</div>' in app_text
    assert '<div class="sidebar-brand-subtitle">{APP_SUBTITLE}</div>' in app_text
