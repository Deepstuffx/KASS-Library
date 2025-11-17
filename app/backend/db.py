import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "kass.db"

# In-process cancel registry to allow immediate visibility for jobs cancelled
# via db helper within the same Python process (useful for tests and in-process control)
_inproc_cancel_registry: dict[str, int] = {}

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS samples (
    id TEXT PRIMARY KEY,
    full_path TEXT UNIQUE,
    rel_path TEXT,
    root_dir TEXT,
    filename TEXT,
    ext TEXT,
    size_bytes INTEGER,
    bpm REAL,
    duration REAL,
    sample_rate INTEGER,
    channels INTEGER,
    content_hash TEXT,
    bpm_hint INTEGER,
    key_hint TEXT,
    key_detected TEXT,
    instrument_hint TEXT,
    fuzzy_score REAL,
    parsed_tokens TEXT,
    added_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_samples_root_rel ON samples (root_dir, rel_path);
CREATE INDEX IF NOT EXISTS idx_samples_instrument ON samples (instrument_hint);

CREATE TABLE IF NOT EXISTS scan_jobs (
    id TEXT PRIMARY KEY,
    status TEXT,
    roots TEXT,
    db_path TEXT,
    batch_size INTEGER,
    min_size INTEGER,
    result TEXT,
    error TEXT,
    cancel_requested INTEGER DEFAULT 0,
    started_at DATETIME DEFAULT (datetime('now')),
    finished_at DATETIME
);

CREATE TABLE IF NOT EXISTS dsp_jobs (
    id TEXT PRIMARY KEY,
    status TEXT,
    params TEXT,
    db_path TEXT,
    processed INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    result TEXT,
    error TEXT,
    cancel_requested INTEGER DEFAULT 0,
    started_at DATETIME DEFAULT (datetime('now')),
    finished_at DATETIME
);

CREATE TABLE IF NOT EXISTS autotags (
    sample_id TEXT,
    tag TEXT,
    confidence REAL,
    created_at DATETIME DEFAULT (datetime('now')),
    PRIMARY KEY(sample_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_autotags_sample ON autotags (sample_id);
"""


def get_conn(path: Path | str | None = None) -> sqlite3.Connection:
    p = DB_PATH if path is None else Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection | None = None):
    own_conn = False
    if conn is None:
        conn = get_conn()
        own_conn = True
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    conn.commit()
    if own_conn:
        conn.close()


### Job helpers
def create_job(conn: sqlite3.Connection, job_id: str, roots: str, db_path: Optional[str], batch_size: int, min_size: int):
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO scan_jobs (id, status, roots, db_path, batch_size, min_size, cancel_requested) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (job_id, 'running', roots, db_path, batch_size, min_size, 0),
    )
    conn.commit()


def set_job_result(conn: sqlite3.Connection, job_id: str, result: dict):
    cur = conn.cursor()
    cur.execute("UPDATE scan_jobs SET status=?, result=?, finished_at=datetime('now') WHERE id=?", ('done', json.dumps(result), job_id))
    conn.commit()


def set_job_failed(conn: sqlite3.Connection, job_id: str, error: str):
    cur = conn.cursor()
    cur.execute("UPDATE scan_jobs SET status=?, error=?, finished_at=datetime('now') WHERE id=?", ('failed', error, job_id))
    conn.commit()


def mark_job_cancel_requested(conn: sqlite3.Connection, job_id: str):
    cur = conn.cursor()
    cur.execute("UPDATE scan_jobs SET cancel_requested=1 WHERE id=?", (job_id,))
    conn.commit()
    try:
        _inproc_cancel_registry[job_id] = 1
    except Exception:
        pass


def get_job(conn: sqlite3.Connection, job_id: str) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM scan_jobs WHERE id=?", (job_id,))
    return cur.fetchone()


### DSP job helpers
def create_dsp_job(conn: sqlite3.Connection, job_id: str, params: str, db_path: Optional[str], total: int = 0):
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO dsp_jobs (id, status, params, db_path, processed, total, cancel_requested) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (job_id, 'running', params, db_path, 0, total, 0),
    )
    conn.commit()


def set_dsp_progress(conn: sqlite3.Connection, job_id: str, processed: int, total: int):
    cur = conn.cursor()
    cur.execute("UPDATE dsp_jobs SET processed=?, total=? WHERE id=?", (processed, total, job_id))
    conn.commit()


def set_dsp_result(conn: sqlite3.Connection, job_id: str, result: dict):
    cur = conn.cursor()
    cur.execute("UPDATE dsp_jobs SET status=?, result=?, finished_at=datetime('now') WHERE id=?", ('done', json.dumps(result), job_id))
    conn.commit()


def set_dsp_failed(conn: sqlite3.Connection, job_id: str, error: str):
    cur = conn.cursor()
    cur.execute("UPDATE dsp_jobs SET status=?, error=?, finished_at=datetime('now') WHERE id=?", ('failed', error, job_id))
    conn.commit()


def mark_dsp_cancel_requested(conn: sqlite3.Connection, job_id: str):
    cur = conn.cursor()
    cur.execute("UPDATE dsp_jobs SET cancel_requested=1 WHERE id=?", (job_id,))
    conn.commit()


def get_dsp_job(conn: sqlite3.Connection, job_id: str) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM dsp_jobs WHERE id=?", (job_id,))
    return cur.fetchone()


def list_dsp_jobs(conn: sqlite3.Connection, limit: int = 100, offset: int = 0):
    cur = conn.cursor()
    cur.execute('SELECT id, status, params, db_path, processed, total, started_at, finished_at, cancel_requested FROM dsp_jobs ORDER BY started_at DESC LIMIT ? OFFSET ?', (limit, offset))
    return [dict(r) for r in cur.fetchall()]


def upsert_sample(conn: sqlite3.Connection, sample: dict):
        """Insert or update a sample row. sample is a dict matching table columns."""
        sql = """
        INSERT INTO samples (id, full_path, rel_path, root_dir, filename, ext, size_bytes, bpm, duration, sample_rate, channels, content_hash, bpm_hint, key_hint, key_detected, instrument_hint, fuzzy_score, parsed_tokens)
        VALUES (:id, :full_path, :rel_path, :root_dir, :filename, :ext, :size_bytes, :bpm, :duration, :sample_rate, :channels, :content_hash, :bpm_hint, :key_hint, :key_detected, :instrument_hint, :fuzzy_score, :parsed_tokens)
        ON CONFLICT(id) DO UPDATE SET
            full_path=excluded.full_path,
            rel_path=excluded.rel_path,
            root_dir=excluded.root_dir,
            filename=excluded.filename,
            ext=excluded.ext,
            size_bytes=excluded.size_bytes,
            bpm=excluded.bpm,
            duration=excluded.duration,
            sample_rate=excluded.sample_rate,
            channels=excluded.channels,
            content_hash=excluded.content_hash,
            bpm_hint=excluded.bpm_hint,
            key_hint=excluded.key_hint,
            key_detected=excluded.key_detected,
            instrument_hint=excluded.instrument_hint,
            fuzzy_score=excluded.fuzzy_score,
            parsed_tokens=excluded.parsed_tokens,
            updated_at=CURRENT_TIMESTAMP;
        """
        # ensure all expected params are present (use None as default)
        params = {
            'id': sample.get('id'),
            'full_path': sample.get('full_path'),
            'rel_path': sample.get('rel_path'),
            'root_dir': sample.get('root_dir'),
            'filename': sample.get('filename'),
            'ext': sample.get('ext'),
            'size_bytes': sample.get('size_bytes'),
            'bpm': sample.get('bpm'),
            'key_detected': sample.get('key_detected'),
            'duration': sample.get('duration'),
            'sample_rate': sample.get('sample_rate'),
            'channels': sample.get('channels'),
            'content_hash': sample.get('content_hash'),
            'bpm_hint': sample.get('bpm_hint'),
            'key_hint': sample.get('key_hint'),
            'instrument_hint': sample.get('instrument_hint'),
            'fuzzy_score': sample.get('fuzzy_score'),
            'parsed_tokens': sample.get('parsed_tokens'),
        }
        conn.execute(sql, params)


def upsert_autotag(conn: sqlite3.Connection, sample_id: str, tag: str, confidence: float):
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO autotags (sample_id, tag, confidence) VALUES (?, ?, ?)",
        (sample_id, tag, confidence),
    )
    conn.commit()


def get_autotags_for_sample(conn: sqlite3.Connection, sample_id: str):
    cur = conn.cursor()
    cur.execute("SELECT tag, confidence, created_at FROM autotags WHERE sample_id=? ORDER BY confidence DESC", (sample_id,))
    return cur.fetchall()


def get_unprocessed_samples(conn: sqlite3.Connection, limit: int = 500):
    cur = conn.cursor()
    cur.execute("SELECT id, full_path FROM samples WHERE content_hash IS NULL LIMIT ?", (limit,))
    return cur.fetchall()


def update_sample_metadata(conn: sqlite3.Connection, sample_id: str, metadata: dict):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE samples SET bpm=?, duration=?, sample_rate=?, channels=?, content_hash=?, key_detected=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
        """,
        (metadata.get('bpm'), metadata.get('duration'), metadata.get('sample_rate'), metadata.get('channels'), metadata.get('content_hash'), metadata.get('key_detected'), sample_id),
    )
    conn.commit()


if __name__ == "__main__":
    c = get_conn()
    init_db(c)
    print(f"Initialized DB at {DB_PATH}")
