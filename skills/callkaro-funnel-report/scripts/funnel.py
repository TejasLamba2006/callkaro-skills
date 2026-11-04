"""Stage rules, per-lead reduction and metrics.json for a CallKaro funnel report.

usage:
  python -I funnel.py --config funnel.json --calls raw/calls.jsonl --out out/metrics.json \
      [--labels out/drop_labels.json] [--schedules out/sch_lang.json]

Stages are cumulative: a lead is at stage k only if it passed stage k-1 on some call, and passed
stage k on some call. A stage with rule null is always passed. Deals are the success rule, counted
on any call, and are excluded from drop-offs. Rates on denominators below min_n are flagged, not hidden.

Rule grammar (nestable): {"all": [...]}, {"any": [...]}, {"not": rule},
  {"field": "dotted.path", "op": "==|!=|>|>=|<|<=|in|contains|not_contains|truthy|regex", "value": v},
  {"is_human": true|false}, {"capability_visited": "name"}, {"function_called": "name"},
  {"transcript_agent_regex": "re"}, {"transcript_customer_regex": "re"},
  {"function_output_regex": "re"} or {"function_output_regex": {"name": "fn", "regex": "re"}}
"""
import argparse
import collections
import csv
import datetime as dt
import io
import json
import os
import re
import sys

KEYS_REQUIRED = ('stages', 'window')


def get(rec, path):
    cur = rec
    for part in str(path).split('.'):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def truthy(v):
    return bool(v) and str(v).lower() not in ('false', '0', 'none', 'null', '')


def _rx(pat, texts):
    return any(re.search(pat, t or '', re.I) for t in texts)


def test(rec, rule):
    if rule is None:
        return True
    if 'all' in rule:
        return all(test(rec, r) for r in rule['all'])
    if 'any' in rule:
        return any(test(rec, r) for r in rule['any'])
    if 'not' in rule:
        return not test(rec, rule['not'])
    if 'is_human' in rule:
        return bool(rec.get('human')) == bool(rule['is_human'])
    if 'capability_visited' in rule:
        return rule['capability_visited'] in (rec.get('capabilities_switched') or [])
    if 'function_called' in rule:
        return rule['function_called'] in (rec.get('functions') or [])
    if 'transcript_agent_regex' in rule:
        return _rx(rule['transcript_agent_regex'], [t for role, t, *_ in rec.get('transcript') or [] if role == 'a'])
    if 'transcript_customer_regex' in rule:
        return _rx(rule['transcript_customer_regex'], [t for role, t, *_ in rec.get('transcript') or [] if role == 'u'])
    if 'function_output_regex' in rule:
        spec = rule['function_output_regex']
        if isinstance(spec, str):
            spec = {'regex': spec}
        outs = [o for o in rec.get('function_outputs') or [] if not spec.get('name') or o.get('name') == spec['name']]
        return _rx(spec['regex'], [o.get('output', '') for o in outs])
    field, op, want = rule['field'], rule['op'], rule.get('value')
    val = get(rec, field)
    if op == 'truthy':
        return truthy(val)
    if op == 'regex':
        return bool(re.search(want, str(val or ''), re.I))
    if op == 'contains':
        if isinstance(val, list):
            return any(str(want).lower() == str(x).lower() for x in val)
        return str(want).lower() in str(val or '').lower()
    if op == 'not_contains':
        return not test(rec, {'field': field, 'op': 'contains', 'value': want})
    if op == 'in':
        return str(val).lower() in [str(w).lower() for w in want]
    if op in ('==', '!='):
        eq = (str(val).lower() == want.lower()) if isinstance(want, str) else (val == want)
        return eq if op == '==' else not eq
    try:
        v, w = float(val or 0), float(want)
    except (TypeError, ValueError):
        return False
    return {'>': v > w, '>=': v >= w, '<': v < w, '<=': v <= w}[op]


def parse_ist(s):
    return dt.datetime.strptime(s[:16], '%Y-%m-%d %H:%M')


