from pathlib import Path
import sys

import pytest

import scripts.setup_wizard as setup_wizard
from scripts.setup_wizard import choose_default_profile, parse_env_template, validate_port, validate_positive_int


def test_parse_env_template_reads_key_values(tmp_path: Path) -> None:
    env_file = tmp_path / "sample.env"
    env_file.write_text("# comment\nA=1\nB = two\n\n", encoding="utf-8")

    parsed = parse_env_template(env_file)

    assert parsed == {"A": "1", "B": "two"}


def test_choose_default_profile_midrange_when_nvidia() -> None:
    assert choose_default_profile(True, {"in_wsl": False}) == "midrange-gpu"


def test_choose_default_profile_low_end_when_no_nvidia() -> None:
    assert choose_default_profile(False, {"in_wsl": False}) == "low-end-laptop"


def test_validate_positive_int_accepts_digits() -> None:
    assert validate_positive_int("8501", "App port") == "8501"


@pytest.mark.parametrize("value", ["", "abc", "85a", "0", "-1"])
def test_validate_positive_int_rejects_non_numeric(value: str) -> None:
    with pytest.raises(ValueError):
        validate_positive_int(value, "Context size")


@pytest.mark.parametrize("value", ["0", "65536", "abc"])
def test_validate_port_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        validate_port(value)


def test_validate_port_accepts_valid_port() -> None:
    assert validate_port("8501") == "8501"


def test_wizard_output_excludes_raw_api_flag_and_keeps_no_cloud_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples" / "profiles").mkdir(parents=True)
    (tmp_path / "examples" / "profiles" / "low-end-laptop.env").write_text("APP_DISPLAY_NAME=EphemerAI\n", encoding="utf-8")
    (tmp_path / "examples" / "profiles" / "midrange-gpu.env").write_text("APP_DISPLAY_NAME=EphemerAI\n", encoding="utf-8")
    (tmp_path / "examples" / "profiles" / "high-vram-workstation.env").write_text("APP_DISPLAY_NAME=EphemerAI\n", encoding="utf-8")
    monkeypatch.setattr(setup_wizard, "PROFILE_DIR", tmp_path / "examples" / "profiles")
    monkeypatch.setattr(setup_wizard, "detect_platform", lambda: {"system": "linux", "release": "test", "in_wsl": False, "in_powershell": False, "shell": "bash"})
    monkeypatch.setattr(setup_wizard, "command_exists", lambda _cmd: False)
    monkeypatch.setattr(setup_wizard, "detect_nvidia", lambda: (False, "none"))
    monkeypatch.setattr(setup_wizard.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(sys, "argv", ["setup_wizard.py"])

    answers = iter(["", "", "", "", "", "", "", "n", "n", "n"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert setup_wizard.main() == 0
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "EXPOSE_RAW_OLLAMA_API" not in env_text
    assert "OLLAMA_NO_CLOUD=1" in env_text


def test_wizard_existing_env_backup_behavior(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("APP_DISPLAY_NAME=OldName\n", encoding="utf-8")
    (tmp_path / "examples" / "profiles").mkdir(parents=True)
    for name in ("low-end-laptop.env", "midrange-gpu.env", "high-vram-workstation.env"):
        (tmp_path / "examples" / "profiles" / name).write_text("APP_DISPLAY_NAME=EphemerAI\n", encoding="utf-8")
    monkeypatch.setattr(setup_wizard, "PROFILE_DIR", tmp_path / "examples" / "profiles")
    monkeypatch.setattr(setup_wizard, "detect_platform", lambda: {"system": "linux", "release": "test", "in_wsl": False, "in_powershell": False, "shell": "bash"})
    monkeypatch.setattr(setup_wizard, "command_exists", lambda _cmd: False)
    monkeypatch.setattr(setup_wizard, "detect_nvidia", lambda: (False, "none"))
    monkeypatch.setattr(setup_wizard.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(sys, "argv", ["setup_wizard.py"])

    answers = iter(["", "", "", "", "", "", "", "y", "n", "n", "n"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert setup_wizard.main() == 0
    backups = list(tmp_path.glob(".env.*.bak"))
    assert backups, "Expected a backup file for pre-existing .env"
    assert backups[0].read_text(encoding="utf-8") == "APP_DISPLAY_NAME=OldName\n"
