#!/usr/bin/env python3
"""Plain-language install/runtime health checks for EphemerAl."""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

SECRET_NAME_HINTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "key",
    "api_key",
    "private",
    "credential",
)


@dataclass
class CheckResult:
    status: str
    title: str
    detail: str
    remediation: str


def parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and ((value[0] == value[-1]) and value[0] in {'"', "'"}):
            value = value[1:-1]
        values[key] = value
    return values


def parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "y"}:
        return True
    if normalized in {"0", "false", "no", "off", "n"}:
        return False
    return None


def redact_value(key: str, value: str) -> str:
    if any(hint in key.lower() for hint in SECRET_NAME_HINTS):
        return "<redacted>"
    if len(value) > 32 and re.fullmatch(r"[A-Za-z0-9_\-\.]+", value):
        return "<redacted>"
    return value


def format_status(status: str) -> str:
    icon = {PASS: "✅", WARN: "⚠️", FAIL: "❌"}.get(status, "•")
    return f"{icon} {status}"


def detect_context_mismatch(llm_context_tokens: Optional[str], ollama_num_ctx: Optional[str]) -> Optional[str]:
    try:
        app_ctx = int(llm_context_tokens) if llm_context_tokens else None
        runtime_ctx = int(ollama_num_ctx) if ollama_num_ctx else None
    except ValueError:
        return "Could not parse LLM_CONTEXT_TOKENS or OLLAMA_NUM_CTX as integers."
    if app_ctx is None or runtime_ctx is None or app_ctx == runtime_ctx:
        return None
    return (
        f"Context mismatch: app budget LLM_CONTEXT_TOKENS={app_ctx}, runtime OLLAMA_NUM_CTX={runtime_ctx}. "
        "LLM_CONTEXT_TOKENS controls app-side budgeting, while OLLAMA_NUM_CTX (or Modelfile num_ctx) "
        "controls model runtime context length."
    )


