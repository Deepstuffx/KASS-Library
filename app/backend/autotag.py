import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .db import get_conn, init_db

try:
    from .dsp import extract_audio_metadata
except Exception:
    extract_audio_metadata = None


def generate_autotags_from_parsed(parsed: dict, metadata: Optional[dict]) -> List[Tuple[str, float]]:
    """Rule-based baseline that returns list of (tag, confidence).
    Uses parsed filename tokens and optional DSP metadata (bpm, duration, key).
    Confidence is a heuristic in [0, 1].
    """
    tags: List[Tuple[str, float]] = []
    name = parsed.get('original', '') if parsed.get('original') else ''
    tokens = parsed.get('tokens') or []
    instrument = (parsed.get('instrument') or '')
    bpm_hint = parsed.get('bpm')

    name_l = name.lower() if name else ''

    # helper to add tag with min confidence merging
    def add(tag: str, conf: float):
        tags.append((tag, max(0.0, min(1.0, float(conf)))))

    # basic categories
    if 'loop' in name_l or any('loop' in (t.lower() if isinstance(t, str) else '') for t in tokens):
        add('loop', 0.9)
        if bpm_hint:
            add('loop:bpm_hint', 0.7)
    # vocals
    if any(k in name_l for k in ('vocal', 'vox', 'voice', 'singer', 'vocalhit', 'vocal_hit')) or ('vocal' in (instrument or '').lower()):
        add('vocal', 0.95)
    # drum one-shots / types
    if any(k in name_l for k in ('kick', 'bd', 'kickloop')) or ('kick' in (instrument or '').lower()):
        add('kick', 0.9)
    if any(k in name_l for k in ('snare', 'sn')) or ('snare' in (instrument or '').lower()):
        add('snare', 0.9)
    if any(k in name_l for k in ('hat', 'hihat', 'hh')):
        add('hat', 0.9)
    if any(k in name_l for k in ('tom',)):
        add('tom', 0.85)
    if any(k in name_l for k in ('fill', 'fills', 'drumfill')):
        add('fill', 0.9)
    if any(k in name_l for k in ('cymbal', 'crash', 'ride', 'splash', 'china')):
        add('cymbal', 0.9)
    if any(k in name_l for k in ('perc', 'percussion', 'shaker', 'bongo', 'conga')):
        add('percussion', 0.85)

    # melodic / bass / fx
    if any(k in name_l for k in ('bass', 'sub', '808')):
        add('bass', 0.9)
    if any(k in name_l for k in ('pad', 'lead', 'synth', 'plucked', 'melody', 'arp')):
        add('melodic', 0.8)
    if any(k in name_l for k in ('fx', 'impact', 'sweep', 'whoosh')):
        add('fx', 0.8)

    # use DSP metadata to boost confidence for loops when duration >= 2s
    if metadata:
        dur = metadata.get('duration')
        bpm = metadata.get('bpm')
        if dur is not None:
            try:
                d = float(dur)
                if d >= 2.0 and any(t[0] == 'loop' for t in tags):
                    # boost loop confidence
                    tags = [(t, min(1.0, c + 0.05)) if t == 'loop' else (t, c) for t, c in tags]
            except Exception:
                pass
        if bpm:
            try:
                _ = float(bpm)
                add('bpm_detected', 0.6)
            except Exception:
                pass
    # fallback tag
    if not tags:
        add('one_shot', 0.4)

    # coalesce tags by taking max confidence per tag
    out: Dict[str, float] = {}
    for t, c in tags:
        if t in out:
            out[t] = max(out[t], c)
        else:
            out[t] = c
    return sorted(list(out.items()), key=lambda x: -x[1])


def run_autotag_pass(roots: List[str], db_path: Optional[str] = None, dry_run: bool = True, limit: Optional[int] = None) -> Dict[str, object]:
    """Run autotag baseline over samples already present in the DB under the provided roots.
    Returns a summary dict.
    """
    conn = get_conn(db_path) if db_path else get_conn()
    init_db(conn)
    root0 = str(Path(roots[0]).resolve()) if roots else None
    cur = conn.cursor()
    params = []
    q = "SELECT id, full_path, filename, parsed_tokens, bpm, duration FROM samples"
    if root0:
        q += " WHERE root_dir = ?"
        params.append(root0)
    if limit:
        q += " LIMIT ?"
        params.append(limit)
    cur.execute(q, tuple(params))
    rows = cur.fetchall()
    total = len(rows)
    wrote = 0
    tag_counts: Dict[str, int] = {}
    examples: List[Tuple[str, List[Tuple[str, float]]]] = []
    for r in rows:
        sample_id = r['id']
        fname = r['filename']
        parsed = {}
        try:
            parsed = json.loads(r['parsed_tokens']) if r['parsed_tokens'] else {}
            # parsed_tokens may be a list (tokens) or a dict; normalize to dict
            if isinstance(parsed, list):
                parsed = {'tokens': parsed}
        except Exception:
            parsed = {}
        # ensure parsed includes original filename
        if not isinstance(parsed, dict):
            parsed = {'tokens': []}
        parsed.setdefault('original', fname)
        parsed.setdefault('tokens', parsed.get('tokens') or [])
        meta = {'bpm': r['bpm'], 'duration': r['duration']}
        tags = generate_autotags_from_parsed(parsed, meta)
        for tag, conf in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        if not dry_run:
            for tag, conf in tags:
                try:
                    from .db import upsert_autotag
                    upsert_autotag(conn, sample_id, tag, conf)
                    wrote += 1
                except Exception:
                    pass
        if len(examples) < 20:
            examples.append((fname, tags[:5]))
    summary = {
        'total_samples': total,
        'wrote_autotags': wrote,
        'tag_counts': tag_counts,
        'examples': examples,
    }
    conn.close()
    return summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('roots', nargs='+')
    parser.add_argument('--db', default=None)
    parser.add_argument('--apply', action='store_true', help='Write autotags to DB')
    args = parser.parse_args()
    res = run_autotag_pass(args.roots, db_path=args.db, dry_run=not args.apply)
    print(res)
