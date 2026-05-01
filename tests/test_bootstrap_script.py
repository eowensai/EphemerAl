import os
import stat
import subprocess
from pathlib import Path


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_exec(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR)


def _make_fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)

    source_bootstrap = Path("/workspace/EphemerAl/scripts/bootstrap.sh").read_text(encoding="utf-8")
    _write(scripts_dir / "bootstrap.sh", source_bootstrap)
    _make_exec(scripts_dir / "bootstrap.sh")

    _write(repo / ".env.example", "OLLAMA_NO_CLOUD=1\n")
    _write(scripts_dir / "setup_wizard.py", "raise SystemExit('wizard should not run in this test')\n")
    _write(scripts_dir / "doctor.py", "print('doctor-ok')\n")
    _write(scripts_dir / "create_ollama_model.sh", "#!/usr/bin/env bash\necho model-script\n")
    _make_exec(scripts_dir / "create_ollama_model.sh")
    return repo


def test_bootstrap_dry_run_without_docker_does_not_create_env(tmp_path: Path) -> None:
    repo = _make_fixture_repo(tmp_path)
    env = os.environ.copy()
    env["PATH"] = "/usr/bin:/bin"  # likely excludes docker in test env

    result = subprocess.run(
        ["bash", "scripts/bootstrap.sh", "--dry-run"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert not (repo / ".env").exists()
    assert "[dry-run]" in result.stdout


def test_bootstrap_yes_creates_env_without_wizard(tmp_path: Path) -> None:
    repo = _make_fixture_repo(tmp_path)
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    docker = fakebin / "docker"
    docker.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"info\" ]]; then exit 0; fi\n"
        "if [[ \"$1\" == \"compose\" && \"$2\" == \"version\" ]]; then exit 0; fi\n"
        "if [[ \"$1\" == \"compose\" ]]; then exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    _make_exec(docker)

    env = os.environ.copy()
    env["PATH"] = f"{fakebin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", "scripts/bootstrap.sh", "--yes"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    created_env = (repo / ".env").read_text(encoding="utf-8")
    assert "OLLAMA_NO_CLOUD=1" in created_env
    assert "Created .env from .env.example" in result.stdout
    assert "setup_wizard.py" not in result.stdout
