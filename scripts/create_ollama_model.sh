#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
elif [[ $# -gt 0 ]]; then
  echo "Error: Unsupported argument '$1'. Use --dry-run only." >&2
  exit 1
fi

read_dotenv_value() {
  local raw="$1"
  local value="${raw#"${raw%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  if [[ "${value}" =~ ^\"(.*)\"$ ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "${value}" =~ ^\'(.*)\'$ ]]; then
    printf '%s' "${BASH_REMATCH[1]}"
    return 0
  fi
  printf '%s' "${value}"
}

load_selected_dotenv() {
  local dotenv_path="$1"
  local -A allowed=(
    [OLLAMA_CONTAINER]=1
    [OLLAMA_MODEL_SOURCE]=1
    [LLM_MODEL_NAME]=1
    [OLLAMA_NUM_CTX]=1
    [OLLAMA_NUM_PREDICT]=1
    [OLLAMA_TEMPERATURE]=1
    [LLM_TEMPERATURE]=1
    [OLLAMA_TOP_P]=1
    [LLM_TOP_P]=1
    [OLLAMA_TOP_K]=1
    [OLLAMA_MIN_P]=1
    [OLLAMA_REPEAT_PENALTY]=1
    [OLLAMA_KV_CACHE_TYPE]=1
  )

  while IFS= read -r line || [[ -n "${line}" ]]; do
    local trimmed="${line#"${line%%[![:space:]]*}"}"
    if [[ -z "${trimmed}" || "${trimmed:0:1}" == "#" ]]; then
      continue
    fi
    if [[ ! "${trimmed}" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      continue
    fi
    local key="${BASH_REMATCH[1]}"
    local raw_value="${BASH_REMATCH[2]}"
    if [[ -z "${allowed[${key}]:-}" ]]; then
      continue
    fi
    local parsed
    parsed="$(read_dotenv_value "${raw_value}")"
    printf -v "${key}" '%s' "${parsed}"
    export "${key}"
  done < "${dotenv_path}"
}

if [[ -f "${REPO_ROOT}/.env" ]]; then
  load_selected_dotenv "${REPO_ROOT}/.env"
fi

OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-ollama}"
OLLAMA_MODEL_SOURCE="${OLLAMA_MODEL_SOURCE:-qwen3:8b}"
LLM_MODEL_NAME="${LLM_MODEL_NAME:-ephemeral-default}"
OLLAMA_NUM_CTX="${OLLAMA_NUM_CTX:-32768}"
OLLAMA_NUM_PREDICT="${OLLAMA_NUM_PREDICT:--1}"
OLLAMA_TEMPERATURE="${OLLAMA_TEMPERATURE:-${LLM_TEMPERATURE:-0.7}}"
OLLAMA_TOP_P="${OLLAMA_TOP_P:-${LLM_TOP_P:-0.8}}"
OLLAMA_TOP_K="${OLLAMA_TOP_K:-40}"
OLLAMA_MIN_P="${OLLAMA_MIN_P:-0}"
OLLAMA_REPEAT_PENALTY="${OLLAMA_REPEAT_PENALTY:-1.1}"

is_int() { [[ "$1" =~ ^-?[0-9]+$ ]]; }
is_decimal() { [[ "$1" =~ ^-?([0-9]+([.][0-9]+)?|[.][0-9]+)$ ]]; }

validate_values() {
  local errors=0
  if ! is_int "${OLLAMA_NUM_CTX}" || (( OLLAMA_NUM_CTX < 1 )); then
    echo "Error: OLLAMA_NUM_CTX must be a positive integer (got '${OLLAMA_NUM_CTX}')." >&2
    errors=1
  fi
  if ! is_int "${OLLAMA_NUM_PREDICT}"; then
    echo "Error: OLLAMA_NUM_PREDICT must be an integer (got '${OLLAMA_NUM_PREDICT}')." >&2
    errors=1
  fi
  if ! is_decimal "${OLLAMA_TEMPERATURE}"; then
    echo "Error: OLLAMA_TEMPERATURE must be numeric (got '${OLLAMA_TEMPERATURE}')." >&2
    errors=1
  fi
  if ! is_decimal "${OLLAMA_TOP_P}"; then
    echo "Error: OLLAMA_TOP_P must be numeric (got '${OLLAMA_TOP_P}')." >&2
    errors=1
  fi
  if ! is_int "${OLLAMA_TOP_K}" || (( OLLAMA_TOP_K < 0 )); then
    echo "Error: OLLAMA_TOP_K must be a non-negative integer (got '${OLLAMA_TOP_K}')." >&2
    errors=1
  fi
  if ! is_decimal "${OLLAMA_MIN_P}"; then
    echo "Error: OLLAMA_MIN_P must be numeric (got '${OLLAMA_MIN_P}')." >&2
    errors=1
  fi
  if ! is_decimal "${OLLAMA_REPEAT_PENALTY}"; then
    echo "Error: OLLAMA_REPEAT_PENALTY must be numeric (got '${OLLAMA_REPEAT_PENALTY}')." >&2
    errors=1
  fi
  if [[ -z "${OLLAMA_MODEL_SOURCE}" || -z "${LLM_MODEL_NAME}" ]]; then
    echo "Error: OLLAMA_MODEL_SOURCE and LLM_MODEL_NAME must not be empty." >&2
    errors=1
  fi
  if (( errors != 0 )); then
    exit 1
  fi
}

require_runtime() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is unavailable. Please install Docker and try again." >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker daemon is unavailable. Start Docker and try again." >&2
    exit 1
  fi
  if ! docker ps --format '{{.Names}}' | grep -Fxq "${OLLAMA_CONTAINER}"; then
    echo "Error: Ollama container '${OLLAMA_CONTAINER}' is not running. Start your Compose stack first." >&2
    exit 1
  fi
}

MODEFILE_HOST="$(mktemp -t Modelfile.ephemeral.XXXXXX)"
cleanup() {
  rm -f "${MODEFILE_HOST}"
  if [[ "${DRY_RUN}" == false ]]; then
    docker exec "${OLLAMA_CONTAINER}" rm -f /tmp/Modelfile.ephemeral >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

cat > "${MODEFILE_HOST}" <<EOF_MODEL
FROM ${OLLAMA_MODEL_SOURCE}

PARAMETER num_ctx ${OLLAMA_NUM_CTX}
PARAMETER num_predict ${OLLAMA_NUM_PREDICT}
PARAMETER temperature ${OLLAMA_TEMPERATURE}
PARAMETER top_p ${OLLAMA_TOP_P}
PARAMETER top_k ${OLLAMA_TOP_K}
PARAMETER min_p ${OLLAMA_MIN_P}
PARAMETER repeat_penalty ${OLLAMA_REPEAT_PENALTY}
EOF_MODEL

validate_values

if [[ "${DRY_RUN}" == true ]]; then
  echo "Dry run enabled. No commands will be executed."
  echo
  echo "Resolved settings:"
  echo "  OLLAMA_CONTAINER=${OLLAMA_CONTAINER}"
  echo "  OLLAMA_MODEL_SOURCE=${OLLAMA_MODEL_SOURCE}"
  echo "  LLM_MODEL_NAME=${LLM_MODEL_NAME}"
  echo "  OLLAMA_NUM_CTX=${OLLAMA_NUM_CTX}"
  echo "  OLLAMA_NUM_PREDICT=${OLLAMA_NUM_PREDICT}"
  echo "  OLLAMA_TEMPERATURE=${OLLAMA_TEMPERATURE}"
  echo "  OLLAMA_TOP_P=${OLLAMA_TOP_P}"
  echo "  OLLAMA_TOP_K=${OLLAMA_TOP_K}"
  echo "  OLLAMA_MIN_P=${OLLAMA_MIN_P}"
  echo "  OLLAMA_REPEAT_PENALTY=${OLLAMA_REPEAT_PENALTY}"
  echo
  echo "Generated Modelfile:"
  cat "${MODEFILE_HOST}"
  echo
  echo "Planned commands:"
  echo "  docker exec \"${OLLAMA_CONTAINER}\" ollama show \"${OLLAMA_MODEL_SOURCE}\" >/dev/null 2>&1 || docker exec \"${OLLAMA_CONTAINER}\" ollama pull \"${OLLAMA_MODEL_SOURCE}\""
  echo "  docker cp \"${MODEFILE_HOST}\" \"${OLLAMA_CONTAINER}\":/tmp/Modelfile.ephemeral"
  echo "  docker exec \"${OLLAMA_CONTAINER}\" ollama create \"${LLM_MODEL_NAME}\" -f /tmp/Modelfile.ephemeral"
  echo "  docker exec \"${OLLAMA_CONTAINER}\" rm -f /tmp/Modelfile.ephemeral"
  exit 0
fi

require_runtime

echo "Checking whether source model '${OLLAMA_MODEL_SOURCE}' is available in container '${OLLAMA_CONTAINER}'..."
if ! docker exec "${OLLAMA_CONTAINER}" ollama show "${OLLAMA_MODEL_SOURCE}" >/dev/null 2>&1; then
  echo "Source model not present. Pulling '${OLLAMA_MODEL_SOURCE}' now..."
  docker exec "${OLLAMA_CONTAINER}" ollama pull "${OLLAMA_MODEL_SOURCE}"
else
  echo "Source model already present."
fi

echo "Copying temporary Modelfile into container..."
docker cp "${MODEFILE_HOST}" "${OLLAMA_CONTAINER}":/tmp/Modelfile.ephemeral

echo "Creating or recreating alias '${LLM_MODEL_NAME}' from '${OLLAMA_MODEL_SOURCE}'..."
docker exec "${OLLAMA_CONTAINER}" ollama create "${LLM_MODEL_NAME}" -f /tmp/Modelfile.ephemeral

echo "Success: alias '${LLM_MODEL_NAME}' now points to '${OLLAMA_MODEL_SOURCE}' with your configured parameters."
