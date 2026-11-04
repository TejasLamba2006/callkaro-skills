"""Build the full funnel workbook from metrics.json (plus the calls file for the call-level sheets).

usage:
  python -I build_xlsx.py --metrics out/metrics.json --calls out/calls_annotated.jsonl --out out/Funnel_Report.xlsx
(calls_annotated.jsonl is written by funnel.py; it carries _attempt, _human_attempt, _pass, _success.)

Sheets: Summary, Funnel Drop-offs, Drop Audit, Drop Audit Calls (only if labels exist), City Funnel, Targets,
Daily Trend, By Version, By Scenario (if configured), By Quadrant (if configured), By Opening Language,
By Final Stage, All Leads, All Calls, Definitions.
Rates are live formulas over count cells. Colour rules read the Targets sheet; rates on denominators below
min_n are not coloured. Play links use recording_url from the call log.
"""
import argparse
import io
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.table import Table, TableStyleInfo

NAVY = '1F3864'
HF = Font(bold=True, color='FFFFFF')
HFILL = PatternFill('solid', fgColor=NAVY)
GRN = PatternFill('solid', fgColor='C6EFCE')
YEL = PatternFill('solid', fgColor='FFE699')
RED = PatternFill('solid', fgColor='F8CBAD')
PCT = '0.0%'
WRAP = Alignment(wrap_text=True, vertical='top')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def header(ws, row, cols, widths=None):
    for j, c in enumerate(cols, 1):
        x = ws.cell(row, j, c)
        x.font, x.fill = HF, HFILL
        x.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
    ws.row_dimensions[row].height = 42
    for j, w in enumerate(widths or [], 1):
        ws.column_dimensions[L(j)].width = w


def table(ws, ref, name):
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
    ws.add_table(t)


