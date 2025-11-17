import re
from typing import Dict, List, Optional
from rapidfuzz import process, fuzz

INSTRUMENT_VOCAB = [
    "kick", "snare", "clap", "hat", "hihat", "perc", "808", "bass",
    "pad", "lead", "fx", "vocal", "vox", "rim", "tom", "shaker", "snap"
]

BPM_RE = re.compile(r"(\d{2,3})\s*bpm", re.I)
KEY_RE = re.compile(r"^[A-G](?:#|b)?(?:m|min|maj|major|minor)?$", re.I)
NUMBER_TOKEN_RE = re.compile(r"^\d{2,3}$")


def tokenize(filename: str) -> List[str]:
    base = re.sub(r"\.[^.]+$", "", filename)
    parts = re.split(r"[_\-\.\s]+", base)
    tokens = [p.lower().strip() for p in parts if p.strip()]
    return tokens


def parse_filename(filename: str, fuzzy_threshold: int = 85, debug: bool = False) -> Dict[str, Optional[object]]:
    tokens = tokenize(filename)
    bpm: Optional[int] = None
    key: Optional[str] = None
    instrument: Optional[str] = None
    fuzzy_score: Optional[float] = None
    token_matches: Optional[list] = None

    # Look for explicit bpm token like `128bpm` inside filename or tokens
    m = BPM_RE.search(filename)
    if m:
        try:
            bpm = int(m.group(1))
        except ValueError:
            bpm = None

    if bpm is None:
        for t in tokens:
            # token like '128bpm'
            m2 = BPM_RE.match(t)
            if m2:
                try:
                    bpm = int(m2.group(1))
                    break
                except ValueError:
                    continue
            if NUMBER_TOKEN_RE.match(t):
                val = int(t)
                if 30 <= val <= 400:
                    bpm = val
                    break

    # Key - look in tokens for explicit key tokens like A# or Gm
    for t in tokens:
        if KEY_RE.match(t):
            # normalize to uppercase letter + accidental
            key_match = re.match(r"([A-G](?:#|b)?)", t, re.I)
            if key_match:
                key = key_match.group(1).upper()
                break

    # Instrument exact match
    for t in tokens:
        if t in INSTRUMENT_VOCAB:
            instrument = t
            fuzzy_score = 100.0
            break

    # Fuzzy match if not exact
    if instrument is None and tokens:
        # collect per-token match info when debug requested
        token_matches = []
        # Score tokens against vocab
        best = None
        best_score = 0.0
        for t in tokens:
            res = process.extractOne(t, INSTRUMENT_VOCAB, scorer=fuzz.token_sort_ratio)
            if res:
                match, score, _ = res
            else:
                match, score = (None, 0.0)
            token_matches.append({"token": t, "best_match": match, "score": float(score)})
            if score > best_score:
                best = match
                best_score = score
        if best and best_score >= fuzzy_threshold:
            instrument = best
            fuzzy_score = float(best_score)

    out = {
        "tokens": tokens,
        "bpm": bpm,
        "key": key,
        "instrument": instrument,
        "fuzzy_score": fuzzy_score,
    }
    if debug:
        out["token_matches"] = token_matches if token_matches is not None else []
    return out


if __name__ == "__main__":
    examples = [
        "Kick_01_128bpm.wav",
        "Snare-140.wav",
        "Lead_A#_64bpm.wav",
        "cool_fx_808_loop.wav",
    ]
    for e in examples:
        print(e, "=>", parse_filename(e))