def ist_of(rec, off):
    return dt.datetime.strptime(rec['at'][:19].replace('T', ' '), '%Y-%m-%d %H:%M:%S') + dt.timedelta(hours=off)


def lead_key(r):
    return r.get('lead') or r['id']


def bins_for(w):
    if w.get('bins') == 'weekly':
        s, e = parse_ist(w['start_ist']), parse_ist(w['end_ist'])
        out, i = [], 0
        while s + dt.timedelta(days=7 * i) < e:
            a = s + dt.timedelta(days=7 * i)
            b = min(a + dt.timedelta(days=7), e)
            out.append({'label': f"{a:%d %b}-{b:%d %b}", 'start': a, 'end': b})
            i += 1
        return out
    if isinstance(w.get('bins'), list):
        return [{'label': b['label'], 'start': parse_ist(b['start_ist']), 'end': parse_ist(b['end_ist'])} for b in w['bins']]
    return [{'label': 'all', 'start': parse_ist(w['start_ist']), 'end': parse_ist(w['end_ist'])}]


def in_window(recs, cfg):
    off = cfg['window']['tz_offset_hours']
    s, e = parse_ist(cfg['window']['start_ist']), parse_ist(cfg['window']['end_ist'])
    out = []
    for r in recs:
        if cfg.get('versions') and r.get('version') not in cfg['versions'] and r.get('version_id') not in cfg['versions']:
            continue
        if any(test(r, x) for x in cfg.get('exclude_calls', [])):
            continue
        if s <= ist_of(r, off) < e:
            out.append(r)
    return out


def analyse(cfg, recs):
    """Annotate each call (_attempt, _human_attempt, _pass, _success) and reduce to one dict per lead."""
    stages, succ, n = cfg['stages'], cfg.get('success'), len(cfg['stages'])
    by_lead = collections.defaultdict(list)
    for r in recs:
        by_lead[lead_key(r)].append(r)
    city_f = cfg.get('city_field', 'city')
    leads = {}
    for lead, cs in by_lead.items():
        cs.sort(key=lambda c: c['at'])
        hn = 0
        for i, c in enumerate(cs, 1):
            c['_attempt'] = i
            if c.get('human'):
                hn += 1
                c['_human_attempt'] = hn
            else:
                c['_human_attempt'] = None
            c['_pass'] = [st.get('rule') is None or test(c, st['rule']) for st in stages]
            c['_success'] = bool(succ) and test(c, succ)
        key_idx = {st['key']: idx for idx, st in enumerate(stages)}
        reached = [False] * n
        for k, st in enumerate(stages):
            req = st.get('requires', stages[k - 1]['key'] if k > 0 else None)
            if req is not None and not reached[key_idx[req]]:
                continue
            if any(c['_pass'][k] for c in cs):
                reached[k] = True
        level = max((k for k in range(n) if reached[k]), default=-1)
        ag = next((c for c in cs if c['_success']), None)
        dim = lambda path: next((get(c, path) for c in cs if path and get(c, path) not in (None, '')), None) or 'none'
        leads[lead] = {
            'lead': lead, 'level': level, 'reached': reached, 'agreed': ag is not None, 'n_calls': len(cs),
            'n_human': sum(1 for c in cs if c.get('human')),
            'agreed_attempt': ag['_attempt'] if ag else None,
            'agreed_human_attempt': ag['_human_attempt'] if ag else None,
            'agree_capability': ((ag.get('capabilities_switched') or ['start'])[-1] if ag else None),
            'city': dim(city_f), 'version': cs[-1].get('version') or 'Unknown',
            'opening_lang': next((c.get('opening_lang') for c in cs if c.get('opening_lang') not in (None, '', 'none')), 'none'),
            'scenario': dim(cfg.get('scenario_field')), 'quadrant': dim(cfg.get('quadrant_field')),
            'arm': dim(cfg.get('arm_field')), 'calls': cs,
            'final_stage': stages[level]['label'] if level >= 0 else 'none',
        }
    return leads


