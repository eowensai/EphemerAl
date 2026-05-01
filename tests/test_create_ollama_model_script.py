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


def _with_temp_env(contents: str) -> subprocess.CompletedProcess[str]:
    original = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    try:
        ENV_FILE.write_text(contents, encoding="utf-8")
        return _run_dry_run()
    finally:
        if original is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original, encoding="utf-8")


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


def test_create_ollama_model_dry_run_accepts_all_profile_envs() -> None:
    profile_paths = [
        ROOT / "examples/profiles/midrange-gpu.env",
        ROOT / "examples/profiles/low-end-laptop.env",
        ROOT / "examples/profiles/high-vram-workstation.env",
    ]
    original = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    try:
        for profile_path in profile_paths:
            shutil.copyfile(profile_path, ENV_FILE)
            result = _run_dry_run()
            assert result.returncode == 0, f"{profile_path}: {result.stderr}"
            assert "Dry run enabled. No commands will be executed." in result.stdout
    finally:
        if original is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original, encoding="utf-8")


def test_create_ollama_model_dry_run_accepts_spaced_values_and_ignores_unknown_keys() -> None:
    result = _with_temp_env(
        "\n".join(
            [
                "# normal dotenv with spaces",
                "OLLAMA_CONTAINER=ollama",
                "OLLAMA_MODEL_SOURCE='qwen3:8b'",
                "LLM_MODEL_NAME=ephemeral-default",
                "OLLAMA_TEMPERATURE=0.7",
                "OLLAMA_TOP_P=0.8",
                "OLLAMA_TOP_K=40",
                "OLLAMA_MIN_P=0",
                "OLLAMA_REPEAT_PENALTY=1.1",
                "UNUSED_PUBLIC_TEXT=Upload files and chat locally with your documents.",
                "UNUSED_SHELL_CODE=$(echo should-not-run)",
                "",
            ]
        )
    )
    assert result.returncode == 0, result.stderr
    assert "Dry run enabled. No commands will be executed." in result.stdout
    assert "OLLAMA_MODEL_SOURCE=qwen3:8b" in result.stdout
    assert "UNUSED_PUBLIC_TEXT" not in result.stdout
    assert "should-not-run" not in result.stdout


def test_create_ollama_model_script_does_not_source_env() -> None:
    content = SCRIPT.read_text(encoding="utf-8")
    assert "source .env" not in content
    assert ". .env" not in content
