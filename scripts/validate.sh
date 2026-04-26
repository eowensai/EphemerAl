#!/usr/bin/env bash
set -euo pipefail

python -m pytest -q
pytest -q
python -m py_compile ephemeral_app.py ephemeral/*.py
ruff check .
