"""Pull every call of one CallKaro agent in a window, normalise, write JSON lines.

usage:
  CK_ACCOUNT=<account> python -I pull_calls.py --config funnel.json --out raw/calls.jsonl [--cku PATH] [--workers 5]
  python -I pull_calls.py --config funnel.json --out raw/calls.jsonl --from-jsonl old/raw.jsonl   # no cku call

Uses `cku calls list --agent <id> --start <s> --end <e> --limit 100 --page N --meta --json`.
The 100-row cap is per page; pages are fetched in parallel, failed pages are retried, rows are de-duplicated by _id.
--from-jsonl re-reads an earlier pull instead of calling cku (applies the same window and version filter).
Logs totalDocs, the page count and any failed pages to <out>.log. Never stores or prints credentials.
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funnel  # noqa: E402  (shared rule engine, used for the success rule)

SCRIPT_RANGES = [('hi', 0x0900, 0x097F), ('bn', 0x0980, 0x09FF), ('gu', 0x0A80, 0x0AFF), ('ta', 0x0B80, 0x0BFF),
                 ('te', 0x0C00, 0x0C7F), ('kn', 0x0C80, 0x0CFF), ('ml', 0x0D00, 0x0D7F)]
GREET = {'hello', 'hi', 'haan', 'ji', 'ok', 'okay', 'han', 'hanji', 'haanji', 'hello?', 'haan ji', 'ji haan'}
VM = re.compile(r'voicemail|leave a message|after the tone|call screening|google assistant|not available right now', re.I)


def script_of(text):
    counts = {}
    for ch in text:
        if ch.isascii():
            if ch.isalpha():
                counts['en'] = counts.get('en', 0) + 1
            continue
        for lang, lo, hi in SCRIPT_RANGES:
            if lo <= ord(ch) <= hi:
                counts[lang] = counts.get(lang, 0) + 1
                break
    return max(counts, key=counts.get) if counts else 'none'


def text_of(m):
    x = m.get('content')
    if isinstance(x, list):
        return ' '.join(i for i in x if isinstance(i, str))
    return x or ''


def switched(name, args):
    if name != 'switch_capability':
        return None
    try:
        a = json.loads(args) if isinstance(args, str) else (args or {})
    except ValueError:
        return None
    return a.get('capability') or a.get('name') or a.get('capability_name')


def normalise(c, cfg):
    v = c.get('versionId')
    transcript, caps, outs, fns = [], [], [], []
    for m in c.get('chat_history') or []:
        kind = m.get('type')
        if kind == 'message':
            s = text_of(m).strip()
            if s:
                model = (m.get('metrics') or {}).get('llm_metadata', {}).get('model_name') if m.get('role') != 'user' else None
                transcript.append(['u' if m.get('role') == 'user' else 'a', s, model])
        elif kind == 'function_call':
            name = m.get('name') or ''
            fns.append(name)
            cap = switched(name, m.get('arguments'))
            if cap:
                caps.append(cap)
            transcript.append(['f', name, None])
        elif kind == 'function_call_output':
            outs.append({'name': m.get('name') or '', 'output': str(m.get('output') or '')[:1000]})
    fns = [f.get('name') for f in (c.get('functions_called') or [])] + fns
    md = c.get('call_metadata') or {}
    to = re.sub(r'\D', '', str(c.get('to') or md.get('phone') or ''))
    dur = c.get('call_duration') or 0
    hang = c.get('hangup_reason') or ''
    cust = [t for role, t, _ in transcript if role == 'u']
    real = [t for t in cust if len(re.sub(r'[\W_]', '', t)) >= 6 and t.strip().lower().rstrip('.!?,') not in GREET]
    rec = {
        'id': c.get('_id'), 'at': str(c.get('createdAt') or '')[:19].replace('T', ' '), 'duration': dur, 'hangup_reason': hang,
        'disposition_reason': (c.get('disposition_reason') or '')[:400],
        'version': v.get('versionName') if isinstance(v, dict) else v,
        'version_id': v.get('_id') if isinstance(v, dict) else v,
        'lead': str(md.get('lead_id') or ''), 'city': md.get('lead_information_city') or md.get('city') or '',
        'insp_city': md.get('lead_information_inspection_city') or '', 'phone_last4': to[-4:],
        'recording_url': c.get('recordingUrl') or '', 'sch_id': c.get('sch_id') or '', 'batch_id': c.get('batchId') or '',
        'credits': c.get('total_credits') or 0, 'latency': c.get('avg_total_latency'),
        'post_call': c.get('post_call') or {}, 'metadata': md, 'functions': fns, 'function_outputs': outs,
        'capabilities_switched': caps, 'transcript': transcript,
        'opening_lang': next((script_of(t) for role, t, _ in transcript if role == 'a' and len(t.split()) >= 3), 'none'),
        'customer_lang': script_of(' '.join(cust)),
    }
    rec['_real_customer_turns'] = len(real)
    rec['human'] = False
    if dur > 0 and not re.search('VOICEMAIL', hang, re.I) and len(real) >= 2 and not any(VM.search(t) for t in cust):
        rec['human'] = True
    if cfg.get('success') and funnel.test(rec, cfg['success']):
        rec['human'] = True   # a closed deal is human by definition
    return rec


def window_utc(cfg, which):
    w = cfg['window']
    t = dt.datetime.strptime(w[which], '%Y-%m-%d %H:%M')
    return (t - dt.timedelta(hours=w['tz_offset_hours'])).strftime('%Y-%m-%d %H:%M:%S')


def run_page(cku, cfg, page, start, end):
    cmd = [cku, 'calls', 'list', '--agent', cfg['agent_id'], '--start', start, '--end', end,
           '--limit', '100', '--page', str(page), '--meta', '--json']
    for attempt in range(4):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL)
        try:
            d = json.loads(r.stdout[r.stdout.find('{'):])
            return [normalise(c, cfg) for c in d['calls']], d['pagination']
        except Exception:
            time.sleep(3 * (attempt + 1))
    return None, None


def in_window_and_version(recs, cfg):
    off = cfg['window']['tz_offset_hours']
    s, e = funnel.parse_ist(cfg['window']['start_ist']), funnel.parse_ist(cfg['window']['end_ist'])
    out = []
    for r in recs:
        if cfg.get('versions') and r.get('version') not in cfg['versions'] and r.get('version_id') not in cfg['versions']:
            continue
        if s <= funnel.ist_of(r, off) < e:
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--cku', default=shutil.which('cku') or 'cku')
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--from-jsonl')
    a = ap.parse_args()
    cfg = json.load(io.open(a.config, encoding='utf-8'))
    log = io.open(a.out + '.log', 'w', encoding='utf-8')
    if a.from_jsonl:
        recs = [json.loads(x) for x in io.open(a.from_jsonl, encoding='utf-8') if x.strip()]
        seen = {r['id']: r for r in in_window_and_version(recs, cfg)}
        log.write(f'from {a.from_jsonl}: {len(recs)} rows, {len(seen)} in window\n')
    else:
        if not os.environ.get('CK_ACCOUNT'):
            sys.exit('CK_ACCOUNT is not set. Set it to the CallKaro account name, then re-run.')
        start, end = window_utc(cfg, 'start_ist'), window_utc(cfg, 'end_ist')
        rows, pg = run_page(a.cku, cfg, 1, start, end)
        if rows is None:
            sys.exit('page 1 failed; check cku login for CK_ACCOUNT')
        n = pg['totalPages']
        log.write(f"totalDocs={pg['totalDocs']} pages={n} window_utc={start}..{end}\n")
        with ThreadPoolExecutor(a.workers) as ex:
            rest = list(ex.map(lambda p: run_page(a.cku, cfg, p, start, end), range(2, n + 1)))
        for p in [i + 2 for i, (r, _) in enumerate(rest) if r is None]:
            r, _ = run_page(a.cku, cfg, p, start, end)
            if r is not None:
                rest[p - 2] = (r, None)
        failed = [i + 2 for i, (r, _) in enumerate(rest) if r is None]
        seen = {}
        for r in rows + [x for r, _ in rest if r for x in r]:
            seen[r['id']] = r
        log.write(f'failed pages {failed}\n')
        if failed:
            print('WARNING failed pages:', failed)
    with io.open(a.out, 'w', encoding='utf-8') as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    log.write(f'saved {len(seen)} unique\nDONE\n')
    log.close()
    print(f'saved {len(seen)} calls to {a.out}')


if __name__ == '__main__':
    main()
