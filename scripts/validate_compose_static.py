#!/usr/bin/env python3
"""Docker-free static validation for Compose policy and safety defaults."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
BASE_COMPOSE = ROOT / "docker-compose.yml"
API_COMPOSE = ROOT / "docker-compose.api.yml"
GPU_COMPOSE = ROOT / "docker-compose.gpu.yml"


def _parse_compose(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must parse to a mapping")
    return data


def _env_value(service: dict[str, Any], key: str) -> str | None:
    env = service.get("environment")
    if isinstance(env, list):
        for item in env:
            if isinstance(item, str) and item.startswith(f"{key}="):
                return item.split("=", 1)[1]
    elif isinstance(env, dict):
        value = env.get(key)
        return None if value is None else str(value)
    return None


def _has_ollama_no_cloud_default_safe(service: dict[str, Any]) -> bool:
    val = _env_value(service, "OLLAMA_NO_CLOUD")
    if not val:
        return False
    compact = val.replace(" ", "")
    return compact == "1" or compact == "${OLLAMA_NO_CLOUD:-1}" or compact == "${OLLAMA_NO_CLOUD-1}"


def validate() -> tuple[bool, list[str]]:
    messages: list[str] = []
    failed = False

    parsed: dict[str, dict[str, Any]] = {}
    for required in [BASE_COMPOSE, API_COMPOSE]:
        if not required.exists():
            messages.append(f"FAIL: {required.name} exists")
            failed = True
            continue
        try:
            parsed[required.name] = _parse_compose(required)
            messages.append(f"PASS: {required.name} parses")
        except Exception as exc:
            messages.append(f"FAIL: {required.name} parses ({exc})")
            failed = True

    if GPU_COMPOSE.exists():
        try:
            parsed[GPU_COMPOSE.name] = _parse_compose(GPU_COMPOSE)
            messages.append(f"PASS: {GPU_COMPOSE.name} parses")
        except Exception as exc:
            messages.append(f"FAIL: {GPU_COMPOSE.name} parses ({exc})")
            failed = True
    else:
        messages.append(f"PASS: {GPU_COMPOSE.name} is optional and not present")

    base = parsed.get("docker-compose.yml", {})
    base_services = base.get("services", {}) if isinstance(base.get("services"), dict) else {}

    for svc in ["ephemeral-app", "ollama", "tika-server"]:
        ok = svc in base_services
        messages.append(f"{'PASS' if ok else 'FAIL'}: base compose defines service '{svc}'")
        failed |= not ok

    ollama = base_services.get("ollama", {}) if isinstance(base_services.get("ollama"), dict) else {}

    has_gpu_reservation = bool(
        ollama.get("deploy", {})
        .get("resources", {})
        .get("reservations", {})
        .get("devices")
    )
    ok = not has_gpu_reservation
    messages.append(f"{'PASS' if ok else 'FAIL'}: base compose does not require NVIDIA GPU reservation")
    failed |= not ok

    expose = ollama.get("expose", [])
    expose_list = expose if isinstance(expose, list) else []
    ok = any(str(p) == "11434" for p in expose_list)
    messages.append(f"{'PASS' if ok else 'FAIL'}: base ollama uses expose for 11434")
    failed |= not ok

    ports = ollama.get("ports")
    ok = not ports
    messages.append(f"{'PASS' if ok else 'FAIL'}: base ollama does not publish raw API port via ports")
    failed |= not ok

    ok = _has_ollama_no_cloud_default_safe(ollama)
    messages.append(f"{'PASS' if ok else 'FAIL'}: base ollama defaults OLLAMA_NO_CLOUD to 1")
    failed |= not ok

    api = parsed.get("docker-compose.api.yml", {})
    api_services = api.get("services", {}) if isinstance(api.get("services"), dict) else {}
    api_ollama = api_services.get("ollama", {}) if isinstance(api_services.get("ollama"), dict) else {}
    api_ports = api_ollama.get("ports") if isinstance(api_ollama.get("ports"), list) else []

    port_joined = "\n".join(str(p) for p in api_ports)
    has_11434 = bool(re.search(r"11434:11434", port_joined))
    ok = has_11434
    messages.append(f"{'PASS' if ok else 'FAIL'}: docker-compose.api.yml publishes ollama 11434")
    failed |= not ok

    bind_ok = "${OLLAMA_API_BIND:-127.0.0.1}" in port_joined
    messages.append(f"{'PASS' if bind_ok else 'FAIL'}: docker-compose.api.yml defaults OLLAMA_API_BIND to 127.0.0.1")
    failed |= not bind_ok

    if GPU_COMPOSE.exists() and GPU_COMPOSE.name in parsed:
        gpu = parsed[GPU_COMPOSE.name]
        gpu_services = gpu.get("services", {}) if isinstance(gpu.get("services"), dict) else {}
        gpu_ollama = gpu_services.get("ollama", {}) if isinstance(gpu_services.get("ollama"), dict) else {}
        devices = (
            gpu_ollama.get("deploy", {})
            .get("resources", {})
            .get("reservations", {})
            .get("devices", [])
        )
        has_nvidia = any(isinstance(d, dict) and d.get("driver") == "nvidia" for d in devices if isinstance(devices, list))
        messages.append(f"{'PASS' if has_nvidia else 'FAIL'}: gpu override contains NVIDIA GPU reservation")
        failed |= not has_nvidia

    return (not failed), messages


if __name__ == "__main__":
    ok, msgs = validate()
    for m in msgs:
        print(m)
    sys.exit(0 if ok else 1)