def summarise(items, stages, min_n):
    n = len(items)
    counts = [sum(1 for x in items if x['reached'][k]) for k in range(len(stages))]
    rows, prev = [], n
    for k, st in enumerate(stages):
        c = counts[k]
        rows.append({'key': st['key'], 'label': st['label'], 'count': c,
                     'pct_of_called': round(c / n, 4) if n else None,
                     'pct_of_prev': round(c / prev, 4) if prev and k else None,
                     'flag_small_n': prev < min_n})
        prev = c
    return {'leads': n, 'deals': sum(1 for x in items if x['agreed']), 'funnel': rows}


def group(leads, key_fn, stages, min_n):
    buckets = collections.defaultdict(list)
    for x in leads.values():
        buckets[key_fn(x)].append(x)
    return {k: summarise(v, stages, min_n) for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1]))}


def load_labels(path):
    if not path:
        return {}
    rows = json.load(io.open(path, encoding='utf-8'))
    return {(x['stage'], x['lead']): x for x in rows if x.get('reason') not in (None, 'ERROR')}


def load_crm(cfg, path):
    if not path:
        return None
    j = cfg.get('crm_join') or {}
    if path.lower().endswith('.json'):
        rows = json.load(io.open(path, encoding='utf-8'))
    else:
        rows = list(csv.DictReader(io.open(path, encoding='utf-8', newline='')))
    return {str(r.get(j.get('crm_key', 'lead_id'))): str(r.get(j.get('status_field', 'status'))) for r in rows}


