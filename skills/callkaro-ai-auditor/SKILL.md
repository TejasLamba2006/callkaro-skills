---
name: callkaro-ai-auditor
description: Set up and read CallKaro AI Auditor (dashboard labels Audit strategy and Audit Reports), which scores sampled calls for transcription, callflow, function and post-call accuracy. Use when writing an audit strategy, choosing audit filters, model and sampling, adding extra variables, reading strategy or batch reports, understanding batch status, scores and issue severity, or turning an audit finding into an agent fix.
---

# CallKaro AI Auditor

Docs: https://docs.callkaro.ai/ai-auditor/introduction. Dashboard labels: **Audit strategy** (inside an agent) and **Audit Reports** (sidebar, `/dashboard/audit_reports`).

AI Auditor reviews calls automatically and returns scores, issues and recommended fixes. It checks Transcription Quality, Callflow Adherence, Function Accuracy, Postcall Accuracy, plus whatever the strategy defines (customer experience, rules). KPI Manager reads these audits as evidence (see `callkaro-kpi-manager`).

Timing: audits run with a two-hour delay, each hourly batch covers one hour of calls. A batch created at 11:00 AM holds eligible calls from 8:00 to 9:00 AM.

## Set up a strategy

Agents, open a voice agent, Audit strategy in the header, Create, give it a clear name.

| Field | Notes |
|---|---|
| Audit Strategy | Required. Plain language on what to check, e.g. polite greeting, understood the request, correct information, confirmed next step; flag interruptions, repeated questions, wrong promises, missed actions. |
| Audit Model | Required. Model used for auditing. |
| Call Flow Summary | Short ordered description of a good call (greet, confirm request, solution, confirm next step, close). |
| Audit Filters | Agent Version, Call Type, Hangup Reason, Call Duration, Drop-Off Reason, Conversion Status, Post-Call Metrics filters. Empty means no limit. Clear Filters resets. Start with something like completed calls over 30 seconds. |
| Calls to Audit per Hour (%) | Share of matching calls reviewed each hour. |
| Maximum Calls per Hour | Hard cap per hour. Start small, raise once results look useful. |
| Extra Variables | Per-call extra outputs. Types: Text, Selector (fixed choices), Boolean, Issue (did a problem occur), Number. Each needs a unique Variable Name and Detection Criteria or Extraction Instructions, e.g. `agent_interrupted_customer`, true when the agent speaks over the customer. Renaming or deleting changes what future audits return. |

Generate with AI builds instructions from the agent's published call script (Edit with AI when instructions exist): add optional instructions, Generate, review, Accept Changes. **Accept Changes only updates the draft**, still press Save or Update.

Enable and Disable also only change the draft. Press **Save** (new) or **Update** (existing). An enabled saved strategy audits matching calls automatically, a disabled one stays saved and idle. The selector shows Active or Unsaved; save an unsaved strategy before creating another. Audit Guide in the agent header has in-product help.

Start with one simple strategy and add checks after reading the first results.

## From the CLI

`cku audit-strategies list <agentId>`, `cku audit-strategies models`, `cku audit-strategies create <agentId> --strategy "..."`. See `callkaro-cli`. Reads are safe, creating or enabling one starts spending credits on live calls, so confirm first.

## Audit Reports

Sidebar, Audit Reports. Choose Strategy or Batch, optionally pick agents, set dates (default last 7 days including today), Search. Reset clears the agent filter and restores dates.

| View | Shows |
|---|---|
| Strategy | Per strategy: Agent Name, Transcriber, Callflow, Postcall and Function accuracy, Total Calls. Use for trends. |
| Batch | Each automatic run: agent, strategy, audit time, status, total, completed and failed calls, quality scores. Use to check one run. |

Batch status: Queued (waiting), Running, Completed, Partial Failed (some calls failed), Failed. "No audit reports to display" means nothing matched: check the strategy is enabled and saved, calls match its filters, agent and dates are right, and enough time has passed.

## Reading a report (View details)

Two tabs. **Summary**: Total Calls, Average Score, Calls Below 80% Score, Total Issues, credits used, grouped into Callflow Adherence, Function Accuracy, Postcall Accuracy, Transcription Quality. Boolean and Issue extra variables also appear here with links to the matching calls. **Call Audits**: one row per audited call with overall score and Postcall, Transcriber, Callflow, Function scores; filter by date, agent version, duration, disconnect reason, conversion status; View issues opens the call.

Severity: Critical (review now), High (soon), Medium (when improving the agent), Low (minor). Start with Calls Below 80% and Critical issues.

Issue panel: Problem, Severity, Proof (call evidence), Expected, Actual, Recommended Fix. Categories: Transcription Issues, Function Call Issues, Postcall Variable Issues, Callflow Adherence Issues, System Log Errors. Extra variable values show in the same panel. Re-transcription (when available) compares the call to the improved transcript, which separates a transcription fault from agent behaviour.

## Turning findings into fixes

1. Read Proof, Expected, Actual and Recommended Fix.
2. Check the same issue appears across several calls, never change a live agent from one call.
3. Create or edit a safe test version of the agent, fix the prompt, function, variable, voice or transcriber.
4. Re-test before publishing. Use `callkaro-agent-review-debug` for root cause (fault layer, smallest fix, no stacking NEVER lines) and `callkaro-qa-framework` to verify.

AI FDE can investigate the finding (Ask mode) or prepare the fix in a new version (Plan mode, approve before it builds).
