# NOTE: `from __future__ import annotations` must be the very first
# non-comment statement in the file. Insert it here to satisfy the
# interpreter requirement.
from __future__ import annotations

# -------- ADVANCED KEYWORD ANALYSIS --------
def analyze_keywords(name: str) -> dict:
    """
    Analyze a file name for a wide set of keywords/phrases to improve classification.
    Returns a dict of detected categories.
    """
    n = name.lower()
    result = {}
    # Drums
    if re.search(r"\bkick( drum)?s?\b", n): result['drum'] = 'Kicks'
    if re.search(r"\bsnare(s)?\b", n): result['drum'] = 'Snares'
    if re.search(r"\bclap(s)?\b", n): result['drum'] = 'Claps'
    if re.search(r"\bhat(s)?\b|hihat|hi[- ]hat", n):
        if 'open' in n or 'ohh' in n: result['drum'] = 'Hats/Open Hats'
        elif 'closed' in n or 'chh' in n: result['drum'] = 'Hats/Closed Hats'
        else: result['drum'] = 'Hats/Shakers'
    if re.search(r"\bperc|percussion|bongo|conga|tom|rim|rimshot|block|cowbell|clave\b", n):
        result['drum'] = 'Percussion/Misc Perc'
    if re.search(r"fill", n): result['drum'] = 'Drum Fills'
    # Loops
    if re.search(r"loop|groove|bpm", n): result['loop'] = True
    # Breakbeats (e.g., amen breaks)
    if re.search(r"\b(amen|breakbeat|break)\b", n): result['breakbeat'] = True
    # Vocals
    # Acapella phrases (allow plural 'acapellas')
    if re.search(r"(acapella|acappella|acap|accap|accappella)s?", n): result['acapella'] = True
    if re.search(r"vocal|vox|chop|adlib|shout|phrase|hook|speech|talk|fx", n): result['vocal'] = True
    # FX
    if re.search(r"impact|hit|boom|riser|build|downlifter|downsweep|sweep|fall|transition|whoosh|swoosh|atmo|ambience|ambient|texture|noise|glitch|stutter|granular|reverse|rev|sub drop|subdrop|lfo|meme|bruh|vine|troll|womp|scream|cartoon", n):
        result['fx'] = True
    # Bass/Synth
    if re.search(r"808|bass|sub", n): result['bass'] = True
    if re.search(r"lead|synth|pad|pluck|arp|chord", n): result['synth'] = True
    # Presets
    if re.search(r"serum|massive x|massive|vital|sylenth|diva|preset|bank|wt|wavetable", n): result['preset'] = True
    # Genre
    for g in ["house","techno","trap","dubstep","dnb","drum and bass","jungle","neuro"]:
        if g in n: result['genre'] = g.title()
    # Misc
    if re.search(r"meme|fun|joke|cartoon|bruh|troll", n): result['meme'] = True
    return result
"""Core organizer functions extracted from the script for programmatic use."""
import os, re, shutil, sqlite3, logging
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Iterable, Optional, Tuple, Callable
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

# Lightweight typing for log callback
LogCb = Optional[Callable[[str], None]]

# -------- CONFIG --------
AUDIO_EXTS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg"}
MIDI_EXTS  = {".mid", ".midi"}
PRESET_EXTS = {".fxp", ".fxb", ".vstpreset", ".ksd", ".nmsv", ".vital", ".vitalbank", ".h2p", ".h2p64"}

ROOT_FOLDERS = [
    "01 Drums",
    "02 Bass",
    "03 Synths & Leads",
    "04 FX",
    "05 Vocals",
    "06 Loops & Grooves",
    "07 One Shots",
    "08 MIDI & Presets",
    "09 Instruments & Real Sounds",
    "10 Meme & Fun Sounds",
    "11 Reference & Templates",
]
LOOP_BUCKETS = [(120,130,"120–130 BPM"),(140,150,"140–150 BPM"),(170,10000,"170+ BPM")]
DEFAULT_LOOP_BIN = "Unsorted BPM"
GENRES = ["House","Techno","Trap","Dubstep","DnB"]

