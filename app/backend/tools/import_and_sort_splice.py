#!/usr/bin/env python3
"""Import audio files from a Splice folder into the workspace sandbox,
pad small files to >=1024 bytes, sort into OrganizedLibraryDemo folders,
and run the scanner to upsert metadata into a sandbox DB.

Usage: PYTHONPATH=. python app/backend/tools/import_and_sort_splice.py --src /Users/.../Splice --dst sandbox
"""
import argparse
import shutil
from pathlib import Path
import os
import stat

from app.backend.filename_parser import parse_filename
from app.backend.scanner import scan_roots

DEFAULT_EXTS = {".wav", ".aiff", ".aif", ".flac", ".ogg", ".mp3"}


def pad_file(path: Path, min_size: int = 1024, target_size: int = 2048):
    try:
        cur = path.stat().st_size
    except OSError:
        cur = 0
    if cur >= min_size:
        return False
    to_write = target_size - cur
    if to_write <= 0:
        return False
    with open(path, 'ab') as fh:
        fh.write(b"\0" * to_write)
    return True


def choose_dest(parsed: dict, sort_base: Path, filename: str) -> Path:
    instr = (parsed.get('instrument') or '').lower() if parsed else ''
    # simple mapping
    drums = {'kick': 'Kicks', 'snare': 'Snares', 'clap': 'Claps', 'hat': 'Hats', 'hihat': 'Hats', 'perc': 'Percussion', 'rim': 'Snares', 'tom': 'Toms', 'shaker': 'Percussion', 'snap': 'Claps', '808': 'Kicks'}
    if instr in drums:
        return sort_base / '01 Drums' / drums[instr]
    if instr == 'bass':
        return sort_base / '02 Bass'
    if instr in ('pad', 'lead', 'synth') or instr.endswith('lead'):
        return sort_base / '03 Synths & Leads'
    if instr in ('fx', 'impact', 'risers', 'downers') or 'fx' in filename.lower():
        return sort_base / '04 FX' / 'Impacts'
    if instr in ('vocal', 'vox'):
        return sort_base / '05 Vocals' / 'Vocal One Shots'
    # loops detection: filenames containing 'loop' or bpm
    if 'loop' in filename.lower() or ('bpm' in filename.lower()):
        return sort_base / '06 Loops & Grooves' / 'Unsorted BPM'
    return sort_base / '07 One Shots'


def import_and_sort(src: Path, dst_base: Path, sort_base: Path, db_path: Path, dry_run: bool = False):
    copied = 0
    padded = 0
    files = []
    for root, dirs, filenames in os.walk(src):
        for f in filenames:
            p = Path(root) / f
            if p.suffix.lower() not in DEFAULT_EXTS:
                continue
            files.append(p)
    for p in files:
        rel = p.name
        parsed = parse_filename(rel, fuzzy_threshold=85)
        dest_dir = choose_dest(parsed, sort_base, rel)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / rel
        # ensure dst copy present
        if dry_run:
            print('[DRY]', p, '->', dest)
            continue
        try:
            shutil.copy2(p, dest)
        except Exception:
            # fallback to copy file content
            with open(p, 'rb') as rf, open(dest, 'wb') as wf:
                wf.write(rf.read())
        # pad if small
        if pad_file(dest, min_size=1024, target_size=2048):
            padded += 1
        copied += 1
    print(f'Copied {copied} files, padded {padded} small files into {sort_base}')

    # run scanner on the sort_base (or dst_base) to upsert into sandbox DB
    print('Running scanner to upsert metadata into', db_path)
    res = scan_roots([str(dst_base)], db_path=str(db_path), batch_size=100)
    print('Scan result:', res)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', required=True, help='Source Splice folder')
    parser.add_argument('--dst', default='sandbox/src_samples', help='Destination base for raw imports')
    parser.add_argument('--sort', default='sandbox/OrganizedLibraryDemo', help='Destination base for sorted library')
    parser.add_argument('--db', default='sandbox/kass_test.db', help='SQLite DB path for scanner output')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    src = Path(args.src)
    dst_base = Path(args.dst)
    sort_base = Path(args.sort)
    db_path = Path(args.db)

    if not src.exists():
        print('Source path does not exist:', src)
        return

    dst_base.mkdir(parents=True, exist_ok=True)
    sort_base.mkdir(parents=True, exist_ok=True)

    import_and_sort(src, dst_base, sort_base, db_path, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
