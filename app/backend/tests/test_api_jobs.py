import json
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.backend.main import app
from app.backend import db as backend_db


def make_file(path: Path, size: int = 1024):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'0' * size)


def test_scan_api_persistence_and_cancel(tmp_path):
    root = tmp_path / 'pack'
    total = 200
    for i in range(total):
        make_file(root / f'sample_{i:04d}.wav')

    db_file = tmp_path / 'api_jobs.db'
    client = TestClient(app)

    # start scan via API (persisted to the provided db_path)
    resp = client.post('/scan', json={
        'roots': [str(root)],
        'db_path': str(db_file),
        'batch_size': 1,
        'min_size': 1,
    })
    assert resp.status_code == 200
    job_id = resp.json()['job_id']

    # wait for job row to be created in the DB
    created = False
    for _ in range(200):
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        try:
            cur.execute("SELECT cancel_requested FROM scan_jobs WHERE id=?", (job_id,))
            r = cur.fetchone()
            if r is not None:
                created = True
                break
        except sqlite3.OperationalError:
            # table may not be created yet
            pass
        finally:
            conn.close()
        time.sleep(0.02)

    assert created, "job row was not created"

    # request cancellation through API
    resp = client.post(f'/scan/{job_id}/cancel', params={'db_path': str(db_file)})
    assert resp.status_code == 200

    # poll the job until it finishes
    final = None
    for _ in range(500):
        r = client.get(f'/scan/{job_id}')
        if r.status_code == 200:
            j = r.json()
            status = j.get('status')
            if status in ('done', 'failed'):
                final = j
                break
        time.sleep(0.02)

    assert final is not None, "job did not finish in time"

    # verify cancel flag and result
    assert final.get('cancel_requested', 0) == 1
    assert final.get('result') is not None

    # result is stored as JSON string in the DB
    res_obj = json.loads(final['result']) if isinstance(final['result'], str) else final['result']
    assert res_obj.get('scanned', 0) < total

    # ensure listing endpoint includes the job
    list_resp = client.get('/scans', params={'db_path': str(db_file)})
    assert list_resp.status_code == 200
    rows = list_resp.json().get('rows', [])
    assert any(r.get('id') == job_id for r in rows)
