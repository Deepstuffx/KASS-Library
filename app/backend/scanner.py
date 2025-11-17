import hashlib
import json
import os
import shutil
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .filename_parser import parse_filename
from . import db as dbmod
from .db import get_conn, init_db, upsert_sample
try:
    from .dsp import extract_audio_metadata
except Exception:
    extract_audio_metadata = None

# folder name used for loops classification
LOOPS_SUBPATH = "06 Loops & Grooves"
# folder name used for vocals classification
VOCALS_SUBPATH = "05 Vocals"
# folder name used for drums classification
DRUMS_SUBPATH = "01 Drums"
LOOP_MIN_SECONDS = 2.0

DEFAULT_EXTS = {".wav", ".aiff", ".aif", ".flac", ".ogg", ".mp3"}


def make_id(full_path: Path, size: int) -> str:
    m = hashlib.sha256()
    m.update(str(full_path).encode("utf-8"))
    m.update(b"|")
    m.update(str(size).encode("utf-8"))
    return m.hexdigest()


def valid_file(p: Path, exts: Optional[Iterable[str]] = None, min_size: int = 512) -> bool:
    if p.name.startswith('.'):
        return False
    try:
        if not p.is_file():
            return False
        size = p.stat().st_size
    except OSError:
        return False
    if size < min_size:
        return False
    if exts is not None:
        if p.suffix.lower() not in exts:
            return False
    return True


def iter_files(roots: List[Path], exts: Optional[Iterable[str]] = None) -> Iterable[Path]:
    exts_set = set(e.lower() for e in (exts or DEFAULT_EXTS))
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_dir():
                continue
            if p.suffix.lower() not in exts_set:
                continue
            yield p


