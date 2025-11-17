# KASS Lab Workspace

This repo contains a multi-app setup:

- `app/backend` — FastAPI backend (Python)
- `app/frontend` — React + Vite + Tailwind (Node)
- `app/desktop` — Tauri desktop shell (Rust)
- `sandbox/` — test data and scripts
- `scripts/` — helper scripts

## Prereqs (macOS)

- Python 3.10+ (found)
- Node.js + npm (install via Homebrew)
- Rust toolchain (cargo, rustc) (install via Homebrew / rustup)
- Tauri CLI (after Node + Rust)

### Install Node & Rust

```zsh
brew install node
brew install rustup-init && rustup-init -y
# restart terminal to load cargo
cargo install create-tauri-app tauri-cli
```

## Backend

Install Python dependencies and run the API:

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/backend/requirements.txt
uvicorn app.backend.main:app --reload --port 8000
```

Open: http://127.0.0.1:8000/health

## Desktop (Tauri) Phase Zero

Tauri desktop scaffold lives in `app/desktop` and points to the Vite dev server during development.

Dev config (`tauri.conf.json`):
- `devPath`: `http://localhost:5173`
- `distDir`: `../frontend/dist`

Run all (backend + frontend + desktop) with one command:

```zsh
./scripts/dev_all.sh
```

Or manually:
```zsh
# Terminal 1 (backend)
./scripts/dev_backend.sh
# Terminal 2 (frontend)
cd app/frontend && npm run dev
# Terminal 3 (desktop)
cd app/desktop && cargo tauri dev
```

## Frontend (to be scaffolded)

After Node is installed:

```zsh
cd app/frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install @tanstack/react-table wavesurfer.js
npm run dev
```

Quick Tailwind setup:
- Add `content: ["./index.html", "./src/**/*.{ts,tsx}"]` to `tailwind.config.js`
- Add `@tailwind base; @tailwind components; @tailwind utilities;` to `src/index.css`

## Desktop (Tauri)

After Node + Rust + Tauri CLI:

```zsh
cd app/desktop
npm create tauri-app@latest .
# choose TypeScript, Vanilla or React as preferred
npm run tauri dev
```

## Sandbox

See `sandbox/README.md` for placeholder test pack layout.

## Notes on DSP libs

- `essentia` and `aubio` may require native builds. Preferred:

```zsh
# Option A: Homebrew system libs
brew install aubio
# Essentia often needs conda or manual build; consider using Librosa features first
```
