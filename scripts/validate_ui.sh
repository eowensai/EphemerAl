#!/usr/bin/env bash
set -euo pipefail

bash scripts/validate.sh
python scripts/ui_smoke.py
