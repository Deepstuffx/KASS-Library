from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import threading
import uuid
import time

from .scanner import scan_roots
from .db import get_conn, init_db, create_job, set_job_result, set_job_failed, mark_job_cancel_requested, get_job
from .db import create_dsp_job, set_dsp_progress, set_dsp_result, set_dsp_failed, mark_dsp_cancel_requested, get_dsp_job, list_dsp_jobs
import sqlite3


app = FastAPI(title="KASS Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory job store for scan jobs (id -> info)
_jobs = {}
_jobs_lock = threading.Lock()


class ScanRequest(BaseModel):
    roots: List[str]
    db_path: Optional[str] = None
    batch_size: Optional[int] = 500
    min_size: Optional[int] = 512


@app.get("/")
def root():
    return {"name": "KASS Backend", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


def _run_scan_job(job_id: str, roots: List[str], db_path: Optional[str], batch_size: int, min_size: int):
    conn = get_conn(db_path) if db_path else get_conn()
    # ensure schema exists
    init_db(conn)
    try:
        # persist job row
        create_job(conn, job_id, ','.join(roots), db_path, batch_size, min_size)
        # small pause to allow callers (tests or APIs) to request cancellation
        # before heavy scanning starts; keeps behavior responsive for in-process control
        try:
            import time as _time
            _time.sleep(0.02)
        except Exception:
            pass
        res = scan_roots(roots, db_path=db_path, batch_size=batch_size, min_size=min_size, job_id=job_id)
        set_job_result(conn, job_id, res)
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['status'] = 'done'
                _jobs[job_id]['result'] = res
                _jobs[job_id]['finished_at'] = time.time()
    except Exception as e:
        set_job_failed(conn, job_id, str(e))
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['status'] = 'failed'
                _jobs[job_id]['error'] = str(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.post('/scan')
def start_scan(req: ScanRequest, background: BackgroundTasks):
    job_id = str(uuid.uuid4())
    job = {
        'status': 'running',
        'started_at': time.time(),
        'result': None,
        'error': None,
    }
    with _jobs_lock:
        _jobs[job_id] = job
    # persist job immediately
    conn = get_conn(req.db_path) if req.db_path else get_conn()
    init_db(conn)
    try:
        create_job(conn, job_id, ','.join(req.roots), req.db_path, req.batch_size, req.min_size)
    finally:
        conn.close()

    # run in background thread to avoid blocking the server
    t = threading.Thread(target=_run_scan_job, args=(job_id, req.roots, req.db_path, req.batch_size, req.min_size), daemon=True)
    t.start()
    return {'job_id': job_id}


@app.post('/scan/dryrun')
def scan_dryrun(req: ScanRequest):
    """Run a synchronous scan in dry-run mode and return planned moves summary."""
    # call scan_roots with dry_run=True and return the summary directly
    try:
        res = scan_roots(req.roots, db_path=req.db_path, batch_size=req.batch_size, min_size=req.min_size, dry_run=True)
        return res
    except Exception as e:
        return {'error': str(e)}, 500
@app.post('/scan/{job_id}/cancel')
def cancel_scan(job_id: str, db_path: Optional[str] = None):
    conn = get_conn(db_path) if db_path else get_conn()
    try:
        r = get_job(conn, job_id)
        if not r:
            return {'error': 'not found'}, 404
        mark_job_cancel_requested(conn, job_id)
        # also update in-memory job store if present for immediate visibility
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]['cancel_requested'] = 1
        return {'status': 'cancel_requested'}
    finally:
        conn.close()


@app.get('/scan/{job_id}')
def scan_status(job_id: str):
    # Prefer DB-backed job if available
    conn = get_conn()
    try:
        try:
            r = get_job(conn, job_id)
        except sqlite3.OperationalError:
            r = None
        if r:
            # convert sqlite3.Row to dict
            row = dict(r)
            return row
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # fallback to in-memory job store
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return {'error': 'job not found'}, 404
    return job


@app.get('/scans')
def list_scans(limit: int = 100, offset: int = 0, db_path: Optional[str] = None):
    conn = get_conn(db_path) if db_path else get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, status, roots, started_at, finished_at, cancel_requested FROM scan_jobs ORDER BY started_at DESC LIMIT ? OFFSET ?', (limit, offset))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {'rows': rows}


@app.post('/dsp')
def start_dsp(background: BackgroundTasks, db_path: Optional[str] = None, limit: int = 500):
    """Start a DSP job to process unprocessed samples."""
    job_id = str(uuid.uuid4())
    # persist job row
    conn = get_conn(db_path) if db_path else get_conn()
    init_db(conn)
    try:
        create_dsp_job(conn, job_id, params='{}', db_path=db_path, total=0)
    finally:
        conn.close()

    # run dsp in background thread
    def _runner(jid, dbp, lim):
        try:
            import app.backend.dsp_runner as runner
            n = runner.run_once(db_path=dbp, limit=lim, job_id=jid)
        except Exception as e:
            conn2 = get_conn(dbp) if dbp else get_conn()
            try:
                set_dsp_failed(conn2, jid, str(e))
            finally:
                conn2.close()

    t = threading.Thread(target=_runner, args=(job_id, db_path, limit), daemon=True)
    t.start()
    return {'job_id': job_id}


@app.get('/dsp/{job_id}')
def dsp_status(job_id: str, db_path: Optional[str] = None):
    conn = get_conn(db_path) if db_path else get_conn()
    try:
        try:
            j = get_dsp_job(conn, job_id)
        except sqlite3.OperationalError:
            j = None
        if j:
            return dict(j)
    finally:
        conn.close()
    return {'error': 'job not found'}, 404


@app.post('/dsp/{job_id}/cancel')
def cancel_dsp(job_id: str, db_path: Optional[str] = None):
    conn = get_conn(db_path) if db_path else get_conn()
    try:
        r = get_dsp_job(conn, job_id)
        if not r:
            return {'error': 'not found'}, 404
        mark_dsp_cancel_requested(conn, job_id)
        return {'status': 'cancel_requested'}
    finally:
        conn.close()


@app.get('/samples')
def list_samples(
    limit: int = 100,
    offset: int = 0,
    instrument: Optional[str] = None,
    sort_by: Optional[str] = 'added_at',
    sort_dir: Optional[str] = 'desc',
    db_path: Optional[str] = None,
):
    """List samples with optional sorting. `sort_by` is whitelisted to prevent SQL injection."""
    allowed = {'added_at', 'filename', 'size_bytes', 'bpm', 'sample_rate', 'fuzzy_score', 'instrument_hint', 'added_at'}
    sort_col = sort_by if sort_by in allowed else 'added_at'
    sort_direction = 'ASC' if (sort_dir or '').lower() == 'asc' else 'DESC'

    conn = get_conn(db_path) if db_path else get_conn()
    cur = conn.cursor()
    sql = 'SELECT id, full_path, filename, ext, size_bytes, bpm, sample_rate, channels, instrument_hint, fuzzy_score, added_at FROM samples'
    where = []
    params = {}
    if instrument:
        where.append('instrument_hint = :instrument')
        params['instrument'] = instrument
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += f' ORDER BY {sort_col} {sort_direction} LIMIT :limit OFFSET :offset'
    params['limit'] = limit
    params['offset'] = offset
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {'rows': rows}


@app.get('/samples/{sample_id}')
def get_sample(sample_id: str, db_path: Optional[str] = None):
    conn = get_conn(db_path) if db_path else get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM samples WHERE id = :id', {'id': sample_id})
    r = cur.fetchone()
    conn.close()
    if not r:
        return {'error': 'not found'}, 404
    return dict(r)
