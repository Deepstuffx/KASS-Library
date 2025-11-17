import sqlite3
from app.backend import db
import tempfile


def test_init_db_creates_tables(tmp_path):
    fn = tmp_path / "test_kass.db"
    conn = sqlite3.connect(str(fn))
    db.init_db(conn)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='samples'")
    row = cur.fetchone()
    assert row is not None
    conn.close()
