````markdown
Developer quickstart

Recommended venvs
- `.venv311` — created with Homebrew Python 3.11. Use when you need `librosa` and compiled deps.
- `.venv` — original project venv (may be Python 3.14; some DSP deps may not build there).

Common commands

Run the backend (dev server):

```bash
./scripts/run-backend.sh
```

Run the scanner CLI:

```bash
./scripts/scan.sh /path/to/folder --db app/backend/kass.db
# or dry-run (does not alter your real DB)
./scripts/scan.sh /path/to/folder --dry-run
```

Reuse venv311 as default

If you want `librosa` available by default, recreate `.venv` using Python 3.11:

```bash
rm -rf .venv
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -r app/backend/requirements.txt
```

Troubleshooting
- If VS Code shows stale diagnostics in Problems, reload the window (Command Palette → Developer: Reload Window) or restart the Python/Pylance language server.
- Use `./scripts/run-backend.sh` to ensure uvicorn runs with the correct Python interpreter.

````