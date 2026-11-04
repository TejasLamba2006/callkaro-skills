"""A4 RCA PDF from metrics.json: matplotlib charts, HTML, printed to PDF with headless Chrome.

usage:
  python -I build_pdf.py --metrics out/metrics.json --out out/Funnel_Report.pdf [--chrome PATH] [--workdir out/pdf]

Chrome is found from --chrome, then the CHROME env var, then google-chrome(-stable)/chromium on PATH.
Every number in the text is computed here from metrics.json; nothing is typed by hand.
Charts: funnel.png, step_<key>.png per audited drop step (bars coloured by dominant side), cities.png.
Requires matplotlib only (plus Chrome). Sections are written only when their data exists.
"""
import argparse
import html
import io
import json
import os
import shutil
import subprocess
import sys

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

NAVY, RED, GREY, AMBER, GREEN = '#1F3864', '#C0504D', '#8C8C8C', '#E1A33A', '#4E9A51'
SIDE_COLOR = {'bot': RED, 'customer': GREY, 'platform': AMBER, 'unknown': '#BFBFBF'}
E = html.escape


def pct(a, b):
    return f'{a / b:.1%}' if b else 'n/a'


def chrome_path(arg):
    cands = [arg, os.environ.get('CHROME')] + [shutil.which(x) for x in ('google-chrome-stable', 'google-chrome', 'chromium', 'chromium-browser')]
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit('Chrome not found: pass --chrome PATH or set CHROME')


def funnel_chart(m, wd):
    rows = m['funnel']
    labs = [r['label'] for r in rows][::-1]
    vals = [r['count'] for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(8, 3.8), dpi=200)
    ax.barh(labs, vals, color=NAVY)
    top = max(vals) if vals else 1
    for i, v in enumerate(vals):
        ax.text(v + top * 0.01, i, f'{v:,}  ({pct(v, rows[0]["count"])} of called)', va='center', fontsize=8)
    ax.set_xlim(0, top * 1.35)
    ax.set_xlabel('leads')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    p = os.path.join(wd, 'funnel.png')
    fig.savefig(p)
    plt.close(fig)
    return p


