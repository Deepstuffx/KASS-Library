#!/usr/bin/env zsh
set -euo pipefail

# Activate venv if present
if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
fi

exec uvicorn app.backend.main:app --reload --port 8000