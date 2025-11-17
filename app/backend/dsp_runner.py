import sqlite3
import time
from app.backend.db import get_conn, init_db, get_unprocessed_samples
import app.backend.dsp as dsp
import app.backend.db as dbmod


def run_once(db_path: str = None, limit: int = 500, job_id: str | None = None):
    conn = get_conn(db_path) if db_path else get_conn()
    init_db(conn)
    rows = get_unprocessed_samples(conn, limit=limit)
    processed = 0
    total = len(rows)

    # persist dsp job row if job_id provided
    if job_id:
        create_dsp = dbmod.create_dsp_job
        create_dsp(conn, job_id, params='{}', db_path=db_path, total=total)

    for r in rows:
        # check cancel
        if job_id:
            j = dbmod.get_dsp_job(conn, job_id)
            if j and j['cancel_requested'] == 1:
                break
        try:
            dsp.process_sample(conn, r, dbmod)
            processed += 1
            if job_id:
                dbmod.set_dsp_progress(conn, job_id, processed, total)
        except Exception as e:
            print('error processing', r[0], e)
    # finalize
    if job_id:
        dbmod.set_dsp_result(conn, job_id, {'processed': processed, 'total': total})
    conn.close()
    return processed


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=None)
    parser.add_argument('--limit', type=int, default=500)
    args = parser.parse_args()
    print('processing...')
    n = run_once(db_path=args.db, limit=args.limit)
    print('processed', n)
