---
name: callkaro-kpi-manager
description: Set up and read CallKaro KPI Manager and KPI Reports, which compare an agent's business metrics to targets, build scheduled A4 KPI Reports (tables, charts, text boxes, custom expression variables), and write a Root Cause Analysis report when a metric misses. Use when adding KPI data sources (API endpoint, Python, or Expression), defining metrics and targets, building or previewing KPI Reports, exporting report PDFs, writing the RCA prompt, choosing the RCA model, reading RCA reports and root causes, working the Pending Tasks board, running a manual RCA, or debugging why a report was not generated.
---

# CallKaro KPI Manager & KPI Report

Docs: https://docs.callkaro.ai/kpi-manager/introduction. Sidebar label: KPI Manager (dashboard `/dashboard/kpi-manager-dashboard`).

KPI Manager pulls the real value of each metric daily, compares it to the target, and when an agent misses it runs an RCA over that day's calls. Its **Report** tab builds a scheduled A4 KPI Report (stat tiles, tables, charts, text boxes, and custom expression variables) emailed on a configurable schedule and exportable as a PDF. It does not audit calls (it consumes AI Auditor results, see `callkaro-ai-auditor`), does not dial, and never changes an agent by itself.

## Two places

| Surface | Path | For |
|---|---|---|
| Setup | Agent, KPI Manager tab (`?mode=kpi`) | 4 sections: **RCA Prompt**, **Data Sources** (API Endpoints, Python Code, Expression), **KPI Metrics**, and **Report** (A4 report builder, custom variables, schedule, recipients, PDF export). Header toggles: **Auto RCA** and **Auto Report**. Per agent; needs a saved agent first. |
| Dashboard | Sidebar, KPI Manager | History (Charts, RCA), Pending Tasks, Run Manual RCA, across all agents. |

## The daily pass

Runs 5:00 AM IST over the previous calendar day: Collect (calls data sources), Measure (actual vs target, always recorded), Analyse, Deliver (stored, PDF emailed to the agent owner, root causes become Pending Task cards).

An RCA only runs when all four hold: actual is below target, the shortfall is at least 1 percentage point, the RCA prompt covers that metric, Auto RCA is on for the agent. Whichever blocked it is written in the day-wise timeline (History, RCA).

### Auto RCA vs Auto Report email matrix

| Auto RCA | Auto Report | What is emailed |
|---|---|---|
| On | Off | RCA emails only (when a metric misses) |
| Off | On | The KPI Report only, on its schedule |
| On | On | Both — and every RCA email also attaches the KPI Report for the same day |
| Off | Off | Nothing |

## Setup

### 1. Data source (Data Sources panel)

| Type | You provide | Reference a field as |
|---|---|---|
| API Endpoint | Unique Name, URL, method POST, headers, parameters (`phone_number` -> `user_phone_number` always sent, cannot be removed). Dummy cURL shows the exact request; test it before saving. | `<name>.data.<field>` (in KPI Metrics) or `source:<name>.data.<field>` (in Report). Response must be wrapped `{ "data": { ... } }`. |
| Python Code | Unique Name, parameters, body of `async def generate_kpi_data(payload: list) -> dict`. `payload` is one entry per lead with `phone_number` plus chosen params. Return one JSON-serialisable dict, no wrapper. `httpx` available without import. Verified via `POST /utils/verify-code` on save. | `<name>.<field>` (in KPI Metrics) or `source:<name>.<field>` (in Report). |
| Expression | Unique Name (`^[A-Za-z][A-Za-z0-9_-]{0,63}$`), mode (`expression` or `conditions`), rule, and `consider_for` (`all` for All calls or `unique` for Unique receipts). Counts calls matching your rule without writing Python or hosting an API. | `<name>.count`, `<name>.total`, `<name>.pct` (in KPI Metrics, e.g. `car_sold.pct`) or `source:<name>.count` / `.total` / `.pct` (in Report). |

A short diagnostic string returned from a Python source (a `message` key) is also read by the RCA agent as context.

### 2. KPI metric (KPI Metrics, Add)

Fields: KPI Metric (descriptive name, the RCA reasons about it, `Conversion Rate` not `metric_2`), Source (`<source_name>.<field>`), Value (target percent). Every agent already has `connected_to_conversion_percentage` (share of connected calls that converted), calculated by the platform, fixed name and source, only its target is editable.

### 3. RCA prompt

The highest-leverage field, up to 10,000 characters, blank is valid (all calls, all metrics). Use it for scope (region, lead source, campaign, outcome, one metric), exclusions (sub-5-second disconnects are dialer artefacts), method (converted vs not at the pricing objection), priority, specific call ids or windows, business context. Metrics the prompt does not mention are still measured and charted but never trigger an analysis. "Generate with AI" (`POST /openai-tools/generate-rca-prompt-draft`) drafts one.

### 4. Header controls

Auto RCA (`nightly_rca_enabled`, default on; off stops only the nightly run, manual runs still work). Auto Report (`report_enabled`, default off). RCA Model (`rca_model` + `rca_llms`): `gpt-5.6-luna` (default, `azure-openai`), `gpt-5.6-sol` (`azure-openai`), `callkaro/krishna-2.5` (`callkaro`), Claude Sonnet 4.6 (`bedrock`), Claude Opus 4.6 (`bedrock`).

