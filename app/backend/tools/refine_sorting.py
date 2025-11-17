#!/usr/bin/env python3
"""Refine sorting inside an OrganizedLibraryDemo folder by moving files
into more specific subfolders based on filename keywords and hints.

Usage: PYTHONPATH=. python app/backend/tools/refine_sorting.py --root sandbox/OrganizedLibraryDemo
"""
import argparse
from pathlib import Path
import shutil
import os


KEYWORD_MAP = [
    # FX subcategories (path relative to root)
    (['riser', 'risers'], '04 FX/Risers'),
    (['downer', 'downers'], '04 FX/Downers'),
    (['spinback', 'spinbacks'], '04 FX/Spinbacks'),
    (['sweep', 'sweeps'], '04 FX/Sweeps'),
    (['impact', 'impacts'], '04 FX/Impacts'),
    (['glitch', 'stutter', 'stutters'], '04 FX/Glitches & Stutters'),
    (['foley'], '04 FX/Foley'),
    (['texture', 'atmo', 'atmos', 'atmosphere'], '04 FX/Textures & Atmos'),
    (['transition', 'transitions'], '04 FX/Transitions'),
    # Hats
    (['openhat', 'open hat', 'open-hat', 'open_hat', 'oh'], '01 Drums/Hats/Open Hats'),
    (['closedhat', 'closed hat', 'closed-hat', 'closed_hat', 'ch', 'closed'], '01 Drums/Hats/Closed Hats'),
    (['hat', 'hihat', 'hi-hat', 'hats'], '01 Drums/Hats'),
    # Kicks / snares / claps / percussion
    (['kick', '808'], '01 Drums/Kicks'),
    (['snare', 'snares'], '01 Drums/Snares'),
    (['clap', 'claps'], '01 Drums/Claps'),
    (['perc', 'percussion', 'percs'], '01 Drums/Percussion'),
    (['rim', 'rimshot'], '01 Drums/Snares'),
    # Bass
    (['bass'], '02 Bass'),
    # Synths and leads
    (['lead', 'leads', 'synth', 'synths', 'pad'], '03 Synths & Leads'),
    # Vocals
    (['vocal', 'vox', 'acapella', 'acapella', 'acappella'], '05 Vocals/Vocal One Shots'),
    # Loops and grooves
    (['loop', 'loops', 'groove', 'grooves'], '06 Loops & Grooves/All Styles/Unsorted BPM'),
    # One shots fallback
    (['oneshot', 'one-shot', 'one_shot', 'one shots'], '07 One Shots'),
    # FX generic
    (['fx'], '04 FX'),
]


def find_match(filename: str):
    s = filename.lower()
    for keywords, rel in KEYWORD_MAP:
        for kw in keywords:
            if kw in s:
                return rel
    return None


def refine(root: Path, dry_run: bool = False):
    moved = 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # avoid traversing into newly created target dirs by skipping top-level dirs
        for fn in filenames:
            total += 1
            src = Path(dirpath) / fn
            rel_match = find_match(fn)
            if not rel_match:
                continue
            dest_dir = root / rel_match
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / fn
            if src.resolve() == dest.resolve():
                continue
            if dry_run:
                print('[DRY] MOVE', src, '->', dest)
                moved += 1
                continue
            try:
                shutil.move(str(src), str(dest))
                moved += 1
            except Exception as e:
                print('Failed to move', src, '->', dest, e)
    print(f'Refined {moved} files out of {total} scanned under {root}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='sandbox/OrganizedLibraryDemo')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    root = Path(args.root)
    if not root.exists():
        print('Root folder not found:', root)
        return
    refine(root, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
