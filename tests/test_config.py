import importlib

from ephemeral import config
import pytest


def test_float_env_valid_invalid_blank_missing(monkeypatch):
    monkeypatch.setenv("X_FLOAT", " 1.25 ")
    assert config._float_env("X_FLOAT", 9.0) == 1.25

    monkeypatch.setenv("X_FLOAT", "")
    assert config._float_env("X_FLOAT", 9.0) == 9.0

    monkeypatch.setenv("X_FLOAT", "abc")
    assert config._float_env("X_FLOAT", 9.0) == 9.0

    monkeypatch.delenv("X_FLOAT", raising=False)
    assert config._float_env("X_FLOAT", 9.0) == 9.0


def test_int_env_optional_cases(monkeypatch):
    monkeypatch.setenv("X_INT_OPT", " 42 ")
    assert config._int_env_optional("X_INT_OPT") == 42

    monkeypatch.setenv("X_INT_OPT", "0")
    assert config._int_env_optional("X_INT_OPT") is None

    monkeypatch.setenv("X_INT_OPT", "-5")
    assert config._int_env_optional("X_INT_OPT") is None

    monkeypatch.setenv("X_INT_OPT", "")
    assert config._int_env_optional("X_INT_OPT") is None

    monkeypatch.setenv("X_INT_OPT", "oops")
    assert config._int_env_optional("X_INT_OPT") is None

    monkeypatch.delenv("X_INT_OPT", raising=False)
    assert config._int_env_optional("X_INT_OPT") is None


def test_int_env_with_default(monkeypatch):
    monkeypatch.setenv("X_INT", "10")
    assert config._int_env("X_INT", 7) == 10

    monkeypatch.setenv("X_INT", "")
    assert config._int_env("X_INT", 7) == 7

    monkeypatch.setenv("X_INT", "bad")
    assert config._int_env("X_INT", 7) == 7


def test_bool_env_variants(monkeypatch):
    for raw in ["1", "true", "yes", "y", "on", "  YES  "]:
        monkeypatch.setenv("X_BOOL", raw)
        assert config._bool_env("X_BOOL", False) is True

    for raw in ["0", "false", "no", "n", "off", " Off "]:
        monkeypatch.setenv("X_BOOL", raw)
        assert config._bool_env("X_BOOL", True) is False

    monkeypatch.setenv("X_BOOL", "maybe")
    assert config._bool_env("X_BOOL", True) is True
    assert config._bool_env("X_BOOL", False) is False

    monkeypatch.delenv("X_BOOL", raising=False)
    assert config._bool_env("X_BOOL", True) is True


def test_ollama_base_url_variants(monkeypatch):
    monkeypatch.setattr(config, "LLM_BASE_URL", "http://ollama:11434/v1")
    assert config._ollama_base_url() == "http://ollama:11434"

    monkeypatch.setattr(config, "LLM_BASE_URL", "http://ollama:11434/v1/")
    assert config._ollama_base_url() == "http://ollama:11434"

    monkeypatch.setattr(config, "LLM_BASE_URL", "http://ollama:11434")
    assert config._ollama_base_url() == "http://ollama:11434"

    monkeypatch.setattr(config, "LLM_BASE_URL", "http://ollama:11434/")
    assert config._ollama_base_url() == "http://ollama:11434"


@pytest.mark.parametrize(
    ("thinking_mode_enabled", "expected_effort"),
    [
        (False, "none"),
        (True, "high"),
    ],
)
def test_reasoning_effort_for_turn(monkeypatch, thinking_mode_enabled, expected_effort):
    monkeypatch.setattr(config, "LLM_REASONING_EFFORT", "none")
    monkeypatch.setattr(config, "LLM_THINKING_EFFORT", "high")
    assert config.reasoning_effort_for_turn(thinking_mode_enabled) == expected_effort


@pytest.mark.parametrize(
    ("thinking_mode_enabled", "configured_max_tokens", "expected_max_tokens"),
    [
        (False, 2048, 2048),
        (False, None, None),
        (True, 2048, None),
        (True, None, None),
    ],
)
def test_max_tokens_for_turn(monkeypatch, thinking_mode_enabled, configured_max_tokens, expected_max_tokens):
    monkeypatch.setattr(config, "LLM_MAX_TOKENS", configured_max_tokens)
    assert config.max_tokens_for_turn(thinking_mode_enabled) == expected_max_tokens


def test_branding_and_prompt_defaults(monkeypatch):
    for key in [
        "APP_DISPLAY_NAME",
        "APP_SUBTITLE",
        "APP_WELCOME_SUBTITLE",
        "APP_LOGO_PATH",
        "APP_EXPORT_TITLE",
        "SYSTEM_PROMPT_PATH",
        "MAX_UPLOAD_MB",
        "DEFAULT_UPLOAD_PROMPT",
    ]:
        monkeypatch.delenv(key, raising=False)

    cfg = importlib.reload(config)

    assert cfg.APP_DISPLAY_NAME == "EphemerAI"
    assert cfg.APP_SUBTITLE == "Private AI Assistant"
    assert cfg.APP_WELCOME_SUBTITLE == "Your private workspace for focused, ephemeral conversations."
    assert cfg.APP_LOGO_PATH == "static/ephemeral_logo.png"
    assert cfg.APP_EXPORT_TITLE == "EphemerAI Conversation"
    assert cfg.SYSTEM_PROMPT_PATH == "system_prompt_template.md"
    assert cfg.MAX_UPLOAD_MB == 50
    assert cfg.DEFAULT_UPLOAD_PROMPT == "Please analyze the uploaded files."


def test_max_upload_mb_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0")
    cfg = importlib.reload(config)
    assert cfg.MAX_UPLOAD_MB == 50

    monkeypatch.setenv("MAX_UPLOAD_MB", "75")
    cfg = importlib.reload(config)
    assert cfg.MAX_UPLOAD_MB == 75

    monkeypatch.delenv("MAX_UPLOAD_MB", raising=False)
    importlib.reload(config)


def test_llm_supports_vision_blank_normalizes_to_none(monkeypatch):
    monkeypatch.setenv("LLM_SUPPORTS_VISION", "")
    cfg = importlib.reload(config)
    assert cfg.LLM_SUPPORTS_VISION is None

    monkeypatch.setenv("LLM_SUPPORTS_VISION", "   ")
    cfg = importlib.reload(config)
    assert cfg.LLM_SUPPORTS_VISION is None
