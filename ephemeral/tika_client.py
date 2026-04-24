import hashlib
import time

import streamlit as st
import requests
from tika import parser

from ephemeral.config import TIKA_CACHE_TTL_S, TIKA_TIMEOUT_S, TIKA_URL


@st.cache_data(ttl=5, show_spinner=False)
def tika_alive() -> bool:
    """Lightweight health check for the Tika server."""
    try:
        base = TIKA_URL.rstrip("/")
        endpoints = (f"{base}/tika", f"{base}/version", base)
        for url in endpoints:
            r = requests.get(url, timeout=2)
            if r.ok:
                return True
        return False
    except Exception:
        return False


# ── Session-scoped Tika parsing cache ─────────────────────────────
def _get_tika_cache() -> dict:
    """Return the session-scoped Tika parse cache, creating if needed."""
    return st.session_state.setdefault("_tika_cache", {})


def parse_with_tika(data: bytes, filename: str) -> str:
    """
    Parse document bytes with Tika via TIKA_URL.
    Cached per-session by content hash (SHA-256) with TTL.
    """
    key = hashlib.sha256(data).hexdigest()
    cache = _get_tika_cache()
    now = time.time()

    expired = [k for k, (ts, _) in cache.items() if now - ts > TIKA_CACHE_TTL_S]
    for k in expired:
        del cache[k]

    if key in cache:
        return cache[key][1]

    with st.spinner(f"Reading {filename}…"):
        try:
            parsed = parser.from_buffer(
                data,
                serverEndpoint=TIKA_URL,
                requestOptions={"timeout": TIKA_TIMEOUT_S},
            )
        except TypeError:
            parsed = parser.from_buffer(data, serverEndpoint=TIKA_URL)

    text = (parsed.get("content") or "").strip()
    if text:
        cache[key] = (now, text)

    return text
