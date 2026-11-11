---
name: callkaro-qa-ops
description: Operate and debug CallKaro day to day. Use when monitoring calls, auditing, reading RCA, managing feedback, batch tables, scheduled queues, analytics, onboarding, pricing, AI FDE help.
---

# CallKaro QA and Ops

## AI FDE

Chat assistant for voice agents: build, improve, or review without edits. Sidebar AI FDE, or the mascot inside Agent Builder (already knows the open agent). Modes: Ask (read-only advice), Auto (starts work at once and saves a new version), Plan (proposes, waits for approval). Plan is the default when opened from the dashboard, and test cases need approval even in Auto. Ask with purpose, language, audience, actions. Attach docs or sheets as needed. Example: "Create a Hindi appointment agent for a dental clinic that checks slots, books, confirms date and time."

Structured QA and root-cause method: `callkaro-qa-framework`, `callkaro-agent-review-debug`.

## Audit loop

- Monitor: why users hang up, where they drop.
- Categorize: over 30s checks conversation quality, voice quality, transcription, hallucination. Under 30s adds early disconnect reason (heavy opening, hard words, long greeting).
- Fix: open call in Fine Tune Prompt, clone a new version (never edit production), find the transcript moment, name the problem, ask an LLM for root cause, patch, recheck, deploy.
- Details live in `callkaro-ai-auditor` and `callkaro-kpi-manager`.
- AI Auditor (sidebar label "Audit Reports", `/dashboard/audit_reports`): strategy picks which calls get scored, reports show callflow, postcall, transcriber accuracy plus cost, results page shows expected vs actual per issue.
- KPI Manager: setup per agent, dashboard charts, RCA reports explain drops, Pending Tasks list fixes, Run Manual RCA on demand.

## Feedback

From a call in history click Add Feedback: name (short title), engineer (optional), issue (detail). Lifecycle: Unresolved, In Review, Resolved. Track in Feedbacks pages (`/dashboard/feedbacks`).

- Unresolved to In Review ("Submit for Review") needs solution details, the fixed version URL, and at least 2 call URLs showing the issue resolved.
- In Review to Resolved ("Resolve") needs resolution notes. "Send Back to Processing" returns it to Unresolved. "Compare Versions" shows the before and after agent versions.

## Batch and schedule ops

- Trial table: one row per attempt (Trial 1 is the first call, Trial 2 the first retry), with totals for receipts, triggered, not connected, voicemail, connected, converted and the two conversion rates. It is not per call.
- Version table splits the same numbers by agent version. Recordings is the per-call list (filters: version, duration, trial, hangup reason, phone, funnel metrics) and holds the audio.
- Send Next Trial retries the contacts that match **any** selected hangup reason **or** any selected boolean post-call variable that is `true`. Click Preview and check the list before sending.
- Scheduled Calls (sidebar label; the docs call it Queued Schedule Calls, `/dashboard/queued-sch-calls`) lists schedule id, agent, to number, scheduled at, metadata. Delete Selected is permanent: the call will not be triggered.

## Ongoing calls

All on the Ongoing Calls page. "User" here means the whole account, not one customer.

| Control | What it does | Reversible |
|---|---|---|
| Call Window | Sets a start and end time. Calls only trigger inside it; calls outside stay queued and resume when it opens. | yes |
| Pause User / Resume User | Pauses call processing for **all agents** at once. Queued calls stay queued. Test calls still work. | yes |
| Pause / Resume (per agent row) | Same, for one agent. Other agents keep running. | yes |
| Clear all (Clear User Queue) | Deletes every queued call for every agent in the account. | **no** |
| Clear (per agent row) | Deletes every queued call for that agent. | **no** |

Pause when in doubt. Clear only when the queue itself is wrong, and never without the account owner asking for it.

## Analytics

Analytics page: total calls, minutes, avg per call, credits, functions called vs failed, distinct responses, calls and credits per day, hangup split. Performance Analytics (sidebar label, `/dashboard/agents-performance`) adds connected percent, conversion percents, audited counts, accuracy columns. Filter by agent, provider, model, date.

## Onboarding

Business verification unlocks everything: Dashboard Settings Compliances, enter business name, 15 char GSTIN, GST certificate PDF, 21 char CIN PDF, submit, 24 to 48h approval. Before approval you can build agents, test only on OTP verified numbers, use dashboard and webhooks. Rejected: fix reason, resubmit. Support: support@callkaro.ai.

## Pricing

Usage based: pay credits used, all models and voices open. Per minute Pulse: fixed rate, rounds up each call to full minute (4.2 min bills 5), preset models only. Enterprise custom: abhinav@callkaro.ai. Watch spend in Call History per call, Analytics totals, Billing reports.

## Ops gotchas

- Year pickers accept absurd years, clamp client side and validate server side.
- Audit date pages show two inputs for one date, trust the picker value.
- Icon buttons lack labels, confirm action by URL change not icon.
- Recharge depends on PayU Bolt, if CORB blocks it the button silently fails.

## Sim honesty

- Sims run with empty metadata. Blank `{{vars}}` failures are harness artifacts, not prompt bugs. Require an explicit empty-metadata fallback instruction (ask once / accept sim values). Sim transcripts test logic only; live calls prove the metadata path.
- Sim auto-grading can fail platform-side ("Failed to run LLM analysis"). Judge transcripts by hand until it is fixed.
