from pathlib import Path


BOOTSTRAP_PS1 = Path('scripts/bootstrap.ps1')


def _script_text() -> str:
    return BOOTSTRAP_PS1.read_text(encoding='utf-8')


def test_ps1_defines_dryrun_and_yes_parameters() -> None:
    text = _script_text()
    assert '[switch]$DryRun' in text
    assert '[switch]$Yes' in text


def test_ps1_dry_run_has_planned_actions_path() -> None:
    text = _script_text()
    assert '[dry-run]' in text
    assert "Would run docker compose up -d --build." in text
    assert "Would run scripts/create_ollama_model.sh." in text


def test_ps1_dry_run_does_not_require_docker_installed() -> None:
    text = _script_text()
    assert "if (-not $dockerCmd)" in text
    assert "if ($DryRun) { Warn 'Docker is unavailable (dry-run continues).' }" in text


def test_ps1_yes_mode_skips_setup_wizard_and_uses_env_example_defaults() -> None:
    text = _script_text()
    yes_branch = "elseif ($Yes)"
    assert yes_branch in text
    # contract: -Yes path creates .env from defaults and does not invoke setup_wizard
    yes_block_start = text.index(yes_branch)
    wizard_ref = text.find('setup_wizard.py', yes_block_start, yes_block_start + 400)
    assert wizard_ref == -1
    assert "Copy-Item '.env.example' '.env'" in text


def test_ps1_keeps_raw_ollama_internal_by_default() -> None:
    text = _script_text()
    assert 'EXPOSE_RAW_OLLAMA_API' not in text
    assert 'docker-compose.api.yml' not in text


def test_ps1_mentions_safe_defaults_and_no_driver_installers() -> None:
    text = _script_text()
    assert '.env.example' in text
    forbidden = ['apt-get', 'yum', 'brew install', 'choco install', 'winget install', 'nvidia-driver']
    assert not any(token in text for token in forbidden)
