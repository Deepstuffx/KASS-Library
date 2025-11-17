#!/usr/bin/env python3
"""
Bucket loop files by BPM ranges and move them into subfolders under
`06 Loops & Grooves` in the sandbox. Supports dry-run and apply modes
and writes an undo CSV when applying.

Usage:
  python app/backend/tools/apply_bpm_buckets.py --root sandbox/OrganizedLibraryDemo [--dry-run] [--apply]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple, List


RANGES = [
    (None, 120, "Up To 120 BPM"),
    (120, 135, "120-135 BPM"),
    (135, 155, "135-155 BPM"),
    (156, 180, "156-180 BPM"),
    (181, None, "180+ BPM"),
]

LOOPS_SUBPATH = "06 Loops & Grooves"
EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".ogg"}


def extract_bpm_from_name(name: str) -> Optional[int]:
    """Try to extract BPM from filename using multiple heuristics.

    Returns integer BPM if found, otherwise None.
    """
    s = name
    # 1) explicit bpm token like 'bpm150' or 'bpm_150' or '150bpm'
    m = re.search(r"\b[bB][pP][mM]?[_-]?(\d{2,3})\b", s)
    if m:
        return int(m.group(1))

    m = re.search(r"\b(\d{2,3})[ _-]?[bB][pP][mM]\b", s)
    if m:
        return int(m.group(1))

    # 2) numbers surrounded by separators: _126_, -128-, 126_Am, 126bpm handled above
    m = re.search(r"(?:_|-|\b)(\d{2,3})(?:_|-|\b)", s)
    if m:
        # validate reasonable BPM
        val = int(m.group(1))
        if 20 <= val <= 300:
            return val

    return None


def bucket_label(bpm: Optional[int]) -> str:
    if bpm is None:
        return "Unsorted BPM"
    for lo, hi, label in RANGES:
        if lo is None and hi is not None:
            if bpm <= hi:
                return label
        elif lo is not None and hi is None:
            if bpm >= lo:
                return label
        else:
            if lo <= bpm <= hi:
                return label
    return "Unsorted BPM"


def find_loop_files(root: Path) -> List[Path]:
    loops_root = root / LOOPS_SUBPATH
    if not loops_root.exists():
        return []
    files: List[Path] = []
    for p in loops_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTENSIONS:
            files.append(p)
    return files


def run(root: Path, dry_run: bool = True, apply: bool = False) -> Tuple[int, int]:
    files = find_loop_files(root)
    moved = 0
    processed = 0
    undo_rows = []

    for f in files:
        processed += 1
        name = f.name
        bpm = extract_bpm_from_name(name)
        label = bucket_label(bpm)
        dest_dir = root / LOOPS_SUBPATH / label
        dest = dest_dir / name

        if dest.exists() and f.exists() and os.path.samefile(str(dest), str(f)):
            # already correct place
            continue

        if dry_run or not apply:
            print(f"[DRY] MOVE {f} -> {dest}")
            moved += 1
        else:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(str(f), str(dest))
            undo_rows.append((str(dest), str(f)))
            moved += 1

    if apply and undo_rows:
        undo_csv = root / "undo_bpm_bucket_moves.csv"
        with undo_csv.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["moved_to", "moved_from"])
            for row in undo_rows:
                w.writerow(row)
        print(f"Wrote undo log: {undo_csv}")

    print(f"Processed {processed} files; actions (dry/apply): {moved}")
    return processed, moved


def main():
    parser = argparse.ArgumentParser(description="Bucket loop files by BPM ranges")
    parser.add_argument("--root", default="sandbox/OrganizedLibraryDemo", help="root library path")
    parser.add_argument("--dry-run", action="store_true", help="perform dry-run only (default)")
    parser.add_argument("--apply", action="store_true", help="apply moves and write undo CSV")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"Root not found: {root}")
        return

    dry = args.dry_run or not args.apply
    processed, moved = run(root, dry_run=dry, apply=args.apply)


if __name__ == "__main__":
    main()
