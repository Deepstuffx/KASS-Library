"""Import helper for KASS-style repositories into the organizer.

Usage:
    python tools/import_kass.py --src PATH --dest PATH [--dry-run] [--clone URL]

If --clone is provided the script will git-clone the URL into `external/` and use that path.
Dry-run will print a CSV mapping of source -> computed destination.
"""
from __future__ import annotations
import argparse
import csv
import os
import subprocess
from pathlib import Path
from typing import List

from kams_sorter.core import classify_path, ensure_base_structure, iter_media


def clone_repo(url: str, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    name = url.rstrip('/').split('/')[-1]
    dest = out / name
    if dest.exists():
        print(f"Using existing clone at {dest}")
        return dest
    print(f"Cloning {url} -> {dest}")
    subprocess.check_call(['git', 'clone', url, str(dest)])
    return dest


def dry_run(src: Path, dest_root: Path, out_csv: Path | None = None) -> List[tuple]:
    rows = []
    for p in iter_media(src):
        try:
            dst = classify_path(p, dest_root)
            rows.append((str(p), str(dst)))
        except Exception as e:
            rows.append((str(p), f'ERROR: {e}'))
    if out_csv:
        with out_csv.open('w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['src','predicted_dest'])
            w.writerows(rows)
    return rows


def perform_import(src: Path, dest_root: Path, dry: bool, tag: bool, workers: int):
    # Use the organizer CLI pipeline: create destination structure and call process via jobs
    ensure_base_structure(dest_root)
    from kams_sorter.cli import main as cli_main
    # The CLI is a small wrapper; rather than reusing it directly here we will call the module
    # programmatically by building jobs (to keep behavior explicit). Simpler: shell out to CLI for now.
    cmd = ['python', '-m', 'kams_sorter.cli', str(src), str(dest_root)]
    if dry:
        cmd.append('--dry-run')
    if tag:
        cmd.append('--tag-source')
    if workers:
        cmd += ['--workers', str(workers)]
    print('Running:', ' '.join(cmd))
    subprocess.check_call(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--clone', help='Git URL to clone (optional)')
    ap.add_argument('--src', help='Path to local repo (if --clone not used)')
    ap.add_argument('--dest', required=True, help='Destination library root')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out-csv', help='Write dry-run mapping to CSV')
    ap.add_argument('--tag-source', action='store_true')
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()

    base = Path.cwd()
    if args.clone:
        src = clone_repo(args.clone, base / 'external')
    elif args.src:
        src = Path(args.src).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f'src not found: {src}')
    else:
        raise SystemExit('Either --clone or --src must be provided')

    dest = Path(args.dest).expanduser().resolve()
    if args.dry_run:
        rows = dry_run(src, dest, Path(args.out_csv) if args.out_csv else None)
        for s,d in rows[:200]:
            print(s,'->',d)
        print(f'... total {len(rows)} items')
    else:
        perform_import(src, dest, args.dry_run, args.tag_source, args.workers)


if __name__ == '__main__':
    main()
