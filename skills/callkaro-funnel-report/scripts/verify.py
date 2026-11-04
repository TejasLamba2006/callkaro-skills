"""Independent check of a funnel run: recount every stage, check invariants, open the workbook and PDF.

usage:
  python -I verify.py --config funnel.json --calls out/calls_annotated.jsonl --metrics out/metrics.json \
      [--xlsx out/Funnel_Report.xlsx] [--pdf out/Funnel_Report.pdf] [--sample 5]

Exit 0 only if every check passes. The recount uses its own rule evaluator (it does NOT import funnel.py),
so a bug in funnel.py's engine shows up here as a mismatch. Built-in predicates are re-implemented here too.
"""
import argparse
import datetime as dt
import io
import json
import random
import re
import sys

REQ_SHEETS = ['Summary', 'Funnel Drop-offs', 'City Funnel', 'Targets', 'Daily Trend', 'By Version', 'By Opening Language',
              'By Final Stage', 'All Leads', 'All Calls', 'Definitions']


def dig(rec, path):
    cur = rec
    for p in str(path).split('.'):
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur


def ev(rec, rule):
    """Independent evaluator for the same rule grammar as funnel.py."""
    if rule is None:
        return True
    if 'all' in rule:
        return all(ev(rec, r) for r in rule['all'])
    if 'any' in rule:
        return any(ev(rec, r) for r in rule['any'])
    if 'not' in rule:
        return not ev(rec, rule['not'])
    if 'is_human' in rule:
        return bool(rec.get('human')) is bool(rule['is_human'])
    if 'capability_visited' in rule:
        return rule['capability_visited'] in (rec.get('capabilities_switched') or [])
    if 'function_called' in rule:
        return rule['function_called'] in (rec.get('functions') or [])
    if 'transcript_agent_regex' in rule:
        return any(re.search(rule['transcript_agent_regex'], t or '', re.I) for role, t, *_ in rec.get('transcript') or [] if role == 'a')
    if 'transcript_customer_regex' in rule:
        return any(re.search(rule['transcript_customer_regex'], t or '', re.I) for role, t, *_ in rec.get('transcript') or [] if role == 'u')
    if 'function_output_regex' in rule:
        spec = rule['function_output_regex'] if isinstance(rule['function_output_regex'], dict) else {'regex': rule['function_output_regex']}
        outs = [o for o in rec.get('function_outputs') or [] if not spec.get('name') or o.get('name') == spec['name']]
        return any(re.search(spec['regex'], o.get('output', '') or '', re.I) for o in outs)
    f, op, want = rule['field'], rule['op'], rule.get('value')
    v = dig(rec, f)
    if op == 'truthy':
        return bool(v) and str(v).lower() not in ('false', '0', 'none', 'null', '')
    if op == 'regex':
        return bool(re.search(want, str(v or ''), re.I))
    if op == 'contains':
        if isinstance(v, list):
            return any(str(want).lower() == str(x).lower() for x in v)
        return str(want).lower() in str(v or '').lower()
    if op == 'not_contains':
        return not ev(rec, {'field': f, 'op': 'contains', 'value': want})
    if op == 'in':
        return str(v).lower() in [str(w).lower() for w in want]
    if op == '==':
        return (str(v).lower() == want.lower()) if isinstance(want, str) else v == want
    if op == '!=':
        return not ev(rec, {'field': f, 'op': '==', 'value': want})
    try:
        x, y = float(v or 0), float(want)
    except (TypeError, ValueError):
        return False
    return {'>': x > y, '>=': x >= y, '<': x < y, '<=': x <= y}[op]


