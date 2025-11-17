# GUI Alpha — Wireframes & Interaction Notes

This document contains quick wireframes, interaction notes, and acceptance criteria for the GUI Alpha (desktop app).

Overview
- Goal: Provide a compact, usable desktop interface to import → scan → review → rule → export.
- Primary screens: Library Browser (table), Preview Panel (waveform + player), Rule Builder modal, Export Preview (dry-run), Sidebar (navigation & roots), Folder Picker dialogs.

Legend
- [S] Sidebar
- [T] Table Browser (rows = samples)
- [P] Preview Panel (waveform + player + metadata)
- [R] Rule Builder (modal)
- [E] Export Preview panel (dry-run list with approve/reject controls)

Top-level layout (three-column responsive desktop):

+---------------------------------------------------------------+
| Header: App title | Import | Scan | Dry-Run | Export | User ... |
+---------------------------------------------------------------+
| [S] Sidebar  |                    [T] Table Browser           |
| (roots,     |  ------------------------------------------------ |
|  jobs,      |  | Row controls | Sample filename | col... |   |  |
|  shortcuts) |  ------------------------------------------------ |
|             |  |  (checkbox)   | 04_Clap___Snap.. | BPM..  |   |  |
|             |  |  (play)       | 15_BB_Snap.wav   | tag..  |   |  |
|             |  |  (wave preview)| ...              | ...    |   |  |
+-------------+--------------------------------------+ [P] Preview|
| Footer: status / quick undo / last action & job progress     |
+---------------------------------------------------------------+

Notes for each area

[S] Sidebar
- Shows scanned roots with counts, quick actions (Add Root, Import Splice Folder).
- Shows running jobs (scan/dsp) with progress bars and cancel buttons.
- Quick filters / saved searches.

[T] Table Browser
- Columns: checkbox, play preview, filename, tags (autotags), bpm, duration, instrument hint, root/subpath, actions (move, tag, open folder)
- Pagination / virtualization for performance (server-side page sizes default 100)
- Column sorting and basic filters (text, range for BPM/duration, tag filter)
- Multi-select operations: apply rule, move to folder, add tag, export selection
- Row context menu: Show in Finder/Explorer, Open containing folder, Copy path, Undo last move

[P] Preview Panel
- Waveform viewer (wavesurfer.js) showing zoom/region selection
- Play / Pause / Loop controls, volume, seek bar, time display
- Metadata: autotags, bpm (detected + hint), key, duration, sample rate, channels
- Buttons: Add tag, Flag, Send to Rule Builder (pre-fill rule)

[R] Rule Builder Modal
- Rule editor with editable conditions and actions.
- Condition builder: field (filename, autotag, bpm, duration, tokens), operator (contains, equals, gt, lt, regex), value
- Action builder: move to folder (choose target), add tag, set priority, mark as manual-exempt
- Rule preview: shows sample match count (run against sample set) and example matches (first 20)
- Save / Test / Apply buttons. Test runs a dry-run and returns planned moves for review.

[E] Export Preview Panel (dry-run)
- Shows planned moves as list: Source → Destination, reason(s) (rule, autotag, bpm), confidence
- Inline controls: Approve/Reject per-row, bulk approve/reject, search, sort
- Apply button triggers backend apply endpoint and writes undo CSV. UI shows progress and link to undo CSV location.

Folder Picker Dialog
- Native OS folder selector invoked via Tauri. Presents chosen root, with optional checkboxes for subfolder templates.

Accessibility & Keyboard
- Table navigation: arrow keys, space for selection, Enter to open preview
- Shortcuts: Space to play/pause, R to open rule modal for selected sample, D to run dry-run for selection

Acceptance Criteria (MVP):
- User can add a folder root and run a scan job.
- The Table Browser presents scanned samples (paginated/virtualized) and supports sorting/filtering.
- Selecting a sample populates the Preview Panel and plays audio with waveform synced.
- User can open Rule Builder, create a rule, run test (dry-run) and see results in Export Preview.
- User can apply the export and receive an undo CSV to revert moves.

Wireframe variants
- Compact mode: hide sidebar, increase table columns density for small screens.
- Focus mode: hide table, large waveform + details for deep listening and tagging.

Implementation hints
- Lazy-load waveform component when a sample is selected to reduce initial bundle size.
- Implement server-side pagination and sample search to keep table responsive for large libraries.
- Use Web Workers for waveform downsampling if client-side rendering on large files is needed.

Design assets
- This initial doc is a living wireframe; convert to Figma or SVG for higher fidelity.


----

Change log
- v0.1: Initial wireframes and interaction notes (this file).
