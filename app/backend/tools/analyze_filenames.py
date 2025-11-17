#!/usr/bin/env python3
"""Analyze filenames under sandbox/OrganizedLibraryDemo to propose new keyphrases.

Outputs a suggestion CSV with token, count, and suggested destination relative path
and a short report printed to stdout. Uses existing KEYWORD_MAP from refine_sorting
to determine which files are already placed.
"""
import re
import csv
import argparse
from collections import Counter, defaultdict
from pathlib import Path

from app.backend.tools.refine_sorting import KEYWORD_MAP, find_match


TOKEN_RE = re.compile(r"[A-Za-z0-9#\+\-]{2,}")


def tokenize(name: str):
    s = Path(name).stem
    tokens = TOKEN_RE.findall(s.lower())
    # normalize some tokens
    tokens = [t.replace('_', '').replace('-', '').strip() for t in tokens if t]
    return tokens


HEURISTIC_FOLDERS = [
    ('riser', '04 FX/Risers'),
    ('sweep', '04 FX/Sweeps'),
    ('whoosh', '04 FX/Sweeps'),
    ('impact', '04 FX/Impacts'),
    ('hit', '04 FX/Impacts'),
    ('reverse', '04 FX/Glitches & Stutters'),
    ('glitch', '04 FX/Glitches & Stutters'),
    ('loop', '06 Loops & Grooves/All Styles/Unsorted BPM'),
    ('bpm', '06 Loops & Grooves/All Styles/Unsorted BPM'),
    ('kick', '01 Drums/Kicks'),
    ('808', '01 Drums/Kicks'),
    ('snare', '01 Drums/Snares'),
    ('clap', '01 Drums/Claps'),
    ('hat', '01 Drums/Hats'),
    ('openhat', '01 Drums/Hats/Open Hats'),
    ('closedhat', '01 Drums/Hats/Closed Hats'),
    ('vocal', '05 Vocals/Vocal One Shots'),
    ('vox', '05 Vocals/Vocal One Shots'),
    ('bass', '02 Bass'),
    ('lead', '03 Synths & Leads'),
    ('pad', '03 Synths & Leads'),
    ('fx', '04 FX'),
]


def heuristic_folder_for_token(token: str):
    for k, dest in HEURISTIC_FOLDERS:
        if k in token:
            return dest
    return None


def analyze(root: Path, out_csv: Path, top_n: int = 200):
    root = Path(root)
    all_files = []
    for p in root.rglob('*'):
        if p.is_file():
            all_files.append(p)

    matched = []
    unmatched = []
    file_tokens = {}

    for p in all_files:
        fn = p.name
        m = find_match(fn)
        toks = tokenize(fn)
        file_tokens[fn] = toks
        if m:
            matched.append((fn, m))
        else:
            unmatched.append(fn)

    # token frequency across all and unmatched
    total_counter = Counter()
    unmatched_counter = Counter()
    for fn, tks in file_tokens.items():
        for t in set(tks):
            total_counter[t] += 1
    for fn in unmatched:
        for t in set(file_tokens[fn]):
            unmatched_counter[t] += 1

    # propose tokens that appear frequently in unmatched but are not in existing KEYWORD_MAP
    existing_keys = set()
    for kws, rel in KEYWORD_MAP:
        for k in kws:
            existing_keys.add(k.lower())

    suggestions = []
    for token, cnt in unmatched_counter.most_common(top_n):
        if token in existing_keys:
            continue
        suggested_folder = heuristic_folder_for_token(token)
        suggestions.append((token, cnt, suggested_folder or 'UNCATEGORIZED'))

    # write suggestions CSV
    with out_csv.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['token', 'unmatched_count', 'suggested_folder'])
        for row in suggestions:
            w.writerow(row)

    # prepare report
    report = {
        'total_files': len(all_files),
        'matched_files': len(matched),
        'unmatched_files': len(unmatched),
        'top_unmatched_tokens': suggestions[:50],
    }
    return report, unmatched[:50]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='sandbox/OrganizedLibraryDemo')
    p.add_argument('--out', default='sandbox/keyword_suggestions.csv')
    args = p.parse_args()
    rep, sample_unmatched = analyze(Path(args.root), Path(args.out))
    print('Analysis Report:')
    print(' Total files:', rep['total_files'])
    print(' Matched files (existing map):', rep['matched_files'])
    print(' Unmatched files:', rep['unmatched_files'])
    print('\nTop suggested tokens (token, unmatched_count, suggested_folder):')
    for t in rep['top_unmatched_tokens'][:30]:
        print(' ', t)
    print('\nSample unmatched filenames:')
    for u in sample_unmatched:
        print(' ', u)
    print('\nSuggestions written to', args.out)


if __name__ == '__main__':
    main()