# Some regex helpers (kept simple)
RE_BPM   = re.compile(r"(?<!\d)(\d{2,3})\s*-?\s*bpm\b", re.I)
RE_LOOP  = re.compile(r"\b(loop|loops?|groove|grooves?)\b", re.I)
RE_ANY   = lambda *w: re.compile(r"|".join(fr"\b{re.escape(x)}\b" for x in w), re.I)
RE_HAT   = re.compile(r"\b(hi[-\s]?hat|hihat|hat)s?\b", re.I)
RE_KICK  = RE_ANY("kick")
RE_SNARE = RE_ANY("snare")
RE_CLAP  = RE_ANY("clap")
RE_BASS  = RE_ANY("808","bass","sub")
RE_SYNTH = RE_ANY("lead","synth","pad","pluck","arp","chord")
RE_VOCAL = RE_ANY("vocal","vox")
RE_MEME  = re.compile(r"\b(meme|bruh|vine|troll|womp|scream|cartoon)\b", re.I)

RE_SERUM   = re.compile(r"serum", re.I)
RE_MASSIVE = re.compile(r"\bmassive(?!\s*x)\b|\bnmsv\b|\bksd\b", re.I)
RE_MASSIVEX= re.compile(r"massive\s*x|\bnmsv\b", re.I)
RE_VITAL   = re.compile(r"\bvital\b", re.I)
RE_SYLENTH = re.compile(r"\bsylenth\b|\bsylenth1\b", re.I)
RE_DIVA    = re.compile(r"\bdiva\b|\bh2p(?:64)?\b", re.I)

# -------- UTILS --------

def is_hidden(p: Path) -> bool:
    return any(part.startswith('.') for part in p.parts)


def ensure_base_structure(dest: Path) -> None:
    for f in ROOT_FOLDERS:
        (dest / f).mkdir(parents=True, exist_ok=True)
    loops = dest / "06 Loops & Grooves"
    for g in GENRES + ["All Styles", "Breakbeats"]:
        base = loops / g
        for _,_,label in LOOP_BUCKETS:
            (base / label).mkdir(parents=True, exist_ok=True)
        (base / DEFAULT_LOOP_BIN).mkdir(parents=True, exist_ok=True)
    presets = dest / "08 MIDI & Presets"
    for synth in ["Serum","Massive","Massive X","Vital","Sylenth1","Diva","Generic"]:
        for sub in ["Presets","Banks","Wavetables","Tables","Misc"]:
            (presets / synth / sub).mkdir(parents=True, exist_ok=True)
    (presets / "MIDI").mkdir(parents=True, exist_ok=True)