def norm_lang(x):
    return str(x or 'none').split('-')[0].lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--calls', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--labels')
    ap.add_argument('--schedules')
    ap.add_argument('--crm')
    a = ap.parse_args()
    cfg = json.load(io.open(a.config, encoding='utf-8'))
    stages, min_n, off = cfg['stages'], cfg.get('min_n', 5), cfg['window']['tz_offset_hours']
    recs = in_window([json.loads(x) for x in io.open(a.calls, encoding='utf-8') if x.strip()], cfg)
    leads = analyse(cfg, recs)
    n = len(stages)
    # write annotated calls now, before the per-bin analyses below overwrite _attempt/_pass on the same dicts
    ann = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'calls_annotated.jsonl')
    with io.open(ann, 'w', encoding='utf-8') as f:
        for r in sorted(recs, key=lambda c: c['at']):
            f.write(json.dumps(r, ensure_ascii=False, default=str) + '\n')
    top = summarise(list(leads.values()), stages, min_n)
    m = {'name': cfg['name'], 'period_label': cfg['period_label'], 'calls': len(recs), 'leads': len(leads),
         'deals': top['deals'], 'stages': [{'key': s['key'], 'label': s['label']} for s in stages], 'min_n': min_n,
         'funnel': top['funnel'], 'answered_calls': sum(1 for r in recs if (r.get('duration') or 0) > 0),
         'human_calls': sum(1 for r in recs if r.get('human')), 'human_leads': sum(1 for x in leads.values() if x['n_human'] > 0)}

    m['bins'] = []
    for b in bins_for(cfg['window']):
        sub = [r for r in recs if b['start'] <= ist_of(r, off) < b['end']]
        sl = analyse(cfg, sub)
        m['bins'].append({'label': b['label'], 'calls': len(sub), 'leads': len(sl), 'deals': sum(1 for x in sl.values() if x['agreed']),
                          'funnel': summarise(list(sl.values()), stages, min_n)['funnel']})

    m['cities'] = group(leads, lambda x: x['city'], stages, min_n)
    m['by_version'] = group(leads, lambda x: x['version'], stages, min_n)
    m['by_opening_lang'] = group(leads, lambda x: x['opening_lang'], stages, min_n)
    m['by_final_stage'] = group(leads, lambda x: x['final_stage'], stages, min_n)
    if cfg.get('scenario_field'):
        m['by_scenario'] = group(leads, lambda x: x['scenario'], stages, min_n)
    if cfg.get('quadrant_field'):
        m['by_quadrant'] = group(leads, lambda x: x['quadrant'], stages, min_n)
    if cfg.get('arm_field'):
        m['arms'] = group(leads, lambda x: x['arm'], stages, min_n)

    agreed = [x for x in leads.values() if x['agreed']]
    m['where_agreed'] = dict(collections.Counter(x['agree_capability'] for x in agreed).most_common())
    m['agreed_on_call'] = dict(sorted(collections.Counter(x['agreed_attempt'] for x in agreed).items()))
    m['calls_per_lead'] = dict(sorted(collections.Counter(min(x['n_calls'], 10) for x in leads.values()).items()))
    m['agreed_human_attempt'] = dict(sorted(collections.Counter(x['agreed_human_attempt'] for x in agreed).items()))

    m['checks'] = []
    for chk in cfg.get('checks', []):
        hits = [x for x in leads.values() if any(test(c, chk['rule']) for c in x['calls'])]
        m['checks'].append({'label': chk['label'], 'leads': len(hits),
                            'calls': sum(1 for x in leads.values() for c in x['calls'] if test(c, chk['rule']))})

    days = collections.OrderedDict()
    for r in sorted(recs, key=lambda c: c['at']):
        d = f"{ist_of(r, off):%Y-%m-%d}"
        row = days.setdefault(d, {'date': d, 'calls': 0, 'answered': 0, 'human': 0, 'deals': 0,
                                  **{s['key']: 0 for s in stages[1:]}})
        row['calls'] += 1
        row['answered'] += 1 if (r.get('duration') or 0) > 0 else 0
        row['human'] += 1 if r.get('human') else 0
        row['deals'] += 1 if r.get('_success') else 0
        for k, s in enumerate(stages):
            if k and r['_pass'][k]:
                row[s['key']] += 1
    m['daily'] = list(days.values())

    labels = load_labels(a.labels)
    m['drop_offs'], m['drop_off_summary'] = [], []
    for k in range(1, n):
        lost = [x for x in leads.values() if not x['agreed'] and x['level'] == k - 1]
        m['drop_off_summary'].append({'step': stages[k]['label'], 'key': stages[k]['key'], 'count': len(lost)})
        for x in sorted(lost, key=lambda z: z['lead']):
            rep = x['calls'][-1]
            lab = labels.get((stages[k]['key'], x['lead'])) or {}
            m['drop_offs'].append({'step': stages[k]['label'], 'stage_key': stages[k]['key'], 'lead': x['lead'], 'city': x['city'],
                                   'version': x['version'], 'calls': x['n_calls'], 'call_id': rep['id'], 'at': rep['at'],
                                   'duration': rep.get('duration') or 0, 'hangup': rep.get('hangup_reason') or '',
                                   'recording_url': rep.get('recording_url') or '', 'reason': lab.get('reason', ''),
                                   'side': lab.get('side', ''), 'evidence': lab.get('evidence', '')})
    m['drop_offs_total'] = sum(x['count'] for x in m['drop_off_summary'])

    dnd = cfg.get('dnd_rule')
    if dnd:
        for city, v in m['cities'].items():
            v['dnd'] = sum(1 for x in leads.values() if x['city'] == city and any(test(c, dnd) for c in x['calls']))
    m['lead_rows'] = [{'lead': x['lead'], 'city': x['city'], 'version': x['version'], 'opening_lang': x['opening_lang'],
                       'n_calls': x['n_calls'], 'n_human': x['n_human'], 'final_stage': x['final_stage'], 'agreed': x['agreed'],
                       'agreed_attempt': x['agreed_attempt'], 'scenario': x['scenario'], 'quadrant': x['quadrant'], 'arm': x['arm']}
                      for x in sorted(leads.values(), key=lambda z: z['lead'])]

    if labels:
        reasons = collections.defaultdict(collections.Counter)
        sides = collections.defaultdict(collections.Counter)
        reason_side = collections.defaultdict(collections.Counter)
        byver = collections.defaultdict(lambda: collections.Counter())
        for (stage, _), x in labels.items():
            sd = x.get('side') or 'unknown'
            reasons[stage][x['reason']] += 1
            sides[stage][sd] += 1
            reason_side[(stage, x['reason'])][sd] += 1
            byver[x.get('version') or 'Unknown'][sd] += 1
        m['drop_audit'] = {'labelled': len(labels), 'reasons': {s: dict(c.most_common()) for s, c in reasons.items()},
                           'sides': {s: dict(c.most_common()) for s, c in sides.items()},
                           'reason_side': {f'{s}:{r}': c.most_common(1)[0][0] for (s, r), c in reason_side.items()},
                           'by_version_side': {v: dict(c) for v, c in byver.items()}}
        m['drop_audit_rows'] = list(labels.values())

    if a.schedules:
        sch = json.load(io.open(a.schedules, encoding='utf-8'))
        pairs, total, mism = collections.Counter(), 0, 0
        for x in leads.values():
            sid = next((c.get('sch_id') for c in x['calls'] if c.get('sch_id') in sch), None)
            if not sid or 'lang' not in sch[sid]:
                continue
            spoken = next((c.get('customer_lang') for c in x['calls'] if c.get('customer_lang') not in (None, '', 'none')), 'none')
            total += 1
            mism += norm_lang(sch[sid]['lang']) != norm_lang(spoken)
            pairs[f"{norm_lang(sch[sid]['lang'])} -> spoken {norm_lang(spoken)}"] += 1
        m['lang_mismatch'] = {'leads_with_schedule': total, 'mismatched': mism, 'pairs': dict(pairs.most_common(20))}

    if a.crm:
        j = cfg.get('crm_join') or {}
        crm = load_crm(cfg, a.crm)
        cats = collections.Counter()
        for x in leads.values():
            key = next((str(get(c, j.get('call_field', 'lead'))) for c in x['calls'] if get(c, j.get('call_field', 'lead'))), x['lead'])
            crm_deal = crm.get(key) == str(j.get('deal_value', 'deal'))
            cats['Both: deal' if x['agreed'] and crm_deal else
                 'Bot deal, no CRM' if x['agreed'] else
                 'CRM deal, bot no deal' if crm_deal else 'Neither'] += 1
        unmatched = len(set(crm) - {str(get(c, j.get('call_field', 'lead'))) for x in leads.values() for c in x['calls']})
        m['crm'] = {'rows': len(crm), 'leads': len(leads), 'categories': dict(cats), 'crm_rows_without_call': unmatched}

    defs = [('Window', f"{cfg['window']['start_ist']} to {cfg['window']['end_ist']} IST (UTC offset {off:+}h)"),
            ('Lead', f"call metadata lead_id; calls without one count as their own lead"),
            ('Human call', 'duration > 0, not VOICEMAIL, >=2 customer turns with >=6 letters not bare greetings, no voicemail/screener phrase; or deal closed'),
            ('Deal', 'success rule: ' + json.dumps(cfg.get('success'), ensure_ascii=False)),
            ('Connected stage', 'stage rules are cumulative; see stages'),
            ('Attempt #', 'calls for the lead ordered by start time (all calls); human attempt # counts human calls only')]
    defs += [(f"Stage {s['label']}", json.dumps(s.get('rule'), ensure_ascii=False) if s.get('rule') else 'always (start of funnel)') for s in stages]
    defs += [('Minimum n', f"rates on denominators below {min_n} are flagged"),
             ('Caveat', 'counts are from the call log; post-call fields are model-filled and may be wrong; see drop audit caveats')]
    m['definitions'] = defs

    io.open(a.out, 'w', encoding='utf-8').write(json.dumps(m, ensure_ascii=False, indent=1, default=str))
    print('calls', m['calls'], 'leads', m['leads'], 'deals', m['deals'], [(r['key'], r['count']) for r in m['funnel']])


if __name__ == '__main__':
    sys.exit(main())
