from pathlib import Path

from scripts.doctor import (
    FAIL,
    PASS,
    WARN,
    detect_context_mismatch,
    format_status,
    is_dangerous_bind,
    parse_bool,
    parse_env_file,
    redact_value,
)


def test_parse_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nA=1\nB='two words'\nC=\"three\"\nINVALID\n", encoding="utf-8")
    values = parse_env_file(env_file)
    assert values["A"] == "1"
    assert values["B"] == "two words"
    assert values["C"] == "three"
    assert "INVALID" not in values


def test_format_status() -> None:
    assert format_status(PASS).startswith("✅")
    assert format_status(WARN).startswith("⚠️")
    assert format_status(FAIL).startswith("❌")


def test_redact_value() -> None:
    assert redact_value("API_KEY", "abc123") == "<redacted>"
    assert redact_value("NORMAL", "short-value") == "short-value"
    assert redact_value("NORMAL", "a" * 64) == "<redacted>"


def test_context_mismatch_detection() -> None:
    assert detect_context_mismatch("8192", "8192") is None
    message = detect_context_mismatch("4096", "8192")
    assert message is not None and "mismatch" in message.lower()
    parse_err = detect_context_mismatch("not-int", "8192")
    assert parse_err is not None and "parse" in parse_err.lower()


def test_parse_bool() -> None:
    assert parse_bool("1") is True
    assert parse_bool("false") is False
    assert parse_bool("OFF") is False
    assert parse_bool("maybe") is None
    assert parse_bool(None) is None


def test_dangerous_bind_detection() -> None:
    assert is_dangerous_bind("0.0.0.0", "") is True
    assert is_dangerous_bind(None, "ports:\n  - '11434:11434'\n") is True
    assert is_dangerous_bind("127.0.0.1", "ports:\n  - '8501:8501'\n") is False
