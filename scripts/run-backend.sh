#!/usr/bin/env bash
# Start the FastAPI backend using the best available venv
set -euo pipefail
ROOTDIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x "$ROOTDIR/.venv311/bin/python" ]; then
  PY="$ROOTDIR/.venv311/bin/python"
elif [ -x "$ROOTDIR/.venv/bin/python" ]; then
  PY="$ROOTDIR/.venv/bin/python"
else
  PY="python3"
fi

cd "$ROOTDIR/app/backend"
"$PY" -m uvicorn app.backend.main:app --reload --port 8000