### 5. KPI Report builder (Report section)

The Report section lays out an emailed report on one or more A4 sheets (`794 x 1123` px per page, `40` px margin; two items at 50% width sit side by side) and previews live values over the configured gap via `POST /kpi-manager/:agentId/report/preview` or exports a PDF via `POST /kpi-manager/:agentId/report/export`.

#### Schedule & recipients (`report_config`)
- `recipients`: up to 10 email addresses.
- `min_trigger_time` and `max_trigger_time`: `HH:mm` in **IST** (15-minute steps).
- `interval_hours` (Gap): `1, 2, 3, 4, 6, 8, 12, 24, 48, 72, 168` (7 days).
  - Examples: `08:00 – 20:00` every `4h` sends at 8 AM, 12 PM, 4 PM, 8 PM IST.
  - When `interval_hours >= 24`, `max_trigger_time` is unused and automatically equals `min_trigger_time` (sends once at `min_trigger_time`).
  - Each report covers calls since the previous report (first report of the day covers overnight). Saving never backfills a past trigger time.

#### Variable references (`${...}` in text/tables, or `refs`/`y_axis` in charts)
- **Built-in** (`builtin:<key>`, or bare `${<key>}` in text/table cells):
  `total_calls`, `connected_calls`, `connected_pct`, `unique_receipts`, `unique_connected`, `unique_connected_pct`, `converted_calls`, `converted_pct`, `unique_converted`, `avg_connected_duration`, `drop_off_reasons` (breakdown), `hangup_reasons` (breakdown).
- **Post-call variables**: `postcall:<varName>` or `postcall:<varName>#<base>` where `<base>` is `all | connected | unique | unique_connected` (breakdown of every value and its count/percentage).
- **Custom variables** (`report_config.custom_variables`): `custom:<name>` or `custom:<name>#<base>` (`all | unique`). Name must be lowercase `snake_case` (`^[a-z][a-z0-9_]{0,63}$`).
- **Data sources**: `source:<apiName>.data.<field>`, `source:<pyName>.<field>`, `source:<exprName>.count` (`.total`, `.pct`).
- **KPI metrics**: `metric:<metricName>` (shows actual % vs target %).

#### Writing expressions (for Custom Variables & Expression Data Sources)
- **Fields**: `post_call.<name>`, `metadata.<key>`, `is_connected`, `is_converted`, `hangup_reason`, `call_duration`.
- **Operators**: `&&`, `||`, `!`, `==`, `!=`, `>`, `>=`, `<`, `<=`, and `in ['a', 'b']`.
- A bare field like `post_call.is_car_sold` means "is true". Text comparisons are case-insensitive.
- Examples (from MG Motors Test Drive Qualifier `6a888bb8bbb7ca9f239df560` on Vapour Sarjapur):
  - `is_connected && post_call.test_drive_booked == 'YES'`
  - `is_connected && post_call.visit_preference == 'HOME_VISIT'`
  - `post_call.call_outcome in ['FOLLOW_UP_REQUESTED', 'ESCALATED_TO_HUMAN']`

#### Canvas elements (`report_config.elements`)
1. **Text box** (`type: "text"`): `content` (with `${...}` interpolation), `x`, `y`, `w` (default 360), `h` (optional), `style: { bold, italic, underline, size, color, align }`.
2. **Table** (`type: "table"`): `header: true`, `cells: string[][]` (1..8 rows x 1..8 cols; each cell supports `${...}`), `x`, `y`, `w` (default 480).
3. **Chart** (`type: "chart"`, `chart_type: "tiles" | "bar" | "line" | "pie" | "funnel" | "table"`):
   - `title`: optional chart heading.
   - `x_axis`: `null` (for `tiles` and unsplit `funnel`), `"metrics"` (compare `y_axis` metrics), or a dimension: `"dim:time_hour"`, `"dim:time_day"`, `"dim:hangup_reason"`, `"dim:drop_off_reason"`, `"dim:is_connected"`, `"dim:converted"`, `"dim:direction"`, `"dim:postcall:<varName>"`, `"dim:metadata:<key>"`.
   - `y_axis` and `refs`: array of variable references (up to 12 for multi-Y charts; 1 for `pie`).
   - `stack_by`: optional dimension (`bar` / `line` when `x_axis` is a `dim:*`).
   - `options`: `{ direction?: "horizontal" | "vertical", compare_previous?: boolean }`.
   - Note: email body renders tiles, tables, and text boxes; charts are rendered in the attached PDF.

### 6. CLI commands (`cku kpi report` & `cku kpi config`)

Always use `cku kpi` rather than raw `PUT /kpi-manager/:agentId` so all 10 top-level fields on the document are preserved:

