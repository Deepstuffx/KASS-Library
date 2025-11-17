# GUI — Backend API Contract (Alpha)

This file maps UI actions and components to backend endpoints and payloads. Implement these endpoints in the FastAPI backend (or equivalent) for the frontend to call.

## Authentication / Session
- (Optional for alpha) local-only user mode — no auth required. For multi-user or cloud features, add standard token auth.

## Endpoints

### GET /roots
- Purpose: list known scan roots and counts
- Response:
  - roots: [{"path": "/Users/.../Samples", "count": 3422, "last_scanned": "..."}, ...]

### POST /roots
- Purpose: add a new scan root
- Body: {"path": "/absolute/path/to/folder"}
- Response: {"ok": true, "root": {...}}

### POST /scan/dryrun
- Purpose: run scanner in dry-run mode and return planned moves
- Body: {"roots": ["/abs/path"], "db_path": "...", "options": {"min_size": 512, "exts": [".wav", ".flac"]}}
- Response: {"scanned": 3422, "planned_moves": n, "moves_preview": [{"src": "...", "dst": "...", "reasons": ["rule: Loops", "autotag: loop"]}, ...]}

### POST /scan/apply
- Purpose: run scanner and apply moves (writes undo CSV)
- Body: same as dryrun plus {"undo_csv_path": "/abs/path/to/undo.csv"}
- Response: {"applied": true, "undo_csv": "/abs/path/to/undo.csv", "summary": {...}}

### GET /samples
- Purpose: paginated fetch of samples for a root
- Query params: root, page (int), page_size (int), sort_by, sort_desc, filters (JSON)
- Response: {"total": 5875, "page": 1, "page_size": 100, "samples": [{"id":"...","filename":"...","autotags":[{"tag":"vocal","confidence":0.95}],"bpm":120,"duration":2.5,...}, ...]}

### GET /samples/{id}
- Purpose: fetch single sample metadata
- Response: full sample record including autotags and DSP metadata

### GET /samples/{id}/waveform
- Purpose: serve a precomputed waveform JSON (downsampled peaks) or a URL to download raw audio for client-side rendering
- Response: {"peaks": [...], "duration": 2.5}

### POST /autotags/run
- Purpose: run autotag baseline (or model) across root or sample list
- Body: {"roots": [...], "apply": false}
- Response: {"total": 5875, "predictions_written": 0 (if apply false)}

### GET /autotags/{sample_id}
- Purpose: fetch autotags for the sample
- Response: [{"tag":"vocal","confidence":0.95}, ...]

### POST /rules
- Purpose: create or test a rule
- Body: {"rule": {"conditions": [...], "actions": [...]}, "test": true, "root": "/abs/path"}
- Response (if test): {"matches": 123, "examples": [{"id":"...","filename":"..."}, ...], "planned_moves": [...]}

### POST /export/apply
- Purpose: apply an export plan (list of moves), return undo CSV
- Body: {"moves": [{"src":"...","dst":"..."}, ...], "undo_csv": "/abs/path"}
- Response: {"applied": true, "undo_csv": "/abs/path"}

### GET /undo/{csv_path}
- Purpose: download the undo CSV or trigger a revert
- Response: file stream or operation result

## Websocket / Job updates
- Provide a websocket channel `/ws/jobs` that streams scan/dsp/export job progress updates and logs. Frontend subscribes for progress bars and live logs.

## Notes & Implementation Hints
- Use server-side pagination for `/samples` and return autotags nested to reduce roundtrips.
- For waveforms, precompute peaks on the backend (during DSP pass) and store as small JSON blobs to serve quickly.
- Dry-run operations should never modify files — they return planned moves and a compact preview of the effect.
- All apply endpoints should return the path to an undo CSV and write one atomically.


Acceptance
- Frontend can call these endpoints in the order: add root → scan/dryrun → view samples → open preview → run rule tests → export/apply → revert (if needed).
