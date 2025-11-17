import sqlite3
import threading
import time
import uuid
from pathlib import Path

from app.backend import main as backend_main
from app.backend import db as backend_db


def make_file(path: Path, size: int = 1024):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'0' * size)


def test_job_persistence_and_cancel(tmp_path):
    root = tmp_path / 'pack'
    total = 200
    for i in range(total):
        make_file(root / f'sample_{i:04d}.wav')

    db_file = tmp_path / 'jobs.db'
    job_id = str(uuid.uuid4())

    # start background job runner (which creates the job row itself)
    t = threading.Thread(target=backend_main._run_scan_job, args=(job_id, [str(root)], str(db_file), 10, 1), daemon=True)
    t.start()

    # wait for job row to be created
    created = False
    for _ in range(100):
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        try:
            cur.execute("SELECT cancel_requested FROM scan_jobs WHERE id=?", (job_id,))
            r = cur.fetchone()
            if r is not None:
                created = True
                break
        except sqlite3.OperationalError:
            # table might not exist yet
            pass
        finally:
            conn.close()
        time.sleep(0.02)

    assert created, "Job row was not created"

    # request cancellation
    conn = backend_db.get_conn(str(db_file))
    try:
        backend_db.mark_job_cancel_requested(conn, job_id)
    finally:
        conn.close()

    # wait for thread to finish
    t.join(timeout=10)
    assert not t.is_alive()

    # verify job row shows cancellation requested and has a result
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT cancel_requested, status, result FROM scan_jobs WHERE id=?", (job_id,))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    cancel_flag, status, result_json = row
    assert cancel_flag == 1
    assert status in ('done', 'failed')
    assert result_json is not None

    import json
    result = json.loads(result_json)
    # scan should have stopped early due to cancel
    assert result.get('scanned', 0) < total
