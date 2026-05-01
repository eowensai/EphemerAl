#!/usr/bin/env python3
"""Interactive setup wizard for generating .env from profile templates."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Tuple

PROFILE_DIR = Path("examples/profiles")
PROFILE_MAP = {
    "low-end-laptop": "low-end-laptop.env",
    "midrange-gpu": "midrange-gpu.env",
    "high-vram-workstation": "high-vram-workstation.env",
}


def detect_platform() -> Dict[str, str | bool]:
    system = platform.system().lower()
    release = platform.release().lower()
    shell = os.environ.get("SHELL", "")
    term_program = os.environ.get("TERM_PROGRAM", "")
    in_wsl = "microsoft" in release or "wsl" in release or bool(os.environ.get("WSL_DISTRO_NAME"))
    in_powershell = "pwsh" in os.environ.get("0", "").lower() or "powershell" in shell.lower()

    return {
        "system": system,
        "release": release,
        "in_wsl": in_wsl,
        "in_powershell": in_powershell,
        "shell": shell or term_program or "unknown",
    }


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_probe(command: list[str]) -> Tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output.strip()


def detect_nvidia() -> Tuple[bool, str]:
    if command_exists("nvidia-smi"):
        ok, output = run_probe(["nvidia-smi", "-L"])
        if ok and output:
            return True, "Detected via nvidia-smi"
        return False, f"nvidia-smi unavailable or failed: {output or 'no output'}"

    ok, output = run_probe(["docker", "info", "--format", "{{json .Runtimes}}"])
    if ok and "nvidia" in output.lower():
        return True, "Detected NVIDIA runtime in Docker"

    return False, "No NVIDIA signal detected"


def parse_env_template(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def choose_default_profile(has_nvidia: bool, platform_info: Dict[str, str | bool]) -> str:
    if not has_nvidia:
        return "low-end-laptop"
    if platform_info.get("in_wsl") and has_nvidia:
        return "midrange-gpu"
    return "midrange-gpu"


def prompt_text(label: str, default: str, required: bool = False) -> str:
    while True:
        value = input(f"{label} [{default}]: ").strip()
        if not value:
            value = default
        if required and not value:
            print("Value is required.")
            continue
        return value


def prompt_yes_no(label: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{label} ({suffix}): ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def validate_positive_int(value: str, field: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field} must be a positive integer.")
    if not stripped.isdigit():
        raise ValueError(f"{field} must be numeric.")
    if int(stripped) <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return stripped


def validate_port(value: str, field: str = "App port") -> str:
    validated = validate_positive_int(value, field)
    if int(validated) > 65535:
        raise ValueError(f"{field} must be between 1 and 65535.")
    return validated


def backup_existing_env(env_path: Path) -> Path:
    stamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup_path = env_path.with_suffix(env_path.suffix + f".{stamp}.bak")
    shutil.copy2(env_path, backup_path)
    return backup_path


def write_env_file(path: Path, env_map: Dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in sorted(env_map.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EphemerAl setup wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Reserved for future automation")
    return parser


def main() -> int:
    build_parser().parse_args()
    print("== EphemerAl Setup Wizard ==")

    pinfo = detect_platform()
    docker_ok = command_exists("docker")
    compose_ok = docker_ok and (run_probe(["docker", "compose", "version"])[0] or command_exists("docker-compose"))
    nvidia_ok, nvidia_msg = detect_nvidia()

    print(f"Platform: {pinfo['system']} ({pinfo['release']})")
    print(f"WSL detected: {pinfo['in_wsl']}")
    print(f"PowerShell detected: {pinfo['in_powershell']}")
    print(f"Docker available: {docker_ok}")
    print(f"Docker Compose available: {compose_ok}")
    print(f"NVIDIA GPU signal: {nvidia_ok} ({nvidia_msg})")

    default_profile = choose_default_profile(nvidia_ok, pinfo)
    choices = ["low-end-laptop", "midrange-gpu", "high-vram-workstation", "custom/manual"]
    print("\nProfiles:")
    for index, name in enumerate(choices, start=1):
        marker = " (default)" if name == default_profile else ""
        print(f"  {index}. {name}{marker}")

    selected = input(f"Select profile [default {default_profile}]: ").strip()
    selected_profile = default_profile
    if selected:
        if selected.isdigit() and 1 <= int(selected) <= len(choices):
            selected_profile = choices[int(selected) - 1]
        elif selected in choices:
            selected_profile = selected

    env_values: Dict[str, str] = {}
    if selected_profile != "custom/manual":
        template_path = PROFILE_DIR / PROFILE_MAP[selected_profile]
        env_values = parse_env_template(template_path)
        print(f"Loaded profile template: {template_path}")
    else:
        print("Starting from empty values for custom/manual profile.")

    env_values["APP_DISPLAY_NAME"] = prompt_text("App display name", env_values.get("APP_DISPLAY_NAME", "EphemerAI"), required=True)
    env_values["APP_PORT"] = validate_port(prompt_text("App port", env_values.get("APP_PORT", "8501"), required=True), "App port")
    env_values["LLM_MODEL_NAME"] = prompt_text("Model alias name", env_values.get("LLM_MODEL_NAME", "ephemeral-default"), required=True)
    env_values["OLLAMA_MODEL_SOURCE"] = prompt_text("Model source tag", env_values.get("OLLAMA_MODEL_SOURCE", "qwen3:8b"), required=True)
    env_values["LLM_CONTEXT_TOKENS"] = validate_positive_int(prompt_text("Context size", env_values.get("LLM_CONTEXT_TOKENS", "32768"), required=True), "Context size")
    env_values["OLLAMA_NUM_CTX"] = env_values["LLM_CONTEXT_TOKENS"]

    no_cloud = prompt_yes_no("Keep Ollama cloud features disabled (OLLAMA_NO_CLOUD=1)?", default=True)
    if not no_cloud:
        print("PRIVACY WARNING: Disabling OLLAMA_NO_CLOUD may allow cloud-connected behavior.")
    env_values["OLLAMA_NO_CLOUD"] = "1" if no_cloud else "0"

    env_path = Path(".env")
    if env_path.exists():
        if not prompt_yes_no(".env already exists. Overwrite?", default=False):
            print("Aborted. Existing .env kept unchanged.")
            return 0
        backup = backup_existing_env(env_path)
        print(f"Backed up existing .env to: {backup}")

    write_env_file(env_path, env_values)
    print("Wrote .env successfully.")
    print("Note: default midrange profile uses qwen3:8b (text-only, not a vision model).")

    if prompt_yes_no("Run 'docker compose up -d --build'?", default=False):
        print("About to run: docker compose up -d --build")
        subprocess.run(["docker", "compose", "up", "-d", "--build"], check=False)
    if prompt_yes_no("Run 'bash scripts/create_ollama_model.sh'? (may download models)", default=False):
        print("About to run: bash scripts/create_ollama_model.sh")
        subprocess.run(["bash", "scripts/create_ollama_model.sh"], check=False)
    if prompt_yes_no("Run 'python scripts/doctor.py'?", default=True):
        print("About to run: python scripts/doctor.py")
        subprocess.run(["python", "scripts/doctor.py"], check=False)

    print("Setup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
