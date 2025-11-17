#!/usr/bin/env zsh
set -euo pipefail

# Rebuild frontend dist, bundle Tauri .app, and install to ~/Applications.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "[build_app] Root: $ROOT_DIR"

FRONTEND_DIR="$ROOT_DIR/app/frontend"
DESKTOP_DIR="$ROOT_DIR/app/desktop"
APP_NAME="KASS Lab.app"
APP_SRC="$DESKTOP_DIR/target/release/bundle/macos/$APP_NAME"
APP_DST="$HOME/Applications/$APP_NAME"

echo "[build_app] Cleaning prior bundles/dist..."
rm -rf "$DESKTOP_DIR/target/release/bundle" || true
rm -rf "$FRONTEND_DIR/dist" || true

echo "[build_app] Building frontend..."
cd "$FRONTEND_DIR"
npm run build

echo "[build_app] Bundling Tauri app (.app)..."
cd "$DESKTOP_DIR"
cargo tauri build --bundles app

echo "[build_app] Installing to: $APP_DST"
mkdir -p "$HOME/Applications"
rm -rf "$APP_DST" || true
cp -R "$APP_SRC" "$HOME/Applications/"

echo "[build_app] Launching app..."
open -n "$APP_DST" || true

echo "[build_app] Done. If macOS blocks launch, try:"
echo "  xattr -dr com.apple.quarantine \"$APP_DST\" && open -n \"$APP_DST\""