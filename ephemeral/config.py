import os
from typing import Optional

APP_VERSION = "1.8.1"

# Prefix used for synthetic context blocks injected into user messages.
# We use a flag (_synthetic) to identify these, not string matching.
CONTEXT_PREFIX = "Context:\n"

# TTL for session-scoped Tika parse cache (seconds)
TIKA_CACHE_TTL_S = 3600

# Token estimation behavior
TOKEN_HEURISTIC_CHARS_PER_TOKEN = 3.5
TOKEN_CACHE_MAX_ENTRIES = 256
TOKENIZE_TIMEOUT_S = 2.0  # keep UI snappy; budgeting degrades silently if tokenize is slow/unavailable

# Debug mode (shows technical status in sidebar, and error detail expanders)
DEBUG_MODE = os.getenv("EPHEMERAL_DEBUG", "0").strip().lower() in {"1", "true", "yes", "y", "on"}

# Feature toggle (operator-only)
ENABLE_TOKEN_BUDGETING = os.getenv("ENABLE_TOKEN_BUDGETING", "1").strip().lower() not in {"0", "false", "no"}

def _float_env(name: str, default: float) -> float:
    """Parse a float env var with safe fallback on missing/blank/invalid values."""
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _int_env_optional(name: str) -> Optional[int]:
    """Parse an optional int env var; return None for missing/blank/invalid/non-positive values."""
    raw = os.getenv(name)
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = int(raw)
        return value if value > 0 else None
    except Exception:
        return None


def _int_env(name: str, default: int) -> int:
    """Parse an int env var with safe fallback on missing/blank/invalid values."""
    value = _int_env_optional(name)
    return value if value is not None else default


def _bool_env(name: str, default: bool = False) -> bool:
    """Parse a bool env var with safe fallback on missing/blank/invalid values."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _optional_env(name: str) -> Optional[str]:
    """Return stripped env value, or None for unset/blank/whitespace-only."""
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "ephemeral-default")
TIKA_URL = os.getenv("TIKA_URL", "http://tika-server:9998")
LLM_SUPPORTS_VISION = _optional_env("LLM_SUPPORTS_VISION")

APP_DISPLAY_NAME = os.getenv("APP_DISPLAY_NAME", "EphemerAI")
APP_SUBTITLE = os.getenv("APP_SUBTITLE", "Private AI Assistant")
APP_WELCOME_SUBTITLE = os.getenv(
    "APP_WELCOME_SUBTITLE",
    "Your private workspace for focused, ephemeral conversations.",
)
APP_LOGO_PATH = os.getenv("APP_LOGO_PATH", "static/ephemeral_logo.png")
APP_EXPORT_TITLE = os.getenv("APP_EXPORT_TITLE", f"{APP_DISPLAY_NAME} Conversation")
SYSTEM_PROMPT_PATH = os.getenv("SYSTEM_PROMPT_PATH", "system_prompt_template.md")
MAX_UPLOAD_MB = _int_env("MAX_UPLOAD_MB", 50)
DEFAULT_UPLOAD_PROMPT = os.getenv("DEFAULT_UPLOAD_PROMPT", "Please analyze the uploaded files.")

TIKA_TIMEOUT_S = _int_env("TIKA_TIMEOUT_S", 15)
LLM_CONTEXT_TOKENS = _int_env_optional("LLM_CONTEXT_TOKENS")
LLM_OUTPUT_RESERVE_TOKENS = _int_env("LLM_OUTPUT_RESERVE_TOKENS", 32768)
LLM_REQUEST_TIMEOUT_S = _float_env("LLM_REQUEST_TIMEOUT_S", 1800.0)
LLM_MAX_RETRIES = _int_env("LLM_MAX_RETRIES", 0)
LLM_TEMPERATURE = _float_env("LLM_TEMPERATURE", 0.7)
LLM_TOP_P = _float_env("LLM_TOP_P", 0.8)
LLM_PRESENCE_PENALTY = _float_env("LLM_PRESENCE_PENALTY", 1.5)
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "none").strip() or "none"
LLM_THINKING_EFFORT = os.getenv("LLM_THINKING_EFFORT", "high").strip() or "high"
LLM_SHOW_REASONING = _bool_env("LLM_SHOW_REASONING", False)
LLM_MAX_TOKENS = _int_env_optional("LLM_MAX_TOKENS")
IMG_TOKEN_COST_DEFAULT = _int_env("IMG_TOKEN_COST_DEFAULT", 2048)


def _ollama_base_url() -> str:
    """
    Convert an OpenAI-style base URL like http://host:11434/v1 into the native Ollama base http://host:11434.
    If /v1 isn't present, returns the URL without trailing slash.
    """
    return LLM_BASE_URL.rstrip("/").split("/v1")[0]


def reasoning_effort_for_turn(thinking_mode_enabled: bool) -> str:
    """
    Return reasoning effort for the current turn.

    Thinking mode uses a separate operator-tunable effort value so deployments can
    adjust quality/latency tradeoffs without source edits.
    """
    return LLM_THINKING_EFFORT if thinking_mode_enabled else LLM_REASONING_EFFORT


def max_tokens_for_turn(thinking_mode_enabled: bool) -> Optional[int]:
    """
    Return max_tokens to send for the current turn.

    In thinking mode we omit max_tokens to avoid budget starvation where hidden
    reasoning consumes most of a small completion cap and truncates visible output.
    """
    if thinking_mode_enabled:
        return None
    return LLM_MAX_TOKENS