def in_scope(cfg, r):
    off = cfg['window']['tz_offset_hours']
    s = dt.datetime.strptime(cfg['window']['start_ist'], '%Y-%m-%d %H:%M')
    e = dt.datetime.strptime(cfg['window']['end_ist'], '%Y-%m-%d %H:%M')
    t = dt.datetime.strptime(r['at'][:19].replace('T', ' '), '%Y-%m-%d %H:%M:%S') + dt.timedelta(hours=off)
    if not (s <= t < e):
        return False
    if cfg.get('versions') and r.get('version') not in cfg['versions'] and r.get('version_id') not in cfg['versions']:
        return False
    return not any(ev(r, x) for x in cfg.get('exclude_calls', []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--calls', required=True, help='raw calls.jsonl or calls_annotated.jsonl (both work)')
    ap.add_argument('--metrics', required=True)
    ap.add_argument('--xlsx')
    ap.add_argument('--pdf')
    ap.add_argument('--sample', type=int, default=5)
    a = ap.parse_args()
    cfg = json.load(io.open(a.config, encoding='utf-8'))
    m = json.load(io.open(a.metrics, encoding='utf-8'))
    recs = [json.loads(x) for x in io.open(a.calls, encoding='utf-8') if x.strip()]
    recs = [r for r in recs if in_scope(cfg, r)]
    problems, notes = [], []

    if len(recs) != m['calls']:
        problems.append(f"calls: recount {len(recs)} vs metrics {m['calls']}")

    leads = {}
    for r in recs:
        leads.setdefault(r.get('lead') or r['id'], []).append(r)
    if len(leads) != m['leads']:
        problems.append(f"leads: recount {len(leads)} vs metrics {m['leads']}")

    stages = cfg['stages']
    key_idx = {st['key']: idx for idx, st in enumerate(stages)}
    level = {}
    reached = {}
    deal = {}
    for lead, cs in leads.items():
        rch = [False] * len(stages)
        for k, st in enumerate(stages):
            req = st.get('requires', stages[k - 1]['key'] if k > 0 else None)
            if req is not None and not rch[key_idx[req]]:
                continue
            if st.get('rule') is None or any(ev(c, st['rule']) for c in cs):
                rch[k] = True
        reached[lead] = rch
        level[lead] = max((k for k in range(len(stages)) if rch[k]), default=-1)
        deal[lead] = bool(cfg.get('success')) and any(ev(c, cfg['success']) for c in cs)

    for k, row in enumerate(m['funnel']):
        n = sum(1 for rch in reached.values() if rch[k])
        if n != row['count']:
            problems.append(f"stage {row['key']}: recount {n} vs metrics {row['count']}")
    counts = [r['count'] for r in m['funnel']]
    for k, st in enumerate(stages):
        req = st.get('requires', stages[k - 1]['key'] if k > 0 else None)
        if req is not None and counts[k] > counts[key_idx[req]]:
            problems.append(f"stage {st['key']} ({counts[k]}) exceeds required stage {req} ({counts[key_idx[req]]})")
    deals = sum(deal.values())
    if deals != m['deals']:
        problems.append(f"deals: recount {deals} vs metrics {m['deals']}")

    dropped = sum(1 for lead in leads if not deal[lead] and level[lead] < len(stages) - 1)
    summed = sum(d['count'] for d in m.get('drop_off_summary', []))
    if summed != len(leads) - deals:
        problems.append(f"drop-offs sum {summed} vs unique leads - deals {len(leads) - deals}")
    if len(m.get('drop_offs', [])) != summed:
        problems.append(f"drop_offs list {len(m.get('drop_offs', []))} vs summary {summed}")
    notes.append(f'leads not converted but already at last stage (not in drop-offs): {dropped}')

    if m.get('drop_audit'):
        labelled = m['drop_audit']['labelled']
        total = sum(c for s in m['drop_audit']['reasons'].values() for c in s.values())
        if total != labelled:
            problems.append(f'drop audit reasons sum {total} vs labelled {labelled}')
        if len(m.get('drop_audit_rows', [])) != labelled:
            problems.append(f"drop_audit_rows {len(m.get('drop_audit_rows', []))} vs labelled {labelled}")

    if a.xlsx:
        from openpyxl import load_workbook
        wb = load_workbook(a.xlsx)
        missing = [s for s in REQ_SHEETS if s not in wb.sheetnames]
        if missing:
            problems.append(f'workbook missing sheets: {missing}')
        if 'Drop Audit' not in wb.sheetnames and m.get('drop_audit'):
            problems.append('drop audit labels present but no Drop Audit sheet')
        if 'Funnel Drop-offs' in wb.sheetnames:
            ws = wb['Funnel Drop-offs']
            has_formula = any(isinstance(c.value, str) and c.value.startswith('=COUNTIFS') for row in ws.iter_rows(max_row=10) for c in row)
            if not has_formula:
                problems.append('Funnel Drop-offs has no COUNTIFS summary formula')
        notes.append(f"workbook sheets: {len(wb.sheetnames)}")

    if a.pdf:
        import os
        if not os.path.exists(a.pdf) or os.path.getsize(a.pdf) < 1000:
            problems.append('PDF missing or empty')
        else:
            with open(a.pdf, 'rb') as f:
                if f.read(5) != b'%PDF-':
                    problems.append('PDF header not %PDF-')
            notes.append(f'pdf bytes: {os.path.getsize(a.pdf)}')

    rnd = random.Random(7)
    sample = rnd.sample(sorted(leads), min(a.sample, len(leads))) if leads else []
    for lead in sample:
        stages_hit = [stages[k]['label'] for k in range(len(stages)) if level[lead] >= k]
        notes.append(f"spot lead {lead[-4:]}: level {level[lead]} ({stages[level[lead]]['label'] if level[lead] >= 0 else 'none'}), "
                     f"calls {len(leads[lead])}, passed {len(stages_hit)} stages")

    for n_ in notes:
        print(' -', n_)
    if problems:
        print('FAIL')
        for p in problems:
            print(' !', p)
        sys.exit(1)
    print('OK: all stages recounted, invariants hold')


if __name__ == '__main__':
    main()
