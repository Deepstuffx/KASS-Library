#!/usr/bin/env bash
# Helper script to run the scanner using the best available Python venv.
# Usage: ./scripts/scan.sh /path/to/dir --db app/backend/kass.db --dry-run

set -euo pipefail
ROOTDIR="$(cd "$(dirname "$0")/.." && pwd)"
# prefer .venv311 if present
if [ -x "$ROOTDIR/.venv311/bin/python" ]; then
  PY="$ROOTDIR/.venv311/bin/python"
elif [ -x "$ROOTDIR/.venv/bin/python" ]; then
  PY="$ROOTDIR/.venv/bin/python"
else
  PY="python3"
fi

"$PY" -m app.backend.scan_runner "$@"
