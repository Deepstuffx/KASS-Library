## Kams Auto Sample Sorter

This repository contains a small utility and GUI to organize audio sample packs into a structured sample library.

Features
- Organize samples (WAV/AIFF/FLAC/MP3/OGG) into semantic folders (Drums, Bass, Synths, FX, Vocals, Loops, Presets, etc.)
- Filename-based advanced keyword classification plus optional audio-feature based heuristics (librosa)
- GUI with dry-run, tagging, recent folders, cache clearing
- CLI mode for batch imports
- Memory of processed files to speed up repeated runs, with cache clear

Quick start

1. Create and activate a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# For macOS: install ffmpeg for non-WAV files
# brew install ffmpeg
```

2. Run the GUI:

```bash
python -c "from organizer.gui import launch_gui; launch_gui()"
```

3. Or use the CLI for batch imports:

```bash
python -m organizer.cli <source-folder> <dest-library> --dry-run
```

Importing an external pack repository (e.g. KASS-Library)

There is a helper script at `tools/import_kass.py` that can perform a dry-run mapping of a cloned repository or clone it for you and then import files into the organizer destination. See `tools/import_kass.py --help`.

Notes
	- Classification updated: Breakbeats (Amen/Breakbeat) routed under `06 Loops & Grooves/Breakbeats/*`; Acapellas under `05 Vocals/Acapellas`.
	- Deep analysis can override filename-based destinations for detected Acapellas and Breakbeat Loops.

Reports

- Use `tools/analyze_repo.py` to generate mapping CSVs and JSON summaries for any source folder or Git repo. By default, reports are written under `reports/` with versioned filenames (e.g., `deep_sample_map_v4.csv`, `fast_sample_summary_v2.json`).
- Example (fast, filename-only):
  - python tools/analyze_repo.py --src "/path/to/packs" --dest "/path/to/library"
- Example (deep, audio features):
  - python tools/analyze_repo.py --src "/path/to/packs" --dest "/path/to/library" --deep
- You can still override output paths with `--out-csv` and `--out-json`.

- The GUI ships with a "Fast mode" flag to skip expensive audio analysis; audio-based classification is optional and requires `librosa` and `ffmpeg` for compressed formats.
- Processed-file caching is stored in `~/.sample_organizer_memory.json`. Use the GUI "Clear Cache" button to reset.

License

This project is provided as-is. When integrating third-party sample packs or code, respect the original licenses for those projects.
# Sample Library Organizer

This repository contains a small sample-organizer tool and a lightweight GUI.

Files added:
- `organizer/core.py` — core functionality (classification, hashing, DB, process).
- `organizer/gui.py` — Tkinter GUI to choose source/destination and run organizer.
- `organizer/cli.py` — small CLI wrapper to run programmatically.
- `app.py` — launcher for GUI.

Quick start (run GUI):

```bash
python3 app.py
```

Quick start (CLI):

```bash
python3 -m organizer.cli /path/to/packs /path/to/library --dry-run
```

Packaging as a native executable (example using pyinstaller):

```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
# then run the produced executable in dist/
```

Notes:
- The project uses only Python stdlib (Tkinter for GUI). No extra requirements needed.
- The tool keeps a state DB at `<dest>/.organizer_state.sqlite` to de-duplicate and resume runs.

If you want I can:
- Add size+mtime prefilter to avoid re-hashing unchanged files (speedup).
- Add unit tests and a small sample dataset for CI.
- Add a proper setup.py/entry-points for pip installation.
