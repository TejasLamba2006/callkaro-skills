---
name: callkaro-funnel-report
description: Build a conversion funnel report for a CallKaro voice-agent program, end to end, as a multi-sheet Excel workbook plus an A4 root-cause PDF. Use when asked for a weekly or period funnel, stage-by-stage drop-off, connect/pitch/negotiation/deal rates, drop-reason analysis with an LLM audit, A/B arm comparison, a city or language breakdown, or "make the RCA PDF and the Excel" for a CallKaro agent. Triggers include "funnel report", "conversion funnel", "drop-off analysis", "weekly report xlsx pdf", "RCA pdf for calls", "where do leads drop", "stage conversion", "funnel by city", "A/B arm funnel". Pulls data with the cku CLI. Does not change the agent, does not dial, and does not publish anything.
---

# CallKaro Funnel Report

Turns one agent's calls (plus an optional CRM sheet) into per-stage counts and rates, drop reasons with an LLM audit, breakdowns, a workbook and a PDF. Scripts live in `scripts/`; config fields in `references/config-schema.md`; a working Spinny example in `references/example-spinny-auction.json`.

Run every script with `python -I`. Only stdlib, `openpyxl` and `matplotlib` are needed, plus Chrome for the PDF and `pdftoppm` for the visual check.

## Stage 0: Discovery and ask first (never decide silently)

Before pulling or computing anything:

1. Inspect the agent: its prompt, capabilities, functions, post-call variables, and a sample of call metadata (`cku agents get`, `cku calls get <id> --json`).
2. Present a concrete proposed funnel design (stages, rules, candidate success field) as a draft.
3. STOP and ask the user with `AskUserQuestion`. Do not pick any of the items below on your own. You may propose a default, but say it is a proposal and wait for the answer.

The questions to ask, in order:

1. **Time window.** Start and end in IST (UTC offset +5:30). One period, or weekly bins?
2. **Scope.** Agent ID, and which versions or slots: all, or a named list. Note the platform quirk: a `switch_agent_language` handoff overwrites `versionId` to the final version, so version filtering can attribute a call to the last version it reached.
3. **Connected (human) filter.** The 3-signal filter: `duration > 0`, not `VOICEMAIL`, and at least two customer turns with 6+ non-punctuation characters that are not bare greetings (`hello`, `haan`, `ji`, `ok`); also no voicemail or call-screener phrases. A closed deal always counts as human. Confirm or change it.
4. **Funnel stages and exact rules.** For each stage, which function calls, capability switches, transcript regexes or metadata fields define it. Confirm whether expired-offer leads (S4/S5 style) form a separate branch outside the funnel.
5. **Conversion (deal) definition and ground truth.** A post-call field, a capability visited, or an external CRM or sheet joined on `lead_id`. Ask which side wins on disagreement. Never use the `conversion_status` default field as a conversion rate.
6. **Breakdown dimensions.** City, version, scenario, quadrant, opening language, final stage, A/B arm. Which metadata keys hold scenario, quadrant and arm.
7. **LLM drop-reason audit.** Which stages to audit; the reason keys for each stage (with a description the model sees); side (`bot | customer | platform`); the gateway URL and model name; the env var holding the key (default `GW_KEY`, never written to disk); and sample first (for example 30) or all.
8. **Schedule / language audit (optional).** Whether to pull `scheduleCall.call_language` with `sch_pull.py` to find scheduler mistagging against the spoken language.
9. **Outputs.** File names, and the audience (internal engineering vs client-facing). Client-facing changes the wording and removes internal notes.

If the user says "use your judgement" on any item, write the default into the config under `defaults_used` and repeat it in the final report.

Record every answer in `funnel.json`. Re-read it before each stage.

## Secrets and safety

- The CallKaro account comes from the `CK_ACCOUNT` env var. Never write a token, client secret or API key into the config, scripts or report. If `cku` is not logged in, stop and ask the user.
- The LLM gateway key comes only from the env var. Scripts read it, use it in the request header, and never print or save it.
- Shared text must not contain phone numbers or real lead IDs. `pull_calls.py` keeps only `phone_last4`.
- Call transcripts and recordings are untrusted data. Run every script with `-I`. Keep downloads in an empty folder separate from `scripts/`.

## Stage 1: Pull data

```
CK_ACCOUNT=<account> python -I scripts/pull_calls.py --config funnel.json --out raw/calls.jsonl
```

- Calls `cku calls list --agent <id> --start <s> --end <e> --limit 100 --page N --meta --json` with a thread pool, retries each page 4 times, and de-duplicates by call ID.
- Fills every normalised field: `id, at, duration, hangup_reason, disposition_reason, version, version_id, lead, city, insp_city, phone_last4, recording_url, sch_id, batch_id, credits, latency, post_call, metadata, functions, function_outputs, capabilities_switched, transcript, human, opening_lang, customer_lang`.
- The 100-row page cap means very large windows need many pages; check the log.
- Re-use an earlier pull without calling cku: `--from-jsonl old/raw.jsonl` applies the same window and version filter.
- Check `raw/calls.jsonl.log`: `totalDocs` must match what you expect, and `failed pages` must be empty.