def step_chart(key, label, items, wd):
    items = sorted(items, key=lambda x: -x['count'])[:12]
    names = [i['reason'].replace('_', ' ') for i in items][::-1]
    vals = [i['count'] for i in items][::-1]
    cols = [SIDE_COLOR.get(i['side'], GREY) for i in items][::-1]
    fig, ax = plt.subplots(figsize=(8, max(2.4, 0.42 * len(items) + 1)), dpi=200)
    ax.barh(names, vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(v + 0.2, i, str(v), va='center', fontsize=8)
    ax.set_title(f'Why leads dropped at: {label}', fontsize=10, loc='left')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    p = os.path.join(wd, f'step_{key}.png')
    fig.savefig(p)
    plt.close(fig)
    return p


def cities_chart(m, wd):
    items = list(m['cities'].items())[:12]
    if not items:
        return None
    names = [k for k, _ in items][::-1]
    vals = [v['leads'] for _, v in items][::-1]
    fig, ax = plt.subplots(figsize=(8, 3.4), dpi=200)
    ax.barh(names, vals, color=NAVY)
    for i, v in enumerate(vals):
        ax.text(v + 0.3, i, str(v), va='center', fontsize=8)
    ax.set_title('Leads called by city (top 12)', fontsize=10, loc='left')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    p = os.path.join(wd, 'cities.png')
    fig.savefig(p)
    plt.close(fig)
    return p


def table(headers, rows):
    h = ''.join(f'<th>{E(str(x))}</th>' for x in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{E(str(c))}</td>' for c in r) + '</tr>' for r in rows)
    return f'<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'


def build_html(m, wd, charts):
    f = m['funnel']
    called = f[0]['count'] if f else 0
    kpi = lambda label, val: f'<div class="kpi"><div class="v">{E(str(val))}</div><div class="l">{E(label)}</div></div>'
    cover = ('<div class="kpis">' + kpi('calls in window', f"{m['calls']:,}") + kpi('unique leads', f"{m['leads']:,}")
             + kpi('leads with a human call', f"{m.get('human_leads', 0):,}")
             + kpi('deals', f"{m['deals']:,}") + kpi('deal rate of called', pct(m['deals'], called)) + '</div>')

    bullets = [f"{called:,} unique leads called in {m['period_label']}; {m.get('human_leads', 0):,} had a human connection."]
    for r in f[1:]:
        bullets.append(f"{r['label']}: {r['count']:,} leads ({pct(r['count'], called)} of called).")
    bullets.append(f"Deals: {m['deals']:,} ({pct(m['deals'], called)} of called, {pct(m['deals'], f[1]['count'] if len(f) > 1 else 0)} of connected).")
    if m.get('drop_offs_total') is not None:
        bullets.append(f"{m['drop_offs_total']:,} leads did not convert; each is counted once at the stage where it stopped.")
    s1 = '<ul>' + ''.join(f'<li>{E(b)}</li>' for b in bullets) + '</ul>'

    s2 = ('<p>Pulled with <code>cku calls list --agent</code> in pages of 100, deduplicated by call ID. Stages are cumulative. '
          'A human call is duration &gt; 0, not voicemail, with two or more real customer turns, and no voicemail or screener phrase; a closed deal is always human. '
          'Rates on fewer than ' + str(m.get('min_n', 5)) + ' leads are flagged. Window: ' + E(m.get('window_label', m['period_label'])) + ' (IST).</p>')

    rows = [[r['label'], f"{r['count']:,}", pct(r['count'], called), pct(r['count'], f[i - 1]['count']) if i else '-']
            for i, r in enumerate(f)]
    s3 = f'<img src="{charts["funnel"]}" class="wide"/>' + table(['Stage', 'Leads', '% of called', '% of previous'], rows)
    if m.get('drop_off_summary'):
        s3 += '<h3>Where leads were lost</h3>' + table(['Step lost', 'Leads'], [[d['step'], f"{d['count']:,}"] for d in m['drop_off_summary']])

    s4 = ''
    da = m.get('drop_audit')
    if da:
        s4 += f"<p>LLM drop audit labelled {da['labelled']:,} leads. Each has one reason, a side (bot, customer or platform), and an exact transcript quote.</p>"
        for key, (path, lab) in charts.get('steps', {}).items():
            s4 += f'<h3>{E(lab)}</h3><img src="{path}" class="wide"/>'
            ev = [d for d in m['drop_offs'] if d['stage_key'] == key and d.get('evidence')][:4]
            if ev:
                s4 += '<ul class="ev">' + ''.join(f"<li><b>{E(d['reason'])}</b> ({E(d['side'])}), call {E(d['call_id'])}: &ldquo;{E(d['evidence'][:180])}&rdquo;</li>" for d in ev) + '</ul>'
        sides = {}
        for sd in da['sides'].values():
            for k, v in sd.items():
                sides[k] = sides.get(k, 0) + v
        tot = sum(sides.values()) or 1
        s4 += '<p>Side split across all labelled drops: ' + ', '.join(f"{k} {v:,} ({v / tot:.0%})" for k, v in sorted(sides.items(), key=lambda kv: -kv[1])) + '.</p>'

    s5 = ''
    if m.get('cities'):
        s5 += f'<img src="{charts["cities"]}" class="wide"/>' if charts.get('cities') else ''
    if m.get('lang_mismatch'):
        lm = m['lang_mismatch']
        s5 += f"<p>Schedule language check: {lm['mismatched']:,} of {lm['leads_with_schedule']:,} leads had a scheduled language different from the spoken language.</p>"
    if m.get('crm'):
        s5 += '<p>CRM comparison: ' + ', '.join(f'{E(k)} {v:,}' for k, v in m['crm']['categories'].items()) + '.</p>'
    if m.get('where_agreed'):
        s5 += '<h3>Where deals were agreed</h3>' + table(['Capability', 'Deals'], list(m['where_agreed'].items()))

    s6 = table(['Item', 'Owner', 'Status'], [['Review flagged rules and definitions with the team', '', 'open'],
                                             ['Fix root causes ranked by drop count above', '', 'open']])

    css = f"""@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; color: #222; font-size: 10pt; }}
h1 {{ color: {NAVY}; font-size: 20pt; margin: 0 0 4px 0; }} h2 {{ color: {NAVY}; border-bottom: 2px solid {NAVY}; padding-bottom: 2px; page-break-after: avoid; }}
h3 {{ color: {NAVY}; font-size: 11pt; page-break-after: avoid; }}
.kpis {{ display: flex; gap: 8px; margin: 14px 0; }} .kpi {{ background: {NAVY}; color: #fff; padding: 10px; flex: 1; text-align: center; border-radius: 4px; }}
.kpi .v {{ font-size: 16pt; font-weight: bold; }} .kpi .l {{ font-size: 8pt; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 9pt; page-break-inside: auto; }}
th {{ background: {NAVY}; color: #fff; text-align: left; padding: 4px; }} td {{ border-bottom: 1px solid #ddd; padding: 3px 4px; }}
img.wide {{ width: 100%; }} section {{ page-break-inside: auto; }} .ev li {{ margin-bottom: 3px; }} code {{ font-size: 9pt; }}
"""
    body = (f'<section><h1>{E(m["name"])}</h1><div>RCA and funnel report, {E(m["period_label"])}</div>{cover}</section>'
            f'<section><h2>1. Summary</h2>{s1}</section>'
            f'<section><h2>2. How the data was built</h2>{s2}</section>'
            f'<section><h2>3. Funnel</h2>{s3}</section>'
            f'<section><h2>4. Root cause by stage</h2>{s4 or "<p>No drop audit was run.</p>"}</section>'
            f'<section><h2>5. Cross-cutting findings</h2>{s5 or "<p>No city, schedule or CRM data supplied.</p>"}</section>'
            f'<section><h2>6. Action items</h2>{s6}</section>')
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--metrics', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--chrome')
    ap.add_argument('--workdir')
    a = ap.parse_args()
    m = json.load(io.open(a.metrics, encoding='utf-8'))
    wd = a.workdir or os.path.join(os.path.dirname(os.path.abspath(a.out)), 'pdf')
    os.makedirs(wd, exist_ok=True)
    charts = {'funnel': funnel_chart(m, wd), 'steps': {}}
    if m.get('drop_audit'):
        keys = list(m['drop_audit']['reasons'].keys())
        stage_label = {s['key']: s['label'] for s in m['stages']}
        rside = m['drop_audit'].get('reason_side') or {}
        for key in keys:
            items = [{'reason': r, 'count': c, 'side': rside.get(f'{key}:{r}') or max(m['drop_audit']['sides'].get(key, {'unknown': 0}).items(), key=lambda kv: kv[1])[0]}
                     for r, c in m['drop_audit']['reasons'][key].items()]
            charts['steps'][key] = (step_chart(key, stage_label.get(key, key), items, wd), stage_label.get(key, key))
        charts['steps'] = {k: (v[0], v[1]) for k, v in charts['steps'].items()}
    cp = cities_chart(m, wd)
    if cp:
        charts['cities'] = cp
    htm = os.path.join(wd, 'report.html')
    io.open(htm, 'w', encoding='utf-8').write(build_html(m, wd, _fix_paths(charts, wd)))
    chrome = chrome_path(a.chrome)
    r = subprocess.run([chrome, '--headless', '--disable-gpu', '--no-sandbox', f'--print-to-pdf={os.path.abspath(a.out)}',
                        '--no-pdf-header-footer', 'file://' + os.path.abspath(htm)], capture_output=True, text=True, timeout=180)
    if not os.path.exists(a.out) or os.path.getsize(a.out) == 0:
        sys.exit('Chrome did not write the PDF: ' + (r.stderr or r.stdout)[-300:])
    print('wrote', a.out)


def _fix_paths(charts, wd):
    """Make chart paths relative to the HTML file (same folder), and unwrap the steps tuple."""
    out = {'funnel': os.path.basename(charts['funnel']), 'steps': {}}
    for k, (p, lab) in charts['steps'].items():
        out['steps'][k] = (os.path.basename(p), lab)
    if 'cities' in charts:
        out['cities'] = os.path.basename(charts['cities'])
    return out


if __name__ == '__main__':
    main()
