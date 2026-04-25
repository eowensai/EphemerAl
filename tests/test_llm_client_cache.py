import hashlib
from collections import OrderedDict
from types import SimpleNamespace


def _token_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def test_cache_eviction_is_partial_not_total():
    """Eviction should remove the oldest quarter, not clear the whole cache."""
    from ephemeral import llm_client

    cache = OrderedDict()
    max_entries = llm_client.TOKEN_CACHE_MAX_ENTRIES
    evict_count = max(1, max_entries // 4)

    for i in range(max_entries + 4):
        llm_client._cache_put(cache, str(i), i)

    assert len(cache) == max_entries + 4 - evict_count
    assert "0" not in cache
    assert str(max_entries + 3) in cache


def test_get_token_cache_migrates_plain_dict(monkeypatch):
    """_get_token_cache should upgrade a plain dict to OrderedDict."""
    from ephemeral import llm_client

    session = {"_token_count_cache": {"x": 10}}
    monkeypatch.setattr(llm_client, "st", SimpleNamespace(session_state=session))

    result = llm_client._get_token_cache()

    assert isinstance(result, OrderedDict)
    assert result["x"] == 10
    assert session["_token_count_cache"] is result


def test_count_text_tokens_cache_hit_promotes_entry(monkeypatch):
    """count_text_tokens should promote a cache hit to most-recently-used."""
    from ephemeral import llm_client

    key_a = _token_key("a")
    key_b = _token_key("b")
    session = {
        "_token_count_cache": OrderedDict([(key_a, 1), (key_b, 2)]),
        "tokenizer_available": False,
    }
    monkeypatch.setattr(llm_client, "st", SimpleNamespace(session_state=session))

    assert llm_client.count_text_tokens("a") == 1
    assert list(session["_token_count_cache"].keys()) == [key_b, key_a]


def test_unrecognized_tokenizer_payload_marks_tokenizer_unavailable(monkeypatch):
    """Unexpected tokenizer payloads should keep tokenizer_available=False."""
    from ephemeral import llm_client

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"unexpected": "shape"}

    session = {
        "_token_count_cache": OrderedDict(),
        "tokenizer_available": None,
    }
    monkeypatch.setattr(llm_client, "st", SimpleNamespace(session_state=session))
    monkeypatch.setattr(llm_client, "ENABLE_TOKEN_BUDGETING", True)
    monkeypatch.setattr(llm_client.requests, "post", lambda *args, **kwargs: FakeResponse())

    expected = llm_client._heuristic_token_estimate("hello")
    assert llm_client.count_text_tokens("hello") == expected
    assert session["tokenizer_available"] is False