def is_dangerous_bind(ollama_api_bind: Optional[str], compose_text: str) -> bool:
    bind = (ollama_api_bind or "").strip()
    if bind.startswith("0.0.0.0"):
        return True
    return bool(re.search(r"(^|\s|['\"])11434:11434($|\s|['\"])", compose_text, re.MULTILINE))


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def is_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def main() -> int:
    root = Path.cwd()
    env_values = parse_env_file(root / ".env")
    compose_text = (root / "docker-compose.yml").read_text(encoding="utf-8") if (root / "docker-compose.yml").exists() else ""
    env = {**env_values, **os.environ}

    checks: List[CheckResult] = []

    py_ok = sys.version_info >= (3, 10)
    required = ["ephemeral_app.py", "docker-compose.yml", "ephemeral/config.py"]
    missing = [p for p in required if not (root / p).exists()]
    checks.append(CheckResult(
        PASS if py_ok and not missing else FAIL,
        "Python and required files",
        f"Python {sys.version.split()[0]}; missing files: {', '.join(missing) if missing else 'none'}.",
        "Use Python 3.10+ and run from repository root.",
    ))

    llm_ctx = env.get("LLM_CONTEXT_TOKENS")
    app_port = parse_int(env.get("APP_PORT", "8501"))
    env_ok = app_port is not None
    checks.append(CheckResult(
        PASS if (root / ".env").exists() and env_ok else WARN,
        ".env presence and parseability",
        f".env {'found' if (root / '.env').exists() else 'not found'}; APP_PORT parse {'ok' if env_ok else 'failed'}.",
        "Create .env from an example profile and ensure APP_PORT is an integer.",
    ))

    docker_available = shutil.which("docker") is not None
    checks.append(CheckResult(PASS if docker_available else FAIL, "Docker availability", "docker command found." if docker_available else "docker command not found.", "Install Docker Engine/Desktop and ensure it is running."))

    rc, out, _ = run_cmd(["docker", "compose", "version"]) if docker_available else (127, "", "")
    compose_available = docker_available and rc == 0
    checks.append(CheckResult(PASS if compose_available else WARN, "Docker Compose availability", out.splitlines()[0] if out else "docker compose unavailable.", "Install/enable Docker Compose v2 plugin."))

    if compose_available:
        rc, out, err = run_cmd(["docker", "compose", "ps"])
        checks.append(CheckResult(PASS if rc == 0 else WARN, "docker compose ps status", out.splitlines()[0] if out else (err or "No output."), "Run `docker compose up -d` and recheck."))
    else:
        checks.append(CheckResult(WARN, "docker compose ps status", "Skipped because Docker Compose is unavailable.", "Install Docker Compose to inspect service status."))

    bind_addr = env.get("APP_BIND_ADDRESS", "127.0.0.1")
    port = app_port or 8501
    reachable = is_reachable("127.0.0.1" if bind_addr in {"0.0.0.0", "::"} else bind_addr, port)
    checks.append(CheckResult(PASS if reachable else WARN, "App container reachability", f"Checked {bind_addr}:{port}.", "Start app service (`docker compose up -d app`) and verify APP_BIND_ADDRESS/APP_PORT."))

    if compose_available:
        rc, out, _ = run_cmd(["docker", "compose", "ps", "--services", "--status", "running"])
        running = set(out.split()) if rc == 0 else set()
        tika_running = "tika-server" in running
        checks.append(CheckResult(PASS if tika_running else WARN, "Tika service status", "tika-server running." if tika_running else "tika-server not listed as running.", "Start tika-server service and confirm TIKA_URL points to it."))
        ollama_running = "ollama" in running
        checks.append(CheckResult(PASS if ollama_running else FAIL, "Ollama container status", "ollama running." if ollama_running else "ollama not listed as running.", "Start ollama service with `docker compose up -d ollama`."))
    else:
        checks.append(CheckResult(WARN, "Tika service status", "Skipped because Docker Compose is unavailable.", "Install Docker Compose or manually verify tika-server container."))
        checks.append(CheckResult(WARN, "Ollama container status", "Skipped because Docker Compose is unavailable.", "Install Docker Compose or manually verify ollama container."))
        ollama_running = False

    model_name = env.get("LLM_MODEL_NAME", "ephemeral-default")
    if ollama_running:
        rc, out, err = run_cmd(["docker", "exec", "ollama", "ollama", "list"])
        model_present = rc == 0 and any(line.split()[0] == model_name for line in out.splitlines()[1:] if line.split())
        checks.append(CheckResult(PASS if model_present else WARN, "Ollama model alias", f"Looking for model alias `{redact_value('LLM_MODEL_NAME', model_name)}`.", "Create/pull the model alias (see README create_ollama_model script)."))
        rc2, out2, err2 = run_cmd(["docker", "exec", "ollama", "ollama", "ps"])
        checks.append(CheckResult(PASS if rc2 == 0 else WARN, "Ollama runtime status", out2.splitlines()[0] if out2 else (err2 or "No output"), "If this fails, check container logs and Ollama installation."))
    else:
        checks.append(CheckResult(WARN, "Ollama model alias", "Skipped because ollama container is not running.", "Start ollama container, then run this doctor again."))
        checks.append(CheckResult(WARN, "Ollama runtime status", "Skipped because ollama container is not running.", "Start ollama container, then rerun checks."))

    mismatch = detect_context_mismatch(llm_ctx, env.get("OLLAMA_NUM_CTX"))
    checks.append(CheckResult(WARN if mismatch else PASS, "Context configuration alignment", mismatch or "No app/runtime context mismatch detected.", "Align LLM_CONTEXT_TOKENS with OLLAMA_NUM_CTX for predictable truncation behavior."))

    if ollama_running:
        rc, out, err = run_cmd(["docker", "exec", "ollama", "nvidia-smi"])
        checks.append(CheckResult(PASS if rc == 0 else WARN, out.splitlines()[0] if out else "GPU visibility", "NVIDIA tools unavailable inside ollama container." if rc != 0 else "GPU visible.", "If using GPU, install NVIDIA Container Toolkit and ensure the container has GPU access."))
    else:
        checks.append(CheckResult(WARN, "GPU visibility", "Skipped because ollama container is not running.", "Start ollama and run again, or ignore on CPU-only setups."))

    dangerous = is_dangerous_bind(env.get("OLLAMA_API_BIND"), compose_text)
    checks.append(CheckResult(WARN if dangerous else PASS, "Raw Ollama API exposure", "Potential broad exposure of port 11434 detected." if dangerous else "No broad Ollama API exposure detected.", "Avoid exposing raw Ollama publicly; keep it internal or front it with authenticated proxy."))

    no_cloud = parse_bool(env.get("OLLAMA_NO_CLOUD"))
    if no_cloud is False:
        status = WARN
        detail = "OLLAMA_NO_CLOUD is explicitly disabled."
    elif no_cloud is None and "OLLAMA_NO_CLOUD" not in env and "OLLAMA_NO_CLOUD=1" in compose_text:
        status = PASS
        detail = "OLLAMA_NO_CLOUD unset, compose default appears to enforce OLLAMA_NO_CLOUD=1."
    elif no_cloud is None:
        status = WARN
        detail = "OLLAMA_NO_CLOUD not set and compose default could not be confirmed."
    else:
        status = PASS
        detail = "OLLAMA_NO_CLOUD enabled."
    checks.append(CheckResult(status, "Ollama cloud privacy", detail, "Set OLLAMA_NO_CLOUD=1 unless you explicitly want cloud features."))

    print("EphemerAl Doctor — Installation & Runtime Health")
    print("=" * 54)
    for item in checks:
        print(f"{format_status(item.status)}  {item.title}")
        print(f"  What we found: {item.detail}")
        print(f"  How to fix: {item.remediation}")
    failed = any(c.status == FAIL for c in checks)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