def scan_roots(roots: List[str], db_path: Optional[str] = None, batch_size: int = 500, min_size: int = 512, exts: Optional[Iterable[str]] = None, job_id: Optional[str] = None, dry_run: bool = False, undo_csv: Optional[str] = None) -> Dict[str, int]:
    """Scan provided root paths, parse filenames, and upsert into DB.
    Returns summary dict.
    """
    roots_paths = [Path(r).resolve() for r in roots]
    conn = get_conn(db_path) if db_path else get_conn()
    init_db(conn)
    inserted = 0
    skipped = 0
    scanned = 0

    batch: List[dict] = []
    # collect planned or executed moves for optional undo logging
    moves: List[tuple] = []

    def move_if_needed(curr: Path, target_dir: Path) -> Path:
        """Move file to target_dir safely. If dry_run, record planned move and
        return original Path. Otherwise perform move, record it if undo_csv is
        requested, and return new Path for continued processing."""
        try:
            resolved = curr.resolve()
        except Exception:
            resolved = curr
        try:
            if target_dir.resolve() in resolved.parents:
                return curr
        except Exception:
            # fallback proceed
            pass
        os.makedirs(target_dir, exist_ok=True)
        dest = target_dir / curr.name
        if dest.exists():
            base = dest.stem
            suf = dest.suffix
            i = 1
            while True:
                candidate = target_dir / f"{base}_{i}{suf}"
                if not candidate.exists():
                    dest = candidate
                    break
                i += 1
        if dry_run:
            moves.append((str(curr), str(dest)))
            return curr
        try:
            shutil.move(str(curr), str(dest))
            moves.append((str(curr), str(dest)))
            return Path(dest)
        except Exception:
            return curr
    # check cancel flag every file by default for responsiveness
    cancel_check_interval = 1
    file_check_counter = 0
    canceled = False
    for p in iter_files(roots_paths, exts=exts):
        scanned += 1
        # if a job id was provided, check for cancellation requests frequently
        if job_id:
            # fast path: check in-process registry first for immediate visibility
            try:
                if getattr(dbmod, '_inproc_cancel_registry', {}).get(job_id) == 1:
                    canceled = True
                    break
            except Exception:
                pass
            try:
                if file_check_counter % cancel_check_interval == 0:
                    cur = conn.cursor()
                    cur.execute("SELECT cancel_requested FROM scan_jobs WHERE id=?", (job_id,))
                    r = cur.fetchone()
                    if r and r[0] == 1:
                        # cancellation requested
                        canceled = True
                        break
            except Exception:
                # ignore DB errors here and continue
                pass
            finally:
                file_check_counter += 1
        try:
            stat = p.stat()
            if stat.st_size < min_size:
                skipped += 1
                continue
        except OSError:
            skipped += 1
            continue

        # parse filename first to detect bpm hints
        parsed = parse_filename(p.name)

        # Prefer vocal classification first so vocal samples aren't swallowed by
        # loop/BPM detection. If a vocal keyword is detected, move the file
        # into the Vocals folder under the scanned root. Otherwise fall back
        # to the existing loop/BPM move logic.
        try:
            vocals_root = roots_paths[0] / VOCALS_SUBPATH if roots_paths else None
            name_l = p.name.lower()
            instrument = parsed.get("instrument") or ""
            tokens = parsed.get("tokens") or []
            # basic vocal keyword checks (filename, parsed instrument, or tokens)
            is_vocal_word = any(k in name_l for k in ("vocal", "vox", "voice", "singer", "vocalhit", "vocal_hit", "vocoder", "vocal_loop"))
            instrument_is_vocal = isinstance(instrument, str) and any(k in instrument.lower() for k in ("vocal", "vox", "voice"))
            tokens_is_vocal = any(isinstance(t, str) and any(k in t.lower() for k in ("vocal", "vox", "voice")) for t in tokens)
            is_vocal = is_vocal_word or instrument_is_vocal or tokens_is_vocal
            if vocals_root and is_vocal:
                try:
                    p = move_if_needed(p, vocals_root)
                    stat = p.stat()
                except Exception:
                    # noop on move failure — continue scanning original path
                    pass
            else:
                # drums-specific sorting: detect drum one-shots, fills, cymbals, toms, hats, snares
                try:
                    drums_root = roots_paths[0] / DRUMS_SUBPATH if roots_paths else None
                    is_drum_word = any(k in name_l for k in ("drum", "snare", "kick", "hat", "hihat", "hh", "tom", "fill", "fills", "cymbal", "crash", "ride", "shaker", "perc", "percussion", "one_shot", "one-shot"))
                    instrument_is_drum = isinstance(instrument, str) and any(k in instrument.lower() for k in ("drum", "snare", "kick", "hat", "tom", "perc", "percussion"))
                    tokens_is_drum = any(isinstance(t, str) and any(k in t.lower() for k in ("drum", "snare", "kick", "hat", "hihat", "tom", "fill", "cymbal", "crash", "ride", "shaker", "perc")) for t in tokens)
                    is_drum = is_drum_word or instrument_is_drum or tokens_is_drum
                    if drums_root and is_drum:
                        # choose a sensible subfolder name
                        subname = None
                        if any(k in name_l for k in ("kick", "bd", "bassdrum")) or (isinstance(instrument, str) and "kick" in instrument.lower()):
                            subname = "Kicks"
                        elif any(k in name_l for k in ("snare", "sn")) or (isinstance(instrument, str) and "snare" in instrument.lower()):
                            subname = "Snares"
                        elif any(k in name_l for k in ("hat", "hihat", "hh")):
                            subname = "Hats"
                        elif any(k in name_l for k in ("tom",)):
                            subname = "Toms"
                        elif any(k in name_l for k in ("fill", "fills", "drumfill")):
                            subname = "Fills"
                        elif any(k in name_l for k in ("cymbal", "crash", "ride", "splash", "china")):
                            subname = "Cymbals"
                        elif any(k in name_l for k in ("shaker", "perc", "percussion", "conga", "bongo")):
                            subname = "Percussion"
                        else:
                            subname = "One Shots"

                        try:
                            dest_root = drums_root / subname
                            p = move_if_needed(p, dest_root)
                            stat = p.stat()
                        except Exception:
                            pass
                except Exception:
                    pass
                # fallback to loop/BPM-based moves
                loops_root = roots_paths[0] / LOOPS_SUBPATH if roots_paths else None
                is_loop_word = "loop" in name_l
                has_bpm = parsed.get("bpm") is not None
                if loops_root and (is_loop_word or has_bpm):
                    # New OR rule:
                    # - If the filename explicitly contains 'loop' (is_loop_word),
                    #   move to Loops (unless it's a vocal).
                    # - Otherwise if there is a BPM hint (has_bpm), only move to
                    #   Loops when audio duration >= LOOP_MIN_SECONDS.
                    try:
                        if is_vocal:
                            # vocals always take precedence
                            pass
                        else:
                            if is_loop_word:
                                # name indicates loop: move regardless of duration
                                p = move_if_needed(p, loops_root)
                                stat = p.stat()
                            elif has_bpm:
                                # bpm hint only: require duration threshold
                                should_move_loop = True
                                if extract_audio_metadata is not None:
                                    try:
                                        meta = extract_audio_metadata(str(p))
                                        dur = None
                                        if isinstance(meta, dict):
                                            dur = meta.get('duration')
                                        if dur is not None:
                                            try:
                                                should_move_loop = float(dur) >= float(LOOP_MIN_SECONDS)
                                            except Exception:
                                                should_move_loop = True
                                        else:
                                            # duration not available -> fallback to move
                                            should_move_loop = True
                                    except Exception:
                                        # audio read failed -> fallback to move
                                        should_move_loop = True
                                if should_move_loop:
                                    p = move_if_needed(p, loops_root)
                                    stat = p.stat()
                    except Exception:
                        pass
        except Exception:
            pass

        sample_id = make_id(p.resolve(), stat.st_size)
        rel = str(p.resolve())
        sample = {
            "id": sample_id,
            "full_path": str(p.resolve()),
            "rel_path": rel,
            "root_dir": str(roots_paths[0]) if roots_paths else "",
            "filename": p.name,
            "ext": p.suffix.lower(),
            "size_bytes": stat.st_size,
            "bpm_hint": parsed.get("bpm"),
            "key_hint": parsed.get("key"),
            "instrument_hint": parsed.get("instrument"),
            "fuzzy_score": parsed.get("fuzzy_score"),
            "parsed_tokens": json.dumps(parsed.get("tokens")),
        }
        batch.append(sample)
        if len(batch) >= batch_size:
            with conn:
                for s in batch:
                    upsert_sample(conn, s)
            inserted += len(batch)
            batch = []
    # final batch
    if batch:
        with conn:
            for s in batch:
                upsert_sample(conn, s)
        inserted += len(batch)
    # if undo_csv requested and moves were executed (not dry-run), write undo log
    if undo_csv and moves and not dry_run:
        try:
            with open(undo_csv, 'w', newline='') as fh:
                w = csv.writer(fh)
                w.writerow(['src','dst'])
                for src, dst in moves:
                    w.writerow([src, dst])
        except Exception:
            pass
    # if canceled, include that in the summary
    if canceled:
        return {"scanned": scanned, "inserted": inserted, "skipped": skipped, "canceled": True}
    # include planned move count when dry_run
    summary = {"scanned": scanned, "inserted": inserted, "skipped": skipped}
    if dry_run:
        summary['planned_moves'] = len(moves)
        summary['planned_move_examples'] = moves[:50]
    try:
        conn.close()
    except Exception:
        pass
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs='+')
    parser.add_argument("--db", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Do not perform moves; just print planned moves")
    parser.add_argument("--undo-csv", default=None, help="Path to write undo CSV of performed moves when not a dry-run")
    args = parser.parse_args()
    print(scan_roots(args.roots, db_path=args.db, dry_run=args.dry_run, undo_csv=args.undo_csv))