```bash
cku kpi config <agentId> [--json]                       # inspect full 10-field KPI Manager + Report config
cku kpi report schema                                   # print full element, variable & dimension reference
cku kpi report get <agentId> [--json]                   # show schedule, recipients, custom vars, elements
cku kpi report set <agentId> --enable --recipients "a@b.com" --min-trigger 08:00 --max-trigger 20:00 --interval 24
cku kpi report add-var <agentId> --name booked_test_drives \
  --expression "is_connected && post_call.test_drive_booked == 'YES'" --consider-for all,unique
cku kpi report add-element <agentId> --type tiles --title "Headline" \
  --refs "builtin:total_calls,builtin:connected_calls,builtin:connected_pct,custom:booked_test_drives#all"
cku kpi report add-element <agentId> --type bar --title "Calls by Car Model" \
  --x-axis "dim:postcall:car_name" --refs "builtin:connected_calls"
cku kpi report add-element <agentId> --type table \
  --cells '[["Metric","Value"],["Triggered","${total_calls}"],["Connected","${connected_pct}"],["Booked","${custom:booked_test_drives}"]]'
cku kpi report preview <agentId> [--interval 168] [--json]   # evaluate live numbers & chart series now
cku kpi report export <agentId> [--file report.pdf]          # render and download the A4 PDF report
```

## Reading results

Dashboard filter (agents, date range, then Search; Reset returns to all agents, last 7 days) drives History and Pending Tasks together. History, Charts: actual vs target per agent per metric per day. History, RCA: one card per agent per day (`GET /v1/audit-reports/daywise`) with the missed metrics (Expected, Actual, Gap), Automatic or Manual tag, the day-wise timeline (`GET /v1/audit-reports/daywise/:agentId/timeline`), and Preview or Download for the PDF (`GET /v1/audit-reports/daywise/:agentId/:rcaDate/pdf`).

## An RCA report

Sections: KPI Metrics Missed, Summary, Root Causes and Recommended Fixes, Updates on Past Findings. Per root cause: Cause, Category, Evidence (links to audited calls), Confidence (High, Medium, Low), Severity (Very High, High, Medium, Low, Very Low, Negligible), Prompt Section, Prompt Excerpt (the exact offending text), Recommended Fix (literal replacement wording for prompt issues), Metric Impact (percentage points), Recurrence (new or recurring with first-seen date).

Categories: Agent behaviour, Function call or integration, Post-call measurement (instrumentation artefact, not a real outcome), System or technical, KPI target unrealistic, External lead quality (only with an executable action), Other. "Need more data" is never a root cause; thin evidence is stated as insufficient data.

## Pending Tasks board

Columns: Action Items (new cards land here), In Progress, Testing in A/B, Live in Prod, Done, Rejected. A card can be assigned to a person or to AI FDE, given target agent versions, re-severity'd, commented on, given attachments, dragged or moved, imported in bulk (`POST /pending-tasks/import`), or created by hand. Nothing reaches AI FDE unless a person assigns the card; if AI FDE is already working that agent version the new fix queues until the current one is Done or Rejected. Read the evidence and prompt excerpt before assigning.

From a terminal, use `cku kpi` (see `callkaro-cli`, section KPI manager). It reads and writes this same board. Rejected is how a card is retired, there is no delete.

## Run Manual RCA

Run Manual RCA view: pick the agent, filter by date and other criteria, select calls (count shown), Run RCA, then set Target (%), RCA Model and an optional RCA prompt (this run only, does not overwrite the saved one). Works even with Auto RCA off. Takes a few minutes in the background; the report lands in History, RCA tagged Manual. Use it to test a prompt idea, chase one complaint, or analyse one campaign.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| No report for a day | Every metric met target, shortfall under 1 point, RCA prompt did not cover the metric, or Auto RCA off. Open the timeline, it states which. |
| "could not be measured" | Nothing came back from the source that day. Check the timeline entry and that the metric's Source path matches the real response. |
| Metric value always empty | Almost always the reference. API sources need the extra `.data`, Python sources do not, Expression sources need `.count`, `.total` or `.pct`. |
| Endpoint "partly delivered" | Batch was split and some parts failed. Timeline shows counts and status codes. |
| "Save the agent first" | Data sources and reports attach to a saved agent. Save, then reopen the tab. |
| Report preview shows 0 calls | Default preview window is `interval_hours` (24h). Pass `--interval 168` (7 days) on `cku kpi report preview` to test over a wider window. |
| Report says data insufficient | Too few audited calls that day. Widen the prompt scope or wait for a busier day. |
| Same cause keeps recurring | Flagged recurring with first-seen date. The card may never have been assigned, or the fix reached only part of the traffic. Check the board. |
| Config changed, report identical | Changes apply to the next run. Use Run Manual RCA to see the effect now. |

## Defaults and access

Run time 5:00 AM IST over the previous day. Trigger threshold 1.0 point below target. Auto RCA on, Auto Report off. Default model `gpt-5.6-luna`. Prompt max 10,000 characters. Recurrence window 14 days. Dashboard default range 7 days. No automatic handoff to AI FDE. Report email goes to the agent owner (plus `report_config.recipients` for scheduled KPI Reports). Permissions: view dashboard needs Analytics View, view config needs Agents View, save config or run manual RCA needs Agents Create, delete config needs Agents Delete.
