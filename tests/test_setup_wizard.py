from pathlib import Path

import pytest

from scripts.setup_wizard import (
    choose_default_profile,
    parse_env_template,
    validate_positive_int,
)


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


@pytest.mark.parametrize("value", ["", "abc", "85a"])
def test_validate_positive_int_rejects_non_numeric(value: str) -> None:
    with pytest.raises(ValueError):
        validate_positive_int(value, "Context size")
