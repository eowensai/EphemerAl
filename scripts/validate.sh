#!/usr/bin/env bash
set -euo pipefail

python -m pytest -q
pytest -q
python -m py_compile ephemeral_app.py ephemeral/*.py
ruff check .
python scripts/validate_compose_static.py

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose config
  docker compose -f docker-compose.yml config
  if [ -f docker-compose.gpu.yml ]; then
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml config
  fi
else
  echo "SKIPPED: Docker CLI or Docker Compose plugin unavailable in this environment."
fi
