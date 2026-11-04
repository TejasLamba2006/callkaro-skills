"""Resumable pull of scheduleCall.call_language for every schedule behind the window's calls.

usage:
  CK_ACCOUNT=<account> python -I sch_pull.py --calls raw/calls.jsonl --config funnel.json --out raw/sch_lang.json [--cku PATH]

Runs `cku scheduled get <sch_id> --json` per schedule (thread pool). Output keeps lang, batch, status, lead, city.
Re-running skips schedules already in --out (errors are retried). Writes a progress file every 200 items.
Use it to find scheduler language mistagging: schedule says Hindi, customer spoke English, etc.
"""
import argparse
import concurrent.futures as cf
import io
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funnel  # noqa: E402


def get(cku, sid):
    r = subprocess.run([cku, 'scheduled', 'get', sid, '--json'], capture_output=True, text=True, encoding='utf-8',
                       errors='replace', stdin=subprocess.DEVNULL)
    i = r.stdout.find('{')
    if r.returncode or i < 0:
        return {'err': (r.stdout + r.stderr)[-200:]}
    sc = json.loads(r.stdout[i:]).get('scheduleCall') or {}
    md = sc.get('metadata') or {}
    return {'lang': sc.get('call_language'), 'batch': sc.get('batch_id'), 'status': sc.get('status'),
            'lead': str(md.get('lead_id') or ''), 'city': md.get('lead_information_city'),
            'created': sc.get('createdAt')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--calls', required=True)
    ap.add_argument('--config', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--cku', default=shutil.which('cku') or 'cku')
    ap.add_argument('--workers', type=int, default=12)
    a = ap.parse_args()
    if not os.environ.get('CK_ACCOUNT'):
        sys.exit('CK_ACCOUNT is not set.')
    cfg = json.load(io.open(a.config, encoding='utf-8'))
    recs = funnel.in_window([json.loads(x) for x in io.open(a.calls, encoding='utf-8') if x.strip()], cfg)
    sids = sorted({r['sch_id'] for r in recs if r.get('sch_id')})
    done = json.load(io.open(a.out, encoding='utf-8')) if os.path.exists(a.out) else {}
    todo = [s for s in sids if s not in done or 'err' in done[s]]
    print('schedules', len(sids), 'todo', len(todo))
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, (sid, res) in enumerate(zip(todo, ex.map(lambda s: get(a.cku, s), todo)), 1):
            done[sid] = res
            if i % 200 == 0:
                json.dump(done, io.open(a.out, 'w', encoding='utf-8'))
    json.dump(done, io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('errors', sum('err' in v for v in done.values()), 'saved', len(done), 'to', a.out)


if __name__ == '__main__':
    main()
