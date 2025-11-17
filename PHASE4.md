Phase 4 — Autotagging, UX & Release Candidate

Goal
- Add automated, high-confidence tagging (autotagging) to complement the filename parser and DSP metadata so the scanner can classify samples more accurately with minimal manual review.
- Deliver a small, usable UI for reviewing planned moves and editing tags before applying them.
- Produce a release-candidate build with CI tests and a user testing plan.

High-level acceptance criteria
- Autotagging produces per-file tag candidates with confidence scores and stores them in the DB.
- Scanner can run in dry-run mode and include autotag suggestions in planned moves output.
- Frontend shows a review UI that lists planned moves and allows applying/rejecting per-file decisions.
- Undo logs are written for all applied operations; rollback works using existing undo CSVs.
- CI runs unit tests for parsing, scanning dry-run, autotagging model inference (mocked), and DB upserts.

Phase 4 Roadmap (short)
1. Define goals & metrics (precision/recall targets) — owner: you/me (in-progress).
2. Scaffold `PHASE4.md` and tracked todos — done.
3. Prototype autotagging pipeline (model + small inference wrapper):
   - Implement a simple rule-based baseline that uses filename tokens + DSP metadata to generate tags and confidence scores.
   - Add unit tests and evaluate baseline on a small labeled set.
4. Add a DB table `autotags` to cache tag predictions and confidence.
5. Extend `scan_roots` dry-run output to include `autotags` for each planned move.
6. Add a frontend review UI (component `PlannedMovesReview`) and backend endpoints to fetch planned moves/dry-runs and accept/reject actions.
7. Run user-testing with a small set of samples and collect feedback.
8. Prepare release candidate: run full DSP pass, create artifacts, add CI checks, and build Tauri package.

Immediate next steps I will take if you confirm:
- Implement a baseline rule-based autotagging function under `app/backend/autotag.py` and add a DB cache table. Then run the tagderivation pass on `sandbox/OrganizedLibraryDemo` in dry-run and report summary counts.

Tell me to "start autotag prototype" to begin implementing the baseline and running a dry-run, or tell me which other Phase 4 task you want first.
