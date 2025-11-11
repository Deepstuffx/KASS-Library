"""Simple CLI wrapper exposing the original script behavior programmatically."""
from __future__ import annotations
import argparse
from pathlib import Path
from .core import iter_media, Job, process, DB, ensure_base_structure
from concurrent.futures import ThreadPoolExecutor, as_completed


def main():
    ap = argparse.ArgumentParser(description='Organizer CLI')
    ap.add_argument('src')
    ap.add_argument('dest')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--tag-source', action='store_true')
    ap.add_argument('--deep', action='store_true', help='Enable deep audio feature analysis (slower)')
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    src = Path(args.src).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    if not src.is_dir():
        print('Source does not exist:', src); return
    dest.mkdir(parents=True, exist_ok=True)
    ensure_base_structure(dest)
    db = DB(dest / '.organizer_state.sqlite')
    files = list(iter_media(src))
    jobs = []
    for f in files:
        try:
            rel = f.relative_to(src)
            rel_pack = rel.parts[0] if len(rel.parts)>0 else ''
        except Exception:
            rel_pack = ''
        jobs.append(Job(src=f, rel_pack=rel_pack))
    success=skipped=failed=0
    with ThreadPoolExecutor(max_workers=max(1,min(args.workers,8))) as ex:
        futs = {ex.submit(process,j,dest,db,args.dry_run,args.tag_source, deep=args.deep): j for j in jobs}
        for fut in as_completed(futs):
            ok,msg = fut.result()
            if ok:
                if msg.startswith('skip duplicate'):
                    skipped += 1
                else:
                    success += 1
            else:
                failed += 1
    db.close()
    print(f'Copied: {success} | Skipped: {skipped} | Failed: {failed} | Scanned: {len(jobs)}')

if __name__ == '__main__':
    main()
