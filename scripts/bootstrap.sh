#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/bootstrap.sh [--dry-run] [--yes] [--help]

Bootstraps EphemerAl for Linux/macOS/WSL:
- checks prerequisites (Docker, Docker Compose, Python, Git)
- optionally runs setup wizard or creates .env from .env.example
- starts containers via docker compose
- creates/updates Ollama model alias
- runs doctor checks

Options:
  --dry-run   Show planned steps without changing anything.
  --yes       Non-interactive mode; auto-accept safe defaults.
  --help      Show this help.
USAGE
}

DRY_RUN=false
ASSUME_YES=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true ;;
    --yes) ASSUME_YES=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Error: Unknown argument '$1'. Use --help." >&2; exit 1 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
warn() { printf 'Warning: %s\n' "$*" >&2; }
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }
run_cmd() {
  if [[ "$DRY_RUN" == true ]]; then
    say "[dry-run] $*"
  else
    "$@"
  fi
}

confirm() {
  local prompt="$1"
  if [[ "$ASSUME_YES" == true ]]; then
    return 0
  fi
  read -r -p "$prompt [y/N]: " ans
  [[ "$ans" =~ ^[Yy]$ ]]
}

check_cmd() {
  local bin="$1" label="$2"
  if ! command -v "$bin" >/dev/null 2>&1; then
    if [[ "$DRY_RUN" == true ]]; then
      warn "$label is unavailable (dry-run continues)."
      return 1
    fi
    fail "$label is not installed or not on PATH."
  fi
}

say "EphemerAl bootstrap will do the following:"
say "  1) Validate local prerequisites"
say "  2) Prepare .env if missing"
say "  3) Run docker compose up -d --build"
say "  4) Run scripts/create_ollama_model.sh"
say "  5) Run python scripts/doctor.py"

DOCKER_READY=false
if check_cmd docker "Docker"; then
  if [[ "$DRY_RUN" == true ]]; then
    if docker info >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
      DOCKER_READY=true
      say "[dry-run] Docker CLI and Compose are available."
    else
      warn "Docker/Compose check would fail in a real run (dry-run continues)."
    fi
  else
    if ! docker info >/dev/null 2>&1; then
      fail "Docker is installed but not running. Start Docker and try again."
    fi
    if ! docker compose version >/dev/null 2>&1; then
      fail "Docker Compose (docker compose) is unavailable. Install/enable Compose v2."
    fi
    DOCKER_READY=true
  fi
fi
check_cmd git "Git" >/dev/null 2>&1 || true

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  warn "Python was not found. setup_wizard.py and doctor.py cannot run."
fi

if [[ "${OSTYPE:-}" == linux* ]] || grep -qi microsoft /proc/version 2>/dev/null; then
  if [[ -f .env ]] && grep -Eq '^\s*OLLAMA_KV_CACHE_TYPE\s*=\s*q8' .env; then
    if ! command -v nvidia-smi >/dev/null 2>&1 && ! command -v nvidia-ctk >/dev/null 2>&1; then
      warn "High-VRAM GPU profile detected (OLLAMA_KV_CACHE_TYPE=q8), but NVIDIA tooling was not found. GPU acceleration may fail."
    fi
  fi
fi

if [[ ! -f .env ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    say "[dry-run] Would prepare .env from defaults (.env.example or profile)."
  elif [[ "$ASSUME_YES" == true ]]; then
    [[ -f .env.example ]] || fail ".env.example was not found, cannot create .env."
    cp .env.example .env
    say "Created .env from .env.example using safe defaults. Please review and adjust .env for your environment."
  elif [[ -n "$PYTHON_BIN" ]] && confirm ".env is missing. Run guided setup wizard now?"; then
    run_cmd "$PYTHON_BIN" scripts/setup_wizard.py
  else
    [[ -f .env.example ]] || fail ".env.example was not found, cannot create .env."
    run_cmd cp .env.example .env
    say "Created .env from .env.example. Please review and adjust .env for your environment."
  fi
fi

if [[ "$DOCKER_READY" == true ]]; then
  run_cmd docker compose up -d --build
  run_cmd bash scripts/create_ollama_model.sh
elif [[ "$DRY_RUN" == true ]]; then
  say "[dry-run] Would run docker compose up -d --build."
  say "[dry-run] Would run scripts/create_ollama_model.sh."
else
  fail "Docker is required for non-dry-run bootstrap."
fi

if [[ -z "$PYTHON_BIN" ]]; then
  warn "Skipping doctor check because Python is unavailable."
else
  run_cmd "$PYTHON_BIN" scripts/doctor.py
fi

say "Bootstrap completed${DRY_RUN:+ (dry run)}."