def safe_hash(path: Path, block_size: int = 1<<20) -> Optional[str]:
    try:
        h = blake2b(digest_size=20)
        with path.open('rb') as f:
            while True:
                chunk = f.read(block_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logging.warning('Hash failed: %s (%s)', path, e)
        return None


def atomic_copy(src: Path, dst: Path) -> None:
    tmp = dst.with_suffix(dst.suffix + '.tmp')
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            try: tmp.unlink()
            except Exception: pass


def next_available_name(dst: Path) -> Path:
    if not dst.exists():
        return dst
    parent = dst.parent
    name = dst.name
    suffixes = getattr(dst, 'suffixes', None)
    if suffixes:
        ext = ''.join(suffixes)
        base_name = name[:-len(ext)]
    else:
        ext = dst.suffix
        base_name = dst.stem
    i = 1
    while True:
        cand = parent / f"{base_name}_{i}{ext}"
        if not cand.exists():
            return cand
        i += 1


def detect_bpm(text: str) -> Optional[int]:
    m = RE_BPM.search(text)
    if not m: return None
    try: return int(m.group(1))
    except Exception: return None


def pick_bpm_label(bpm: Optional[int]) -> str:
    if bpm is None: return DEFAULT_LOOP_BIN
    for lo,hi,label in LOOP_BUCKETS:
        if lo <= bpm <= hi: return label
    if bpm >= 170: return '170+ BPM'
    return DEFAULT_LOOP_BIN


def detect_genre(text: str) -> str:
    for g,rx in GENRES and [] or []: # defensive stub
        pass
    # simple detection using existing patterns from original file
    for g, rx in {"House": re.compile(r"\b(house|tech[-\s]?house|deep house|prog(?:ressive)? house)\b", re.I),
                 "Techno": re.compile(r"\b(techno|industrial techno|acid techno)\b", re.I),
                 "Trap": re.compile(r"\b(trap|trvp)\b", re.I),
                 "Dubstep": re.compile(r"\b(dubstep|riddim|tearout)\b", re.I),
                 "DnB": re.compile(r"\b(dnb|drum\s*&?\s*bass|jungle|neuro)\b", re.I)}.items():
        if rx.search(text):
            return g
    return 'All Styles'


def in_any(text: str, rx: re.Pattern) -> bool:
    return bool(rx.search(text))

# -------- CLASSIFICATION --------

def classify_path(file_path: Path, dest_root: Path) -> Path:
    name = file_path.name
    lname = name.lower()
    try:
        rel = str(file_path.parent).lower()
    except Exception:
        rel = ''
    merged = lname + ' ' + rel
    ext = file_path.suffix.lower()
    # Use advanced keyword analysis
    kw = analyze_keywords(name)
    # MIDI
    if ext in MIDI_EXTS:
        return dest_root / '08 MIDI & Presets/MIDI'
    # Presets
    if ext in PRESET_EXTS or kw.get('preset'):
        synth_base = dest_root / '08 MIDI & Presets'
        if 'serum' in lname:   return synth_base / 'Serum/Presets'
        if 'massive x' in lname: return synth_base / 'Massive X/Presets'
        if 'massive' in lname: return synth_base / 'Massive/Presets'
        if 'vital' in lname:
            if ext == '.vitalbank': return synth_base / 'Vital/Banks'
            return synth_base / 'Vital/Presets'
        if 'sylenth' in lname: return synth_base / 'Sylenth1/Presets'
        if 'diva' in lname:    return synth_base / 'Diva/Presets'
        return synth_base / 'Generic/Presets'
    # Wavetables
    if ext == '.wav' and re.search(r"\b(wt|wavetable|tables?)\b", merged, re.I):
        return dest_root / '08 MIDI & Presets/Serum/Wavetables'
    # Loops & Breakbeats (also detect by parent folder names)
    is_break = re.search(r"\b(amen|breakbeat|break)\b", merged, re.I)
    if kw.get('loop') or kw.get('breakbeat') or is_break:
        bpm = detect_bpm(merged)
        bpm_label = pick_bpm_label(bpm)
        if kw.get('breakbeat') or is_break:
            return dest_root / f'06 Loops & Grooves/Breakbeats/{bpm_label}'
        genre = kw.get('genre', detect_genre(merged))
        return dest_root / f'06 Loops & Grooves/{genre}/{bpm_label}'
    # Drums
    if 'drum' in kw:
        return dest_root / f"01 Drums/{kw['drum']}"
    # Vocals (acapella first; detect in file or parent folder names)
    is_acap = re.search(r"(acapella|acappella|acap|accap|accappella)s?", merged, re.I)
    if kw.get('acapella') or is_acap:
        return dest_root / '05 Vocals/Acapellas'
    if kw.get('vocal'):
        return dest_root / '05 Vocals/Vocal One Shots'
    # FX
    if kw.get('fx'):
        return dest_root / '04 FX'
    # Bass/Synth
    if kw.get('bass'):
        return dest_root / '02 Bass'
    if kw.get('synth'):
        return dest_root / '03 Synths & Leads'
    # Meme/Fun
    if kw.get('meme'):
        return dest_root / '10 Meme & Fun Sounds'
    # Fallback
    return dest_root / '07 One Shots'

# -------- DB --------
class DB:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        try:
            self.conn.execute('PRAGMA journal_mode=WAL;')
        except Exception:
            pass
        self.lock = Lock()
        self.session_hashes: set[str] = set()
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS files(
                hash TEXT PRIMARY KEY,
                size INTEGER,
                src  TEXT,
                dest_rel TEXT,
                mtime REAL,
                status TEXT
            )
        ''')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_size ON files(size)')
        self.conn.commit()

    def reserve(self, h: str, size: int, src: Path, mtime: Optional[float], *, persist: bool = True) -> bool:
        with self.lock:
            if h in self.session_hashes:
                return False
            row = self.conn.execute('SELECT status FROM files WHERE hash=?', (h,)).fetchone()
            if row:
                self.session_hashes.add(h)
                return False
            if persist:
                self.conn.execute('INSERT OR IGNORE INTO files(hash,size,src,dest_rel,mtime,status) VALUES (?,?,?,?,?,?)',
                                  (h, size, str(src), None, mtime, 'in-progress'))
                try:
                    self.conn.commit()
                except Exception:
                    pass
            self.session_hashes.add(h)
            return True

    def finalize(self, h: str, size: int, src: Path, dest_rel: Path, mtime: Optional[float], *, persist: bool = True) -> None:
        with self.lock:
            self.session_hashes.add(h)
            if persist:
                cur = self.conn.execute('UPDATE files SET size=?, src=?, dest_rel=?, mtime=?, status=? WHERE hash=?',
                                        (size, str(src), str(dest_rel), mtime, 'done', h))
                if cur.rowcount == 0:
                    self.conn.execute('INSERT OR IGNORE INTO files(hash,size,src,dest_rel,mtime,status) VALUES (?,?,?,?,?,?)',
                                      (h, size, str(src), str(dest_rel), mtime, 'done'))
                try:
                    self.conn.commit()
                except Exception:
                    pass

    def find_done_by_size_mtime(self, size: int, mtime: Optional[float]) -> Optional[str]:
        """Return a hash for an already-processed file that matches size+mtime and status='done'.
        This allows skipping the expensive hashing step when a file hasn't changed.
        """
        with self.lock:
            if mtime is None:
                row = self.conn.execute('SELECT hash FROM files WHERE size=? AND mtime IS NULL AND status=?',
                                        (size, 'done')).fetchone()
            else:
                row = self.conn.execute('SELECT hash FROM files WHERE size=? AND mtime=? AND status=?',
                                        (size, mtime, 'done')).fetchone()
            if row:
                return row[0]
            return None

    def close(self):
        with self.lock:
            try:
                self.conn.commit()
            finally:
                self.conn.close()

import json
import time
# -------- PIPELINE --------
@dataclass

class Job:
    src: Path
    rel_pack: str


# --- MEMORY FOR LAST USED FOLDERS/FILES ---
MEMORY_PATH = Path.home() / '.sample_organizer_memory.json'
def load_memory():
    if MEMORY_PATH.exists():
        try:
            with MEMORY_PATH.open('r', encoding='utf-8') as fh:
                data = json.load(fh)
                # normalize types
                if isinstance(data.get('processed'), list):
                    data['processed'] = set(data['processed'])
                # ensure recent lists exist
                data.setdefault('recent_srcs', [])
                data.setdefault('recent_dests', [])
                return data
        except Exception:
            pass
    return {'last_src': None, 'last_dest': None, 'processed': set(), 'recent_srcs': [], 'recent_dests': []}

def save_memory(mem):
    try:
        # Convert set to list for JSON
        mem = dict(mem)
        if isinstance(mem.get('processed'), set):
            mem['processed'] = list(mem['processed'])
        # recent lists should be lists
        if isinstance(mem.get('recent_srcs'), set):
            mem['recent_srcs'] = list(mem['recent_srcs'])
        if isinstance(mem.get('recent_dests'), set):
            mem['recent_dests'] = list(mem['recent_dests'])
        with MEMORY_PATH.open('w', encoding='utf-8') as fh:
            json.dump(mem, fh)
    except Exception:
        pass

def add_processed_file(mem, fpath):
    if 'processed' not in mem or not isinstance(mem['processed'], (set, list)):
        mem['processed'] = set()
    if isinstance(mem['processed'], list):
        mem['processed'] = set(mem['processed'])
    mem['processed'].add(str(fpath))


def add_recent_src(mem, path: str, limit: int = 10):
    if not path:
        return
    lst = mem.get('recent_srcs') or []
    if path in lst:
        lst.remove(path)
    lst.insert(0, path)
    mem['recent_srcs'] = lst[:limit]


def add_recent_dest(mem, path: str, limit: int = 10):
    if not path:
        return
    lst = mem.get('recent_dests') or []
    if path in lst:
        lst.remove(path)
    lst.insert(0, path)
    mem['recent_dests'] = lst[:limit]

def is_processed(mem, fpath):
    if 'processed' not in mem:
        return False
    if isinstance(mem['processed'], list):
        mem['processed'] = set(mem['processed'])
    return str(fpath) in mem['processed']

def clear_memory(confirm=False):
    if confirm and MEMORY_PATH.exists():
        MEMORY_PATH.unlink()
        return True
    return False


def iter_media(root: Path) -> Iterable[Path]:
    mem = load_memory()
    for p in root.rglob('*'):
        if p.is_file() and not is_hidden(p):
            ext = p.suffix.lower()
            if ext in AUDIO_EXTS or ext in MIDI_EXTS or ext in PRESET_EXTS:
                if not is_processed(mem, p):
                    yield p


def process(job: Job, dest_root: Path, db: DB, dry: bool, tag_source: bool, log_cb: LogCb = None, *, deep: bool = False) -> Tuple[bool,str]:
    # Load and update memory for last used folders and processed files
    mem = load_memory()
    mem['last_src'] = str(job.src.parent)
    mem['last_dest'] = str(dest_root)

    src = job.src
    try:
        st = src.stat()
        size = st.st_size
        mtime = st.st_mtime
    except Exception as e:
        return False, f'stat fail: {src} ({e})'


    # Quick prefilter: if a done entry exists with same size+mtime, skip hashing/copy.
    try:
        existing_hash = db.find_done_by_size_mtime(size, mtime)
    except Exception:
        existing_hash = None
    if existing_hash:
        # ensure this hash is recorded in the in-memory session to prevent duplicates
        try:
            db.reserve(existing_hash, size, src, mtime, persist=not dry)
        except Exception:
            pass
        add_processed_file(mem, src)
        save_memory(mem)
        return True, f'skip duplicate (size+mtime): {src.name}'

    h = safe_hash(src)
    if not h:
        return False, f'hash fail: {src}'
    reserved = db.reserve(h, size, src, mtime, persist=not dry)
    if not reserved:
        add_processed_file(mem, src)
        save_memory(mem)
        return True, f'skip duplicate: {src.name}'
    target_dir = classify_path(src, dest_root)
    # Optional deep audio analysis override
    if deep and src.suffix.lower() in {'.wav','.aif','.aiff','.flac','.mp3','.ogg'}:
        try:
            from .audio_features import analyze_and_classify
            grp, features = analyze_and_classify(src)
            # Override certain groups
            if grp == 'Acapella':
                target_dir = dest_root / '05 Vocals/Acapellas'
            elif grp == 'Breakbeat Loop':
                target_dir = dest_root / '06 Loops & Grooves/Breakbeats/Unsorted BPM'
            elif grp == 'Loop':
                # Fall back to All Styles/Unsorted BPM for generic loops
                target_dir = dest_root / '06 Loops & Grooves/All Styles/Unsorted BPM'
            elif grp == 'Vocal':
                target_dir = dest_root / '05 Vocals/Vocal One Shots'
        except Exception:
            # Ignore deep errors and keep filename-based classification
            pass
    target_dir.mkdir(parents=True, exist_ok=True)
    dst_name = src.name
    if tag_source and job.rel_pack:
        stem, ext = os.path.splitext(dst_name)
        pack = Path(job.rel_pack).parts[0]
        safe_pack = re.sub(r'[^\w\s\-\+&]','',pack).strip().replace(' ','')
        dst_name = f"{stem}_[{safe_pack}]{ext}"
    dst = next_available_name(target_dir / dst_name)
    if not dry:
        try:
            atomic_copy(src, dst)
        except Exception as e:
            return False, f'copy fail: {src} -> {dst} ({e})'
    rel_path = dst.relative_to(dest_root)
    db.finalize(h, size, src, rel_path, mtime, persist=not dry)
    add_processed_file(mem, src)
    save_memory(mem)
    if log_cb:
        log_cb(f'OK -> {rel_path}')
    return True, f'OK -> {rel_path}'
