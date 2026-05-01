from pathlib import Path


def test_readme_public_default_and_text_only_contracts() -> None:
    text = Path('README.md').read_text(encoding='utf-8')
    assert 'qwen3:8b' in text
    assert 'text-only' in text


def test_readme_manual_order_has_compose_before_model_creation() -> None:
    text = Path('README.md').read_text(encoding='utf-8')
    compose_idx = text.find('docker compose up -d --build')
    create_idx = text.find('bash scripts/create_ollama_model.sh')
    assert compose_idx != -1 and create_idx != -1
    assert compose_idx < create_idx


def test_no_stale_readme_references() -> None:
    text = Path('README.md').read_text(encoding='utf-8')
    assert 'static/logo.svg' not in text
    assert ('Ephemeral ' + 'Screenshot.jpg') not in text
    assert 'EXPOSE_RAW_OLLAMA_API' not in text
