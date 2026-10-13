---
name: callkaro-kpi-manager
description: Set up and read CallKaro KPI Manager, which compares an agent's business metrics to targets every day and writes a Root Cause Analysis report when one misses. Use when adding KPI data sources (API endpoint or Python), defining metrics and targets, writing the RCA prompt, choosing the RCA model, reading RCA reports and root causes, working the Pending Tasks board, running a manual RCA, or debugging why a report was not generated.
---

# CallKaro KPI Manager

Docs: https://docs.callkaro.ai/kpi-manager/introduction. Sidebar label: KPI Manager (dashboard `/dashboard/kpi-manager-dashboard`).

KPI Manager pulls the real value of each metric daily, compares it to the target, and when an agent misses it runs an RCA over that day's calls. The report names the cause, quotes evidence, points at the prompt section, and gives the literal fix. It does not audit calls (it consumes AI Auditor results, see `callkaro-ai-auditor`), does not dial, and never changes an agent by itself.

## Two places

| Surface | Path | For |
|---|---|---|
| Setup | Agent, KPI Manager tab | Data sources, metrics, RCA prompt, RCA model, Auto RCA toggle. Per agent. Needs a saved agent first. |
| Dashboard | Sidebar, KPI Manager | History (Charts, RCA), Pending Tasks, Run Manual RCA, across all agents. |

## The daily pass

Runs 5:00 AM IST over the previous calendar day: Collect (calls data sources), Measure (actual vs target, always recorded), Analyse, Deliver (stored, PDF emailed to the agent owner, root causes become Pending Task cards).

An RCA only runs when all four hold: actual is below target, the shortfall is at least 1 percentage point, the RCA prompt covers that metric, Auto RCA is on for the agent. Whichever blocked it is written in the day-wise timeline (History, RCA).

## Setup

### 1. Data source (Data Sources panel)

| Type | You provide | Reference a field as |
|---|---|---|
| API Endpoint | Unique Name, URL, method POST, headers, parameters (`phone_number` always sent, cannot be removed). Dummy cURL shows the exact request, test it before saving. | `<name>.data.<field>`. Response must be wrapped `{ "data": { ... } }`. |
| Python Code | Unique Name, parameters, body of `async def generate_kpi_data(payload: list) -> dict`. `payload` is one entry per lead with `phone_number` plus chosen params. Return one JSON-serialisable dict, no wrapper. `httpx` available without import. | `<name>.<field>` |

A short diagnostic string returned from a Python source (a `message` key) is also read by the RCA agent as context.

### 2. KPI metric (KPI Metrics, Add)

Fields: KPI Metric (descriptive name, the RCA reasons about it, `Conversion Rate` not `metric_2`), Source (`<source_name>.<field>`), Value (target percent). Every agent already has `connected_to_conversion_percentage` (share of connected calls that converted), calculated by the platform, fixed name and source, only its target is editable.

### 3. RCA prompt

The highest-leverage field, up to 10,000 characters, blank is valid (all calls, all metrics). Use it for scope (region, lead source, campaign, outcome, one metric), exclusions (sub-5-second disconnects are dialer artefacts), method (converted vs not at the pricing objection), priority, specific call ids or windows, business context. Metrics the prompt does not mention are still measured and charted but never trigger an analysis. "Generate with AI" drafts one.

### 4. Header controls

Auto RCA (default on; off stops only the nightly run, manual runs still work). RCA Model: GPT-5.4 (default), GPT-5.6 Sol, GPT-5.6 Luna, Claude Opus 4.6, Claude Sonnet 4.6.

### 5. Save

Applies to the next run only. Reports already generated do not change.

## Reading results

Dashboard filter (agents, date range, then Search; Reset returns to all agents, last 7 days) drives History and Pending Tasks together. History, Charts: actual vs target per agent per metric per day. History, RCA: one card per agent per day with the missed metrics (Expected, Actual, Gap), Automatic or Manual tag, the day-wise timeline (each event Done, Attention, Failed, Skipped or Info), and Preview or Download for the PDF.

## An RCA report

Sections: KPI Metrics Missed, Summary, Root Causes and Recommended Fixes, Updates on Past Findings. Per root cause: Cause, Category, Evidence (links to audited calls), Confidence (High, Medium, Low), Severity (Very High, High, Medium, Low, Very Low, Negligible), Prompt Section, Prompt Excerpt (the exact offending text), Recommended Fix (literal replacement wording for prompt issues), Metric Impact (percentage points), Recurrence (new or recurring with first-seen date).

Categories: Agent behaviour, Function call or integration, Post-call measurement (instrumentation artefact, not a real outcome), System or technical, KPI target unrealistic, External lead quality (only with an executable action), Other. "Need more data" is never a root cause; thin evidence is stated as insufficient data.

## Pending Tasks board

Columns: Action Items (new cards land here), In Progress, Testing in A/B, Live in Prod, Done, Rejected. A card can be assigned to a person or to AI FDE, given target agent versions, re-severity'd, commented on, given attachments, dragged or moved, or created by hand. Nothing reaches AI FDE unless a person assigns the card; if AI FDE is already working that agent version the new fix queues until the current one is Done or Rejected. Read the evidence and prompt excerpt before assigning.

From a terminal, use `cku kpi` (see `callkaro-cli`, section KPI manager). It reads and writes this same board. Rejected is how a card is retired, there is no delete.

## Run Manual RCA

Run Manual RCA view: pick the agent, filter by date and other criteria, select calls (count shown), Run RCA, then set Target (%), RCA Model and an optional RCA prompt (this run only, does not overwrite the saved one). Works even with Auto RCA off. Takes a few minutes in the background; the report lands in History, RCA tagged Manual. Use it to test a prompt idea, chase one complaint, or analyse one campaign.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| No report for a day | Every metric met target, shortfall under 1 point, RCA prompt did not cover the metric, or Auto RCA off. Open the timeline, it states which. |
| "could not be measured" | Nothing came back from the source that day. Check the timeline entry and that the metric's Source path matches the real response. |
| Metric value always empty | Almost always the reference. API sources need the extra `.data`, Python sources do not. |
| Endpoint "partly delivered" | Batch was split and some parts failed. Timeline shows counts and status codes. |
| "Save the agent first" | Data sources attach to a saved agent. Save, then reopen the tab. |
| Report says data insufficient | Too few audited calls that day. Widen the prompt scope or wait for a busier day. |
| Same cause keeps recurring | Flagged recurring with first-seen date. The card may never have been assigned, or the fix reached only part of the traffic. Check the board. |
| Config changed, report identical | Changes apply to the next run. Use Run Manual RCA to see the effect now. |

Practices that matter: descriptive metric names, minimal endpoint parameters, test the cURL before saving, scoped RCA prompt with explicit exclusions, targets the agent has actually hit before, and moving cards through the board so the next report can say whether the fix worked.

## Defaults and access

Run time 5:00 AM IST over the previous day. Trigger threshold 1.0 point below target. Auto RCA on. Default model GPT-5.4. Prompt max 10,000 characters. Recurrence window 14 days. Dashboard default range 7 days. No automatic handoff to AI FDE. Report email goes to the agent owner. Permissions: view dashboard needs Analytics View, view config needs Agents View, save config or run manual RCA needs Agents Create, delete config needs Agents Delete.
