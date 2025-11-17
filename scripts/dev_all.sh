#!/usr/bin/env zsh
set -euo pipefail

# Orchestrate backend + frontend + tauri desktop.
# 1. Start Python backend
# 2. Start Vite frontend
# 3. Launch Tauri pointing at dev server

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Activate venv if present
if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

# Start backend
./scripts/dev_backend.sh &
BACKEND_PID=$!

echo "[dev_all] Backend PID: $BACKEND_PID"

# Start frontend (pin to 5173 per vite.config)
cd app/frontend
npm run dev &
FRONTEND_PID=$!

echo "[dev_all] Frontend PID: $FRONTEND_PID"

# Wait for Vite to be reachable to avoid blank window in Tauri
for i in {1..60}; do
  if curl -sSf http://127.0.0.1:5173 >/dev/null 2>&1; then
    echo "[dev_all] Vite is up at http://127.0.0.1:5173"
    break
  fi
  sleep 0.5
done

# Launch Tauri desktop
cd ../desktop
# Ensure cargo/tauri available in PATH (rustup)
if [[ -f "$HOME/.cargo/env" ]]; then
  source "$HOME/.cargo/env"
fi
if ! command -v cargo >/dev/null 2>&1; then
  echo "[dev_all] cargo not found. Please install Rust via rustup: https://rustup.rs" >&2
  exit 1
fi
if ! command -v tauri >/dev/null 2>&1; then
  echo "[dev_all] tauri CLI not found. Installing locally (this may take a minute)..." >&2
  cargo install tauri-cli --version ^2 || {
    echo "[dev_all] Failed to install tauri-cli. Install manually: cargo install tauri-cli --version ^2" >&2
    exit 1
  }
fi

cargo tauri dev || {
  echo "[dev_all] Tauri exited unexpectedly" >&2
}

# Cleanup when Tauri exits
echo "[dev_all] Shutting down child processes..."
kill $FRONTEND_PID 2>/dev/null || true
kill $BACKEND_PID 2>/dev/null || true
