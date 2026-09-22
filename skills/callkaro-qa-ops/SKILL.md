---
name: callkaro-qa-ops
description: Operate and debug CallKaro day to day. Use when monitoring calls, auditing, reading RCA, managing feedback, batch tables, scheduled queues, analytics, onboarding, pricing, AI FDE help.
---

# CallKaro QA and Ops

## AI FDE

Chat assistant for voice agents: build, improve, or review without edits. Sidebar AI FDE, or the mascot inside Agent Builder (already knows the open agent). Modes: Ask (advice), Auto (does it), Plan (proposes, waits for approval). Ask with purpose, language, audience, actions. Attach docs or sheets as needed. Example: "Create a Hindi appointment agent for a dental clinic that checks slots, books, confirms date and time."

## Audit loop

- Monitor: why users hang up, where they drop.
- Categorize: over 30s checks conversation quality, voice quality, transcription, hallucination. Under 30s adds early disconnect reason (heavy opening, hard words, long greeting).
- Fix: open call in Fine Tune Prompt, clone a new version (never edit production), find the transcript moment, name the problem, ask an LLM for root cause, patch, recheck, deploy.
- AI Auditor: strategy picks which calls get scored, reports show callflow, postcall, transcriber accuracy plus cost, results page shows expected vs actual per issue.
- KPI Manager: setup per agent, dashboard charts, RCA reports explain drops, Pending Tasks list fixes, Run Manual RCA on demand.

## Feedback

From a call in history click Add Feedback: name (short title), engineer (optional), issue (detail). Lifecycle: Unresolved, In Review, Resolved. Track in Feedbacks pages.

## Batch and schedule ops

Batch table and trial tables show per call status, version table splits by agent version, send next trial retries failures, recordings hold audio. Queued Schedule Calls lists schedule id, agent, number, time, metadata. Delete Selected clears dupes before rescheduling.

## Ongoing calls

Call Window opens live view. Pause User halts that person, Clear User Queue drops their backlog. Pause Agent halts the agent, Clear Agent Queue drops its backlog. Paused rows stay visible so you know what is held.

## Analytics

Analytics page: total calls, minutes, avg per call, credits, functions called vs failed, distinct responses, calls and credits per day, hangup split. Agents Performance adds connected percent, conversion percents, audited counts, accuracy columns. Filter by agent, provider, model, date.

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
