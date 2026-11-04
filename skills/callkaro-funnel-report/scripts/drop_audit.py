"""LLM drop-reason audit. One call per dropped lead, at the last call that passed the stage before the drop.

usage:
  GW_KEY=<key> python -I drop_audit.py --config funnel.json --calls raw/calls.jsonl --out out/drop_labels.json \
      [--sample 30] [--workers 8] [--model NAME] [--gateway URL]

A lead dropped at stage k when it passed stage k-1 on some call, never passed stage k, and did not close a deal.
The reason key must come from drop_reasons.reasons_per_stage[<stage key>]; anything else becomes "other".
The gateway key is read ONLY from the env var named by drop_reasons.llm.key_env (default GW_KEY). Never written
to disk or printed. Gateway replies may be plain JSON or SSE ("data: ..." lines); both are handled.
Failed calls are written with reason "ERROR" and excluded from metrics. Run --sample first and check by hand.
"""
import argparse
import collections
import concurrent.futures as cf
import io
import json
import os
import random
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funnel  # noqa: E402

FIXED_SIDES = ('bot', 'customer', 'platform')


def transcript_text(rec, limit=8000):
    lines = []
    for role, text, *_ in rec.get('transcript') or []:
        if role == 'f':
            lines.append(f'[tool {text}]')
        else:
            lines.append(('CUSTOMER: ' if role == 'u' else 'BOT: ') + str(text))
    return '\n'.join(lines)[-limit:]


def build_prompt(cfg, stage):
    dr = cfg['drop_reasons']
    reasons = dict(dr['reasons_per_stage'].get(stage, {}))
    if 'other' not in reasons:
        reasons['other'] = 'None of the above; explain in evidence'
    label = next(s['label'] for s in cfg['stages'] if s['key'] == stage)
    sysp = (f"You audit why an outbound voice-agent call for '{cfg['name']}' did not progress past the stage: {label}. "
            'Pick exactly ONE reason from the list. Reply with JSON only, no prose: '
            '{"reason": "<key>", "side": "bot|customer|platform", "evidence": "<short exact quote copied from the transcript>", '
            '"bot_mistake": "<one short sentence if the bot did something wrong, else empty>", '
            '"customer_expected_price": <number in rupees or null>, "competitor": "<name or empty>", "callback_requested": true|false}.\n'
            'Side: bot = the agent caused the drop; customer = the customer decided; platform = audio, line or system fault.\n'
            + '\n'.join(f'- {k}: {v}' for k, v in reasons.items()))
    return sysp, set(reasons)


def parse_reply(raw):
    raw = raw.strip()
    if raw.startswith('data:') or '\ndata:' in raw:
        out = ''.join((json.loads(l[5:]).get('choices') or [{}])[0].get('delta', {}).get('content') or ''
                      for l in raw.splitlines()
                      if l.startswith('data:') and l[5:].strip() not in ('', '[DONE]'))
    else:
        out = json.JSONDecoder().raw_decode(raw)[0]['choices'][0]['message']['content'] or ''
    i = out.index('{')
    return json.JSONDecoder().raw_decode(out[i:])[0]


def call_llm(gw, model, key, sysp, text, timeout=180):
    body = json.dumps({'model': model, 'temperature': 0, 'max_tokens': 800,
                       'messages': [{'role': 'system', 'content': sysp}, {'role': 'user', 'content': text}]}).encode()
    req = urllib.request.Request(gw, body, {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key,
                                            'User-Agent': 'Mozilla/5.0'})
    return parse_reply(urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'replace'))


def label_one(cfg, gw, model, key, job, retries=3):
    stage, lead, rec = job
    sysp, valid = build_prompt(cfg, stage)
    err = ''
    for attempt in range(retries):
        try:
            d = call_llm(gw, model, key, sysp, transcript_text(rec))
            reason = d.get('reason') if d.get('reason') in valid else 'other'
            side = d.get('side') if d.get('side') in FIXED_SIDES else 'platform'
            return {'stage': stage, 'lead': lead, 'call': rec['id'], 'version': rec.get('version'), 'reason': reason,
                    'reason_raw': d.get('reason'), 'side': side, 'evidence': str(d.get('evidence') or '')[:300],
                    'bot_mistake': str(d.get('bot_mistake') or '')[:300],
                    'customer_expected_price': d.get('customer_expected_price'),
                    'competitor': str(d.get('competitor') or '')[:60], 'callback_requested': bool(d.get('callback_requested')),
                    'model': model}
        except Exception as e:  # network, bad JSON, bad gateway reply: retry with backoff
            err = f'{type(e).__name__}: {str(e)[:160]}'
            time.sleep(2 * (attempt + 1))
    return {'stage': stage, 'lead': lead, 'call': rec['id'], 'version': rec.get('version'), 'reason': 'ERROR', 'error': err}


def jobs_from(cfg, recs):
    leads = funnel.analyse(cfg, recs)
    stages = cfg['stages']
    audited = set(cfg['drop_reasons']['stages_audited'])
    jobs = []
    for lead, x in leads.items():
        if x['agreed']:
            continue
        k = x['level'] + 1          # first stage not passed
        if k >= len(stages) or stages[k]['key'] not in audited:
            continue
        key = stages[k]['key']
        cs = x['calls']
        # last call that passed the stage before the drop; fall back to last call
        cand = [c for c in cs if c['_pass'][x['level']]] if x['level'] >= 0 else []
        if not cand:
            cand = cs
        jobs.append((key, lead, cand[-1]))
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--calls', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--model')
    ap.add_argument('--gateway')
    a = ap.parse_args()
    cfg = json.load(io.open(a.config, encoding='utf-8'))
    llm = cfg['drop_reasons']['llm']
    gw = (a.gateway or llm['gateway']).rstrip('/') + '/chat/completions'
    model = a.model or llm['model']
    key = os.environ.get(llm.get('key_env', 'GW_KEY'), '')
    if not key and 'localhost' not in gw and '127.0.0.1' not in gw:
        sys.exit(f"{llm.get('key_env', 'GW_KEY')} is not set")
    recs = funnel.in_window([json.loads(x) for x in io.open(a.calls, encoding='utf-8') if x.strip()], cfg)
    jobs = jobs_from(cfg, recs)
    if a.sample:
        random.seed(7)
        jobs = random.sample(jobs, min(a.sample, len(jobs)))
    print('jobs', len(jobs), collections.Counter(j[0] for j in jobs))
    out = []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        out = list(ex.map(lambda j: label_one(cfg, gw, model, key, j), jobs))
    io.open(a.out, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    ok = [x for x in out if x['reason'] != 'ERROR']
    print('labelled', len(ok), 'errors', len(out) - len(ok), dict(collections.Counter(x['reason'] for x in ok)))


if __name__ == '__main__':
    main()
