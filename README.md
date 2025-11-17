 ____  __.  _____    _________ _________ .____       _____ __________ 
|    |/ _| /  _  \  /   _____//   _____/ |    |     /  _  \\______   \
|      <  /  /_\  \ \_____  \ \_____  \  |    |    /  /_\  \|    |  _/
|    |  \/    |    \/        \/        \ |    |___/    |    \    |   \
|____|__ \____|__  /_______  /_______  / |_______ \____|__  /______  /
	\/       \/        \/        \/          \/       \/       \/ 

# KASS Lab - Ecosystem Overview

## KASS Library
Intelligent Audio Sample Sorting System (KASS)

KASS Library takes messy sample packs from any source and transforms them into a clean, structured, DAW-ready sample library folder.

All analysis, classification, DSP, ML, UI, and database logic exist only to generate that final export folder. The folder is the product.

---

## 1. Project Overview

KASS Library:
- Ingests large sample packs or directories
- Analyzes each sample (BPM, Key, Type, Loop/One-Shot, Spectral Info)
- Applies user-defined rules to determine placement
- Exports a polished, permanent sample library

The exported "KASS Library Folder" is intended to be your long-term, professionally organized sample database.

---

## 2. Primary Purpose

KASS Library is NOT:
- a DAW
- a sampler
- a Splice replacement

KASS Library IS:
- a preprocessing tool
- an organizational engine
- a rules-driven folder builder
- a sample librarian for producers

---

## 3. Features (Current & Planned)

### Current Capabilities
- Multi-pack scanning
- BPM + Key detection
- Loop vs One-Shot identification
- Instrument detection (kick, snare, perc, 808, etc.)
- FX classification
- Loudness & brightness analysis
- Rule-based export system (IF / THEN)
- Dry-run preview and undo
- SQLite internal metadata storage

### Planned Additions
- Splice folder auto-detection & ingestion
- KASS Folder Manager (templates + health checks)
- MAKID/Splice style GUI (waveform, table, filters, animations)
- Synth preset sorting (Serum, Massive, Vital, Diva, Sylenth)
- ML Similar Sound search and vibe tagging
- Export folder templates (EDM / Lo-Fi / Trap / Cinematic / Ableton)

---

## 4. Architecture Overview

```
[ FRONTEND (React UI) ]
- Table Browser
- Waveform Player
- Rule Builder
- Export Manager
	  |  (IPC)
[ TAURI (Rust Shell) ]
- Launches backend
- File dialogs
- OS permissions
	  |  (HTTP/IPC)
[ BACKEND (KASS Engine) ]
- Scanner & Parser
- DSP + ML Analysis
- Rule Engine
- Export Executor
- SQLite (internal)
	  |
[ FINAL EXPORT (KASS Folder) ]
- Clean DAW-ready folders
```

---

## 5. Project Structure

```
KASS-Lab/
|-- app/
|   |-- backend/     (KASS Engine: DSP, ML, Rules, Export)
|   |-- frontend/    (React UI)
|   |-- desktop/     (Tauri Shell)
|   |-- sandbox/     (Testing environment)
|   `-- scripts/     (Dev tools)
`-- docs/           (Architecture, Rules, API, Specs)
```

---

## 6. Database Purpose

The SQLite database is temporary and internal. It stores:
- Analysis results
- Classification metadata
- Rule evaluations
- Export plans
- Undo history

Users never interact with it directly. It is disposable.

---

## 7. KASS Sandbox Environment

Sandbox includes:
- Fake packs (clean + messy)
- Fake Splice folder
- Synth preset test libraries
- Benchmark scripts
- Regression tests

Used for:
- DSP accuracy
- Rule conflict testing
- Export validation
- Performance benchmarking

---

## 8. Development Roadmap (Summary)

0. Framework Setup  
1. Scanner + Parser  
2. DSP Analysis Pipeline  
3. Rule Engine + Export System  
4. GUI Alpha  
5. Splice Integration  
6. KASS Folder Manager  
7. Synth Preset Sorting  
8. ML Enhancements  
9. Polish + Release  

---

## 9. Technology Summary

- Backend: Python, FastAPI, Essentia, Librosa, Aubio, RapidFuzz
- Frontend: React, TailwindCSS, TanStack Table, Wavesurfer.js
- Desktop: Tauri (Rust)

---

## 10. Strategic Design Principles (Key Considerations Summary)

### Architecture
- Backend decoupled from UI
- DSP/ML precomputed, not real-time
- Multiprocessing for large packs

### UX
- Simple interface
- Automatic & advanced modes
- Dry-run + Undo required
- Clear rule priority

### Performance
- Downsampled waveforms
- Incremental scanning
- Skip BPM/key on tiny one-shots

### DSP/ML
- Confidence thresholds
- Embedding versioning
- ML optional

### Rules
- Human-readable IF/THEN
- Conflict detection
- Reorderable

### Export
- The folder IS the product
- Never overwrite silently
- Customizable templates

### Splice
- Auto-detect
- Incremental updates
- Duplicate-safe

### Synth Presets
- Modular parsers
- Unified export structure

---

End of file.
