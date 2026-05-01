from pathlib import Path

from scripts.doctor import (
    FAIL,
    PASS,
    WARN,
    _classify_ollama_ports,
    _is_no_cloud_default_safe,
    detect_context_mismatch,
    format_status,
    main,
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


def test_port_exposure_classification_safe_base() -> None:
    broad, loopback = _classify_ollama_ports({"expose": ["11434"]})
    assert broad is False
    assert loopback is False


def test_port_exposure_ignores_comments_and_non_ollama_ports() -> None:
    broad, loopback = _classify_ollama_ports({"ports": ["8501:8501"]})
    assert broad is False
    assert loopback is False


def test_port_exposure_loopback_opt_in() -> None:
    broad, loopback = _classify_ollama_ports({"ports": ["127.0.0.1:11434:11434"]})
    assert broad is False
    assert loopback is True


def test_port_exposure_broad_bindings() -> None:
    broad, loopback = _classify_ollama_ports({"ports": ["11434:11434", "0.0.0.0:11434:11434"]})
    assert broad is True
    assert loopback is False


def test_no_cloud_default_safe_patterns() -> None:
    assert _is_no_cloud_default_safe({"environment": ["OLLAMA_NO_CLOUD=${OLLAMA_NO_CLOUD:-1}"]}) is True
    assert _is_no_cloud_default_safe({"environment": {"OLLAMA_NO_CLOUD": "1"}}) is True
    assert _is_no_cloud_default_safe({"environment": {"OLLAMA_NO_CLOUD": "0"}}) is False


def test_main_uses_ephemeral_app_remediation_and_handles_no_docker(monkeypatch, capsys) -> None:
    monkeypatch.setattr("scripts.doctor.shutil.which", lambda _: None)
    rc = main()
    captured = capsys.readouterr().out
    assert rc == 0
    assert "docker compose up -d ephemeral-app" in captured
    assert "docker compose up -d app" not in captured
    assert "Docker-dependent checks will be skipped" in captured
    assert "NVIDIA GPU" in captured
