import importlib.util


spec = importlib.util.spec_from_file_location("validate_compose_static", "scripts/validate_compose_static.py")
assert spec and spec.loader
vcs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcs)


def test_static_validator_passes_current_repo_contracts():
    ok, messages = vcs.validate()
    assert ok, "\n".join(messages)


def test_base_compose_is_cpu_safe_and_internal_api_only():
    base = vcs._parse_compose(vcs.BASE_COMPOSE)
    services = base["services"]
    ollama = services["ollama"]

    assert "deploy" not in ollama or not ollama["deploy"].get("resources", {}).get("reservations", {}).get("devices")
    assert "ports" not in ollama
    assert "11434" in [str(p) for p in ollama.get("expose", [])]


def test_api_compose_publishes_11434_with_loopback_default():
    api = vcs._parse_compose(vcs.API_COMPOSE)
    ports = api["services"]["ollama"]["ports"]
    joined = "\n".join(str(p) for p in ports)
    assert "11434:11434" in joined
    assert "${OLLAMA_API_BIND:-127.0.0.1}" in joined


def test_ollama_no_cloud_safe_default_detection():
    service = {"environment": ["OLLAMA_NO_CLOUD=${OLLAMA_NO_CLOUD:-1}"]}
    assert vcs._has_ollama_no_cloud_default_safe(service)