def ryg(ws, rng, first_cell, target_ref, min_n_ref, higher_ref, n_cell):
    """Green when >= target, yellow within warn band (0.2 relative), red otherwise. Uncoloured when n < MIN_N or target 0."""
    cond = f'AND(ISNUMBER({first_cell}),{target_ref}>0,{n_cell}>={min_n_ref})'
    ok = f'IF({higher_ref}="Yes",{first_cell}>={target_ref},{first_cell}<={target_ref})'
    warn = f'IF({higher_ref}="Yes",{first_cell}>={target_ref}*0.8,{first_cell}<={target_ref}*1.2)'
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'AND({cond},{ok})'], fill=GRN))
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'AND({cond},NOT({ok}),{warn})'], fill=YEL))
    ws.conditional_formatting.add(rng, FormulaRule(formula=[f'AND({cond},NOT({ok}),NOT({warn}))'], fill=RED))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--metrics', required=True)
    ap.add_argument('--calls', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    m = json.load(io.open(a.metrics, encoding='utf-8'))
    calls = [json.loads(x) for x in io.open(a.calls, encoding='utf-8') if x.strip()]
    wb = Workbook()
    min_n = m.get('min_n', 5)
    stages = [s['label'] for s in m['stages']]

    # ---------------- Targets (created first so formulas can reference it) ----------------
    tg = wb.active
    tg.title = 'Targets'
    tg['A1'] = 'Targets. Type a target in column B. 0 = use the period average (no colour). Warn band 20%.'
    tg['A1'].font = Font(bold=True, color=NAVY)
    header(tg, 3, ['Rate metric', 'Target', 'Higher is better?', 'Period average'], [44, 12, 18, 16])
    TGT = {}
    rate_rows = [
        ('Connect rate (connected / called)', 'connect'),
        ('Pitch rate (pitched / connected)', 'pitch'),
        ('Negotiation rate (negotiation / pitched)', 'neg'),
        ('Escalation rate (escalated / negotiation)', 'esc'),
        ('Deal rate (deal / connected)', 'deal_conn'),
        ('Deal rate (deal / pitched)', 'deal_pitch'),
        ('Hang-up on first call rate', 'hang1'),
        ('DND rate (DND / called)', 'dnd'),
    ]
    for i, (lab, key) in enumerate(rate_rows, 4):
        tg.cell(i, 1, lab)
        tg.cell(i, 2, 0).number_format = PCT
        tg.cell(i, 3, 'No' if key in ('hang1', 'dnd') else 'Yes')
        TGT[key] = (f'Targets!$B${i}', f'Targets!$C${i}')
    tg['A14'] = 'MIN_N (rates on fewer than this many leads/calls are not coloured)'
    tg['B14'] = min_n
    MINN = 'Targets!$B$14'
    tg.column_dimensions['A'].width = 52

    # ---------------- Summary ----------------
    s = wb.create_sheet('Summary', 0)
    s['A1'] = f"{m['name']}: funnel and root cause, {m['period_label']}"
    s['A1'].font = Font(bold=True, size=14, color=NAVY)
    header(s, 3, ['Headline KPI', 'Value'], [48, 18])
    kpis = [('Calls in window', m['calls']), ('Unique leads', m['leads']), ('Answered calls (duration > 0)', m['answered_calls']),
            ('Human-connected calls', m['human_calls']), ('Leads with a human call', m['human_leads']),
            ('Deals (leads)', m['deals']), ('Drop-offs (leads not converted, all steps)', m.get('drop_offs_total', 0))]
    for i, (k, v) in enumerate(kpis, 4):
        s.cell(i, 1, k)
        s.cell(i, 2, v)
    r0 = 4 + len(kpis) + 1
    header(s, r0, ['Lead funnel stage', 'Leads reaching stage', '% of called', '% of previous'], [48, 18, 14, 16])
    for i, r in enumerate(m['funnel']):
        row = r0 + 1 + i
        s.cell(row, 1, r['label'])
        s.cell(row, 2, r['count'])
        s.cell(row, 3, f'=IF($B${r0 + 1}=0,"",B{row}/$B${r0 + 1})').number_format = PCT
        s.cell(row, 4, '' if i == 0 else f'=IF(B{row - 1}=0,"",B{row}/B{row - 1})').number_format = PCT
    fend = r0 + len(m['funnel'])
    bc = BarChart()
    bc.type, bc.title, bc.legend = 'bar', 'Leads reaching each stage', None
    bc.add_data(Reference(s, min_col=2, min_row=r0, max_row=fend), titles_from_data=True)
    bc.set_categories(Reference(s, min_col=1, min_row=r0 + 1, max_row=fend))
    bc.y_axis.scaling.orientation = 'minMax'
    bc.x_axis.scaling.orientation = 'maxMin'
    bc.height, bc.width = 8, 16
    s.add_chart(bc, 'F3')

    r1 = fend + 3
    ag = m.get('where_agreed', {})
    header(s, r1, ['Where deals were agreed (capability at the deal)', 'Deals'], [48, 18])
    for i, (k, v) in enumerate(ag.items()):
        s.cell(r1 + 1 + i, 1, k)
        s.cell(r1 + 1 + i, 2, v)
    if ag:
        pie = PieChart()
        pie.title = 'Where deals were agreed'
        pie.add_data(Reference(s, min_col=2, min_row=r1, max_row=r1 + len(ag)), titles_from_data=True)
        pie.set_categories(Reference(s, min_col=1, min_row=r1 + 1, max_row=r1 + len(ag)))
        s.add_chart(pie, f'F{r1}')
    r2 = r1 + max(len(ag), 1) + 3
    header(s, r2, ['Deal agreed on call #', 'Leads'], [48, 18])
    for i, (k, v) in enumerate(m.get('agreed_on_call', {}).items()):
        s.cell(r2 + 1 + i, 1, f'call {k}')
        s.cell(r2 + 1 + i, 2, v)
    r3 = r2 + len(m.get('agreed_on_call', {})) + 3
    header(s, r3, ['Pricing / safety check', 'Calls or leads matching'], [48, 18])
    for i, c in enumerate(m.get('checks', [])):
        s.cell(r3 + 1 + i, 1, c['label'])
        s.cell(r3 + 1 + i, 2, f"{c['leads']} leads / {c['calls']} calls")
    r4 = r3 + len(m.get('checks', [])) + 3
    if m.get('crm'):
        header(s, r4, ['CRM truth comparison', 'Leads'], [48, 18])
        for i, (k, v) in enumerate(m['crm']['categories'].items()):
            s.cell(r4 + 1 + i, 1, k)
            s.cell(r4 + 1 + i, 2, v)
        s.cell(r4 + 2 + len(m['crm']['categories']), 1, f"CRM rows with no matching call: {m['crm']['crm_rows_without_call']}")

    # ---------------- Funnel drop-offs ----------------
    fd = wb.create_sheet('Funnel Drop-offs')
    header(fd, 1, ['Step lost', 'Leads lost (count)'], [44, 18])
    for i, r in enumerate(m['drop_off_summary'], 2):
        fd.cell(i, 1, r['step'])
        fd.cell(i, 2, f'=COUNTIFS($A$20:$A$5000,A{i})')
    fd.cell(2 + len(m['drop_off_summary']), 1, 'Total dropped (check = unique leads minus deals)')
    fd.cell(2 + len(m['drop_off_summary']), 2, f'=SUM(B2:B{1 + len(m["drop_off_summary"])})')
    fd.cell(3 + len(m['drop_off_summary']), 1, 'Unique leads minus deals')
    fd.cell(3 + len(m['drop_off_summary']), 2, m['leads'] - m['deals'])
    hdr = ['Step lost', 'Lead', 'City', 'Version', 'Calls', 'Representative call', 'Play recording', 'AI reason', 'AI side', 'AI evidence', 'At (IST start)', 'Duration s', 'Hangup']
    header(fd, 19, hdr, [30, 18, 14, 22, 8, 24, 18, 26, 12, 60, 20, 12, 22])
    for i, d in enumerate(m['drop_offs'], 20):
        vals = [d['step'], d['lead'], d['city'], d['version'], d['calls'], d['call_id'], None, d['reason'], d['side'],
                d['evidence'], d['at'], d['duration'], d['hangup']]
        for j, v in enumerate(vals, 1):
            fd.cell(i, j, v)
        if d.get('recording_url'):
            c = fd.cell(i, 7, 'Play')
            c.hyperlink = d['recording_url']
            c.font = Font(color='0563C1', underline='single')
    if m['drop_offs']:
        table(fd, f'A19:M{19 + len(m["drop_offs"])}', 'DropOffs')
    fd.freeze_panes = 'A20'

    # ---------------- Drop Audit + Drop Audit Calls ----------------
    da = m.get('drop_audit')
    if da:
        ds = wb.create_sheet('Drop Audit')
        all_reasons = sorted({r for d in da['reasons'].values() for r in d})
        keys = list(da['reasons'].keys())
        header(ds, 1, ['Reason'] + keys + ['Total'], [34] + [16] * len(keys) + [10])
        for i, rs in enumerate(all_reasons, 2):
            ds.cell(i, 1, rs)
            for j, k in enumerate(keys, 2):
                ds.cell(i, j, da['reasons'][k].get(rs, 0))
            ds.cell(i, len(keys) + 2, f'=SUM(B{i}:{L(len(keys) + 1)}{i})')
        last_r = 1 + len(all_reasons)
        if all_reasons:
            ds.conditional_formatting.add(f'B2:{L(len(keys) + 1)}{last_r}',
                                          ColorScaleRule(start_type='min', start_color='FFFFFF', end_type='max', end_color='F4B183'))
        r = last_r + 3
        header(ds, r, ['Whose side'] + keys, None)
        sides = ['bot', 'customer', 'platform', 'unknown']
        for i, sd in enumerate(sides, r + 1):
            ds.cell(i, 1, sd)
            for j, k in enumerate(keys, 2):
                ds.cell(i, j, da['sides'].get(k, {}).get(sd, 0))
        ch = BarChart()
        ch.type, ch.grouping, ch.overlap, ch.title = 'col', 'stacked', 100, 'Whose side, by drop step'
        ch.add_data(Reference(ds, min_col=1, max_col=len(keys) + 1, min_row=r + 1, max_row=r + len(sides)), from_rows=True, titles_from_data=True)
        ch.set_categories(Reference(ds, min_col=2, max_col=len(keys) + 1, min_row=r))
        ch.height, ch.width = 8, 16
        ds.add_chart(ch, f'A{r + len(sides) + 3}')
        r = r + len(sides) + 22
        header(ds, r, ['Version', 'Bot-side labels', 'Total labels', 'Bot-side %'], None)
        for i, (v, c) in enumerate(sorted(da['by_version_side'].items()), r + 1):
            ds.cell(i, 1, v)
            ds.cell(i, 2, c.get('bot', 0))
            ds.cell(i, 3, sum(c.values()))
            ds.cell(i, 4, f'=IF(C{i}=0,"",B{i}/C{i})').number_format = PCT

        dc = wb.create_sheet('Drop Audit Calls')
        lab_rows = m.get('drop_audit_rows', [])
        cols = ['Step', 'Lead', 'Call', 'Version', 'Reason', 'Side', 'Evidence', 'Bot mistake', 'Customer expected price', 'Competitor',
                'Callback requested', 'Model', 'Play recording']
        header(dc, 1, cols, [22, 16, 28, 18, 26, 12, 60, 40, 16, 16, 12, 22, 14])
        for i, x in enumerate(lab_rows, 2):
            vals = [x['stage'], x['lead'], x['call'], x.get('version'), x['reason'], x['side'], x['evidence'], x.get('bot_mistake'),
                    x.get('customer_expected_price'), x.get('competitor'), 'Yes' if x.get('callback_requested') else 'No', x.get('model')]
            for j, v in enumerate(vals, 1):
                dc.cell(i, j, v)
            rec = next((c for c in calls if c['id'] == x['call']), None)
            if rec and rec.get('recording_url'):
                c = dc.cell(i, 13, 'Play')
                c.hyperlink = rec['recording_url']
                c.font = Font(color='0563C1', underline='single')
        if lab_rows:
            n = len(lab_rows) + 1
            table(dc, f'A1:M{n}', 'DropAuditCalls')
            dc.conditional_formatting.add(f'F2:F{n}', FormulaRule(formula=['$F2="bot"'], fill=RED))
            dc.conditional_formatting.add(f'F2:F{n}', FormulaRule(formula=['$F2="customer"'], fill=GRN))
            dc.conditional_formatting.add(f'F2:F{n}', FormulaRule(formula=['$F2="platform"'], fill=YEL))
        dc.freeze_panes = 'A2'

    # ---------------- City Funnel ----------------
    cf = wb.create_sheet('City Funnel')
    ns = len(stages)
    step_rate_hdrs = [f'{stages[k]} / {stages[k - 1]}' for k in range(1, ns)]
    hdr = ['City'] + stages + ['Deals', 'DND'] + step_rate_hdrs + ['Deal / connected', 'DND rate']
    header(cf, 1, hdr, [18] + [14] * (ns + 2) + [16] * (len(step_rate_hdrs) + 2))
    cities = list(m['cities'].items())
    deal_col_idx = 2 + ns
    dnd_col_idx = 3 + ns
    r_start = 4 + ns
    for i, (city, v) in enumerate(cities, 2):
        f = v['funnel']
        cf.cell(i, 1, city)
        for j, r in enumerate(f, 2):
            cf.cell(i, j, r['count'])
        cf.cell(i, deal_col_idx, v.get('deals', f[-1]['count'] if f else 0))
        cf.cell(i, dnd_col_idx, v.get('dnd', 0))
    tot = 2 + len(cities)
    last = max(tot - 1, 2)
    cf.cell(tot, 1, 'ALL CITIES')
    for j in range(2, dnd_col_idx + 1):
        cf.cell(tot, j, f'=SUM({L(j)}2:{L(j)}{last})')
    for i in range(2, tot + 1):
        for k in range(1, ns):
            rc = r_start + k - 1
            num_c, den_c = L(2 + k), L(1 + k)
            cf.cell(i, rc, f'=IF({den_c}{i}=0,"",{num_c}{i}/{den_c}{i})').number_format = PCT
        dc_col = r_start + ns - 1
        conn_c = L(3) if ns > 1 else L(2)
        cf.cell(i, dc_col, f'=IF({conn_c}{i}=0,"",{L(deal_col_idx)}{i}/{conn_c}{i})').number_format = PCT
        dnd_r_col = dc_col + 1
        cf.cell(i, dnd_r_col, f'=IF(B{i}=0,"",{L(dnd_col_idx)}{i}/B{i})').number_format = PCT
    cf.freeze_panes = 'B2'
    if ns > 1:
        ryg(cf, f'{L(r_start)}2:{L(r_start)}{tot}', f'{L(r_start)}2', 'Targets!$B$4', MINN, 'Targets!$C$4', 'B2')
    dc_letter = L(r_start + ns - 1)
    conn_letter = L(3) if ns > 1 else L(2)
    ryg(cf, f'{dc_letter}2:{dc_letter}{tot}', f'{dc_letter}2', 'Targets!$B$8', MINN, 'Targets!$C$8', f'{conn_letter}2')
    dnd_letter = L(r_start + ns)
    ryg(cf, f'{dnd_letter}2:{dnd_letter}{tot}', f'{dnd_letter}2', 'Targets!$B$11', MINN, 'Targets!$C$11', 'B2')
    if cities:
        bc = BarChart()
        bc.type, bc.title, bc.legend = 'bar', 'Top cities: leads called', None
        top = min(len(cities), 10)
        bc.add_data(Reference(cf, min_col=2, min_row=1, max_row=top + 1), titles_from_data=True)
        bc.set_categories(Reference(cf, min_col=1, min_row=2, max_row=top + 1))
        cf.add_chart(bc, f'{L(r_start + ns + 2)}2')

    # ---------------- Daily Trend ----------------
    dt_ = wb.create_sheet('Daily Trend')
    dk = [s_['key'] for s_ in m['stages']][1:]
    hdr = ['Date (IST)', 'Calls', 'Answered', 'Human connected'] + [s_['label'] for s_ in m['stages']][1:] + ['Deals', 'Live connect rate', 'Live pitch rate']
    header(dt_, 1, hdr, [14, 10, 10, 14] + [14] * len(dk) + [10, 14, 14])
    for i, d in enumerate(m['daily'], 2):
        dt_.cell(i, 1, d['date'])
        dt_.cell(i, 2, d['calls'])
        dt_.cell(i, 3, d['answered'])
        dt_.cell(i, 4, d['human'])
        for j, k in enumerate(dk, 5):
            dt_.cell(i, j, d.get(k, 0))
        dt_.cell(i, 5 + len(dk), d['deals'])
        # live rates: connect = human / calls; pitch = pitched / connected (dk[0]=connected col E, dk[1]=pitched col F)
        dt_.cell(i, 6 + len(dk), f'=IF(B{i}=0,"",D{i}/B{i})').number_format = PCT
        dt_.cell(i, 7 + len(dk), f'=IF(E{i}=0,"",F{i}/E{i})' if len(dk) > 1 else '').number_format = PCT
    nd = len(m['daily'])
    if nd:
        lc = LineChart()
        lc.title, lc.y_axis.title = 'Daily calls and human connected', 'count'
        lc.add_data(Reference(dt_, min_col=2, min_row=1, max_row=nd + 1), titles_from_data=True)
        lc.add_data(Reference(dt_, min_col=4, min_row=1, max_row=nd + 1), titles_from_data=True)
        lc.set_categories(Reference(dt_, min_col=1, min_row=2, max_row=nd + 1))
        lc.height, lc.width = 8, 18
        dt_.add_chart(lc, f'A{nd + 4}')
        bc2 = BarChart()
        bc2.title = 'Daily deals'
        bc2.add_data(Reference(dt_, min_col=5 + len(dk), min_row=1, max_row=nd + 1), titles_from_data=True)
        bc2.set_categories(Reference(dt_, min_col=1, min_row=2, max_row=nd + 1))
        dt_.add_chart(bc2, f'K{nd + 4}')
    dt_.freeze_panes = 'B2'

    # ---------------- breakdown sheets ----------------
    def breakdown(name, src, label):
        ws = wb.create_sheet(name)
        head = [label, 'Leads'] + [r['label'] for r in m['stages']] + ['Deals', 'Deal rate (of leads)', 'Deal / connected', 'Deal / pitched']
        header(ws, 1, head, [30, 10] + [13] * len(m['stages']) + [10, 14, 14, 14])
        for i, (k, v) in enumerate(src.items(), 2):
            ws.cell(i, 1, k)
            ws.cell(i, 2, v['leads'])
            for j, r in enumerate(v['funnel'], 3):
                ws.cell(i, j, r['count'])
            dcol = 3 + len(m['stages'])
            ws.cell(i, dcol, f"={L(3 + len(m['stages']) - 1)}{i}")
            ws.cell(i, dcol + 1, f'=IF(B{i}=0,"",{L(dcol)}{i}/B{i})').number_format = PCT
            ws.cell(i, dcol + 2, f'=IF(C{i}=0,"",{L(dcol)}{i}/C{i})').number_format = PCT
            ws.cell(i, dcol + 3, f'=IF(E{i}=0,"",{L(dcol)}{i}/E{i})').number_format = PCT
        ws.freeze_panes = 'B2'
        return ws

    breakdown('By Version', m['by_version'], 'Version')
    if m.get('by_scenario'):
        breakdown('By Scenario', m['by_scenario'], 'Scenario')
    if m.get('by_quadrant'):
        breakdown('By Quadrant', m['by_quadrant'], 'Quadrant')
    breakdown('By Opening Language', m['by_opening_lang'], 'Opening language')
    breakdown('By Final Stage', m['by_final_stage'], 'Final stage')

    # ---------------- All Leads / All Calls ----------------
    al = wb.create_sheet('All Leads')
    cols = ['Lead', 'City', 'Version', 'Opening lang', 'Calls', 'Human calls', 'Final stage', 'Deal', 'Deal on call #', 'Scenario', 'Quadrant', 'Arm']
    header(al, 1, cols, [18, 14, 22, 12, 8, 12, 26, 8, 14, 14, 14, 12])
    leads_rows = m.get('lead_rows', [])
    for i, x in enumerate(leads_rows, 2):
        for j, k in enumerate(['lead', 'city', 'version', 'opening_lang', 'n_calls', 'n_human', 'final_stage', 'agreed', 'agreed_attempt', 'scenario', 'quadrant', 'arm'], 1):
            al.cell(i, j, x.get(k))
    if leads_rows:
        table(al, f'A1:L{len(leads_rows) + 1}', 'AllLeads')
        n = len(leads_rows) + 1
        al.conditional_formatting.add(f'H2:H{n}', FormulaRule(formula=['$H2=TRUE'], fill=GRN))
        al.conditional_formatting.add(f'G2:G{n}', FormulaRule(formula=['ISNUMBER(SEARCH("Negotiation",$G2))'], fill=YEL))
    al.freeze_panes = 'A2'

    ac = wb.create_sheet('All Calls')
    cols = ['Call', 'At (IST, UTC stored)', 'Lead', 'City', 'Version', 'Duration s', 'Hangup', 'Human', 'Attempt #', 'Human attempt #',
            'Capabilities switched', 'Passed stages', 'Deal', 'Opening lang', 'Customer lang', 'Play recording']
    header(ac, 1, cols, [28, 20, 16, 14, 22, 10, 22, 8, 10, 14, 30, 30, 8, 12, 12, 14])
    for i, c in enumerate(calls, 2):
        vals = [c['id'], c['at'], c['lead'], c.get('city'), c.get('version'), c.get('duration'), c.get('hangup_reason'),
                'Yes' if c.get('human') else 'No', c.get('_attempt'), c.get('_human_attempt'),
                ', '.join(c.get('capabilities_switched') or []), ', '.join(s_['label'] for s_, p in zip(m['stages'], c.get('_pass') or []) if p),
                'Yes' if c.get('_success') else 'No', c.get('opening_lang'), c.get('customer_lang')]
        for j, v in enumerate(vals, 1):
            ac.cell(i, j, v)
        if c.get('recording_url'):
            cell = ac.cell(i, 16, 'Play')
            cell.hyperlink = c['recording_url']
            cell.font = Font(color='0563C1', underline='single')
    if calls:
        table(ac, f'A1:P{len(calls) + 1}', 'AllCalls')
    ac.freeze_panes = 'A2'

    # ---------------- Definitions ----------------
    de = wb.create_sheet('Definitions')
    header(de, 1, ['Term', 'Definition'], [34, 120])
    for i, (k, v) in enumerate(m.get('definitions', []), 2):
        de.cell(i, 1, k).alignment = WRAP
        de.cell(i, 2, v).alignment = WRAP

    wb.save(a.out)
    print('wrote', a.out, 'sheets:', wb.sheetnames)


if __name__ == '__main__':
    main()
