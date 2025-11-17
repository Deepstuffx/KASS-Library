import tempfile
from pathlib import Path
import sqlite3
from app.backend.scanner import scan_roots
from app.backend import db


def make_file(path: Path, size: int = 1024):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'0' * size)


def test_scan_inserts_rows(tmp_path):
    # create temp root with some files
    root = tmp_path / 'pack'
    f1 = root / 'Kick_01_128bpm.wav'
    f2 = root / 'Snare-140.wav'
    make_file(f1)
    make_file(f2)

    db_file = tmp_path / 'test.db'
    res = scan_roots([str(root)], db_path=str(db_file), batch_size=1)
    assert res['scanned'] >= 2
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM samples")
    count = cur.fetchone()[0]
    assert count >= 2
    conn.close()
