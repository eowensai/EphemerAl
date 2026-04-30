from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ollama_model.sh"
ENV_FILE = ROOT / ".env"


def _run_dry_run() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_create_ollama_model_dry_run_without_env() -> None:
    original = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    try:
        ENV_FILE.unlink(missing_ok=True)
        result = _run_dry_run()
        assert result.returncode == 0, result.stderr
        assert "Dry run enabled. No commands will be executed." in result.stdout
    finally:
        if original is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original, encoding="utf-8")


def test_create_ollama_model_dry_run_accepts_env_example() -> None:
    original = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    try:
        shutil.copyfile(ROOT / ".env.example", ENV_FILE)
        result = _run_dry_run()
        assert result.returncode == 0, result.stderr
        assert "Dry run enabled. No commands will be executed." in result.stdout
    finally:
        if original is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original, encoding="utf-8")


def test_create_ollama_model_dry_run_accepts_profile_env() -> None:
    original = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    try:
        shutil.copyfile(ROOT / "examples/profiles/midrange-gpu.env", ENV_FILE)
        result = _run_dry_run()
        assert result.returncode == 0, result.stderr
        assert "Dry run enabled. No commands will be executed." in result.stdout
    finally:
        if original is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original, encoding="utf-8")
