from ephemeral import llm_client


def _reset_cache():
    llm_client.model_supports_images.clear()


def test_unset_uses_auto_detect(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(llm_client, "LLM_SUPPORTS_VISION", None)
    monkeypatch.setattr(llm_client, "_ollama_show", lambda: {"capabilities": ["vision"]})
    assert llm_client.model_supports_images() is True


def test_blank_uses_auto_detect(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(llm_client, "LLM_SUPPORTS_VISION", "")
    monkeypatch.setattr(llm_client, "_ollama_show", lambda: {"capabilities": ["vision"]})
    assert llm_client.model_supports_images() is True


def test_whitespace_only_uses_auto_detect(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(llm_client, "LLM_SUPPORTS_VISION", "   ")
    monkeypatch.setattr(llm_client, "_ollama_show", lambda: {"capabilities": ["vision"]})
    assert llm_client.model_supports_images() is True


def test_explicit_true_forces_vision(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(llm_client, "LLM_SUPPORTS_VISION", "true")
    monkeypatch.setattr(llm_client, "_ollama_show", lambda: None)
    assert llm_client.model_supports_images() is True


def test_explicit_false_forces_text_only(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(llm_client, "LLM_SUPPORTS_VISION", "false")
    monkeypatch.setattr(llm_client, "_ollama_show", lambda: {"capabilities": ["vision"]})
    assert llm_client.model_supports_images() is False
