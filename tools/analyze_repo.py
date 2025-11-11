"""Analyze a repository of sample packs and produce a mapping report for the organizer.

Usage:
    python tools/analyze_repo.py --clone <git-url> --dest <dest-root> [--out-csv map.csv] [--out-json summary.json] [--deep]
    python tools/analyze_repo.py --src <local-path> --dest <dest-root> ...

By default it runs in "fast" mode (filename-only classification). Use --deep to enable audio-based feature extraction for improved classification (requires librosa).
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from organizer.core import classify_path, iter_media

try:
    from organizer.audio_features import analyze_and_classify
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False


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


def analyze(src: Path, dest_root: Path, deep: bool=False) -> Iterable[dict]:
    for p in iter_media(src):
        try:
            pred = classify_path(p, dest_root)
        except Exception as e:
            pred = f'ERROR: {e}'
        entry = {
            'src': str(p),
            'ext': p.suffix.lower(),
            'predicted_dest': str(pred),
            'size': p.stat().st_size if p.exists() else None,
        }
        if deep and AUDIO_AVAILABLE and p.suffix.lower() in {'.wav','.aif','.aiff','.flac','.mp3','.ogg'}:
            try:
                grp, features = analyze_and_classify(p)
                entry['audio_group'] = grp
                entry['features'] = features
                # Destination override for certain detected groups
                if grp == 'Acapella':
                    entry['predicted_dest'] = str(dest_root / '05 Vocals/Acapellas')
                elif grp == 'Breakbeat Loop':
                    entry['predicted_dest'] = str(dest_root / '06 Loops & Grooves/Breakbeats/Unsorted BPM')
            except Exception as e:
                entry['audio_error'] = str(e)
        yield entry


def summarize(rows: Iterable[dict]) -> dict:
    total = 0
    by_ext = Counter()
    by_dest = Counter()
    size_total = 0
    largest = []
    folders = Counter()
    for r in rows:
        total += 1
        by_ext[r.get('ext','')] += 1
        by_dest[r.get('predicted_dest','')] += 1
        s = r.get('size') or 0
        size_total += s
        largest.append((s, r.get('src')))
        # parent folder
        try:
            folders[Path(r['src']).parent.name] += 1
        except Exception:
            pass
    largest_sorted = sorted(largest, reverse=True)[:10]
    top_folders = folders.most_common(10)
    return {
        'total_files': total,
        'total_size_bytes': size_total,
        'by_extension': dict(by_ext),
        'by_predicted_dest': dict(by_dest),
        'largest': [{'size': s, 'path': p} for s,p in largest_sorted],
        'top_folders': [{'folder': f, 'count': c} for f,c in top_folders]
    }


def _next_report_paths(base_reports: Path, deep: bool):
    base_reports.mkdir(parents=True, exist_ok=True)
    prefix = 'deep' if deep else 'fast'
    # Prefer versioned filenames: *_vN.csv/json; find next N across both csv and json
    def next_version(stem: str, ext: str) -> Path:
        n = 1
        while True:
            cand = base_reports / f"{stem}_v{n}.{ext}"
            if not cand.exists():
                return cand
            n += 1
    csv_path = next_version(f"{prefix}_sample_map", 'csv')
    json_path = next_version(f"{prefix}_sample_summary", 'json')
    return csv_path, json_path


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--clone', help='Git URL to clone')
    group.add_argument('--src', help='Path to local repo')
    ap.add_argument('--dest', required=True, help='Destination library root (used to compute predicted dest)')
    ap.add_argument('--out-csv', help='Write mapping CSV (defaults to reports/<prefix>_sample_map_vN.csv)')
    ap.add_argument('--out-json', help='Write summary JSON (defaults to reports/<prefix>_sample_summary_vN.json)')
    ap.add_argument('--deep', action='store_true', help='Enable audio feature extraction (slow)')
    ap.add_argument('--max', type=int, default=0, help='Limit number of files analyzed (0=all)')
    args = ap.parse_args()

    base = Path.cwd()
    if args.clone:
        src = clone_repo(args.clone, base / 'external')
    else:
        src = Path(args.src).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f'src not found: {src}')

    dest_root = Path(args.dest).expanduser().resolve()
    rows = []
    count = 0
    writer = None
    csvfh = None
    # Default output locations under reports/ with versioning
    reports_dir = Path('reports')
    out_csv = Path(args.out_csv) if args.out_csv else None
    out_json = Path(args.out_json) if args.out_json else None
    if out_csv is None or out_json is None:
        auto_csv, auto_json = _next_report_paths(reports_dir, deep=args.deep)
        if out_csv is None:
            out_csv = auto_csv
        if out_json is None:
            out_json = auto_json
    # Prepare CSV writer
    csvfh = open(out_csv, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfh, fieldnames=['src','ext','size','predicted_dest','audio_group'])
    writer.writeheader()

    try:
        for r in analyze(src, dest_root, deep=args.deep):
            rows.append(r)
            if writer:
                writer.writerow({
                    'src': r.get('src'),
                    'ext': r.get('ext'),
                    'size': r.get('size'),
                    'predicted_dest': r.get('predicted_dest'),
                    'audio_group': r.get('audio_group','')
                })
            count += 1
            if args.max and count >= args.max:
                break
            if count % 200 == 0:
                print(f'Analyzed {count} files...')
    finally:
        if csvfh:
            csvfh.close()

    summary = summarize(rows)
    print('Summary:')
    print(json.dumps(summary, indent=2))
    # Always write JSON summary to the selected path
    with open(out_json, 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)
    print(f"Wrote CSV -> {out_csv}")
    print(f"Wrote JSON -> {out_json}")

if __name__ == '__main__':
    main()
