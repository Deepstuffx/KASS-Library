"""Simple CLI to run the scanner against one or more root folders.

Usage:
    python -m app.backend.scan_runner /path/to/folder --db app/backend/kass.db
"""

from __future__ import annotations

from .scanner import scan_roots
from pathlib import Path
import tempfile
import shutil
import logging


def run() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Run a quick scan')
    parser.add_argument('roots', nargs='+', help='One or more root folders to scan')
    parser.add_argument('--db', default=None, help='Optional path to SQLite DB')
    parser.add_argument('--batch-size', type=int, default=500, help='Number of samples to upsert per transaction')
    parser.add_argument('--min-size', type=int, default=512, help='Minimum file size (bytes) to consider')
    parser.add_argument('--exts', default=None, help='Comma-separated list of extensions to include (e.g. .wav,.flac)')
    parser.add_argument('--job-id', default=None, help='Optional job id to record progress/cancellation')
    parser.add_argument('--dry-run', action='store_true', help='Run scan without modifying your real DB (uses temporary DB)')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format='%(asctime)s %(levelname)s %(message)s')

    db_path = args.db
    temp_db = None
    if args.dry_run:
        # create a temporary DB file and remove it afterwards
        temp_dir = tempfile.mkdtemp(prefix='kass-dryrun-')
        temp_db = str(Path(temp_dir) / 'kass_dryrun.db')
        db_path = temp_db
        logging.info('Running in dry-run mode, temporary DB at %s', db_path)

    exts = None
    if args.exts:
        exts = [e.strip() for e in args.exts.split(',') if e.strip()]

    result = scan_roots(args.roots, db_path=db_path, batch_size=args.batch_size, min_size=args.min_size, exts=exts, job_id=args.job_id)
    print('Scan result:', result)

    if temp_db:
        # cleanup temporary DB
        try:
            shutil.rmtree(Path(temp_db).parent)
            logging.info('Removed temporary DB at %s', temp_db)
        except Exception:
            logging.warning('Failed to remove temporary DB at %s', temp_db)


if __name__ == '__main__':
    run()