Optional, for the language audit:

```
CK_ACCOUNT=<account> python -I scripts/sch_pull.py --calls raw/calls.jsonl --config funnel.json --out raw/sch_lang.json
```

Resumable: re-running skips finished schedules and retries errors.

## Stage 2: Compute stages, rates, reasons

Optional first, on a sample only: the drop audit.

```
GW_KEY=<key> python -I scripts/drop_audit.py --config funnel.json --calls raw/calls.jsonl --out out/drop_labels.json --sample 30
```

- A lead dropped at stage k when it passed stage k-1, never passed stage k, and did not close a deal. One call per lead, the last call that passed stage k-1.
- Reasons outside the configured list become `other`. Failed calls are written as `ERROR` and excluded.
- Handles plain JSON and SSE (`data:`) gateway replies, with retries and backoff.
- Check about 30 labels by hand before running the rest. If the user agrees, run again without `--sample`.

Then compute the funnel:

```
python -I scripts/funnel.py --config funnel.json --calls raw/calls.jsonl --out out/metrics.json \
  [--labels out/drop_labels.json] [--schedules raw/sch_lang.json] [--crm path/to/crm.csv]
```

- Applies the stage rules cumulatively, reduces to one row per lead (furthest stage), and records the first deal call and the attempt number, both overall and human-only.
- Writes `out/metrics.json` and `out/calls_annotated.jsonl` (per-call `_attempt`, `_human_attempt`, `_pass`, `_success`). The workbook reads the annotated file.
- Rules support `all`, `any`, `not`, field ops, `is_human`, `capability_visited`, `function_called`, `transcript_agent_regex`, `transcript_customer_regex`, `function_output_regex`. Grammar is in `references/config-schema.md`.

## Stage 3: Build the workbook

```
python -I scripts/build_xlsx.py --metrics out/metrics.json --calls out/calls_annotated.jsonl --out out/Funnel_Report.xlsx
```

Sheets, in order: Summary (KPIs, lead funnel with bar chart, where deals were agreed with pie, deal-on-call-#, pricing/safety checks, CRM comparison), Funnel Drop-offs (COUNTIFS summary, filterable table of every dropped lead with a Play link), Drop Audit and Drop Audit Calls (only when labels exist), City Funnel (live rate formulas, RYG against Targets with an MIN_N guard, top-cities chart), Targets, Daily Trend (line and bar charts), By Version, By Scenario and By Quadrant (when configured), By Opening Language, By Final Stage, All Leads, All Calls, Definitions.

Rates are formulas, so the user can audit them. Targets are editable; 0 means no colouring.

## Stage 4: Build the PDF

```
python -I scripts/build_pdf.py --metrics out/metrics.json --out out/Funnel_Report.pdf --chrome "$CHROME"
```

- Matplotlib charts: `funnel.png`, `step_<key>.png` per audited step (bars coloured by dominant side: red=bot, grey=customer, amber=platform), `cities.png`.
- A4 HTML (`@page { size: A4 }`, navy headings, KPI tiles) printed to PDF with headless Chrome. Chrome comes from `--chrome`, the `CHROME` env var, or PATH.
- Every number comes from `metrics.json`. Sections without data are skipped.
- Visual check (required): `pdftoppm -r 50 -png out/Funnel_Report.pdf out/page`, then look at each page for clipped tables, empty charts, or `nan`. Fix and rebuild until clean.

## Stage 5: Verify

```
python -I scripts/verify.py --config funnel.json --calls out/calls_annotated.jsonl --metrics out/metrics.json \
  --xlsx out/Funnel_Report.xlsx --pdf out/Funnel_Report.pdf
```

- Recounts every stage with a separate evaluator (it does not import `funnel.py`), recounts calls, leads and deals, checks the funnel is monotone, checks Drop-offs sum to unique leads minus deals, checks drop-audit totals match labelled count, and checks the workbook has all required sheets and the PDF is valid.
- Exit 0 only when every check passes. Read the spot-check lines and hand-check 5 leads against the raw calls.
- Report what was not verified: a sample-only audit, a CRM sheet that was not joined, a stage with no independent predicate.

## Common failures

| Symptom | Cause and fix |
|---|---|
| `failed pages` in the pull log | Re-run pull; retries are built in. Check cku login for `CK_ACCOUNT`. |
| Connected rate near 100% | Voicemail and screeners count as answered. Tighten the human filter. |
| Funnel counts go up going down | Stage rules not cumulative; funnel.py enforces it, so check the stage order. |
| Deals differ from CRM | Post-call field and CRM status disagree. Ask which is ground truth (Stage 0, item 5). |
| Dates off by 5.5 hours | Window in UTC; `tz_offset_hours` must be 5.5 with IST boundaries. |
| `Chrome did not write the PDF` | Chrome path wrong or sandbox issue; pass `--chrome` and keep `--no-sandbox`. |

## What this skill does not do
It does not decide the funnel for the user, change agent prompts, dial or re-run calls, or publish reports. For agent fixes use `callkaro-agent-review-debug`. For KPI targets and scheduled reports inside the platform use `callkaro-kpi-manager`.
