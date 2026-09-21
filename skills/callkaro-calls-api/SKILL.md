---
name: callkaro-calls-api
description: Trigger CallKaro calls and campaigns over REST. Use when placing outbound calls, scheduling, retries, creating v1 or v2 campaigns, deleting scheduled calls, reading call history, handling errors.
---

# CallKaro Calls API

Base: `https://api.callkaro.ai`. Auth header on every request: `X-API-KEY: your key` from Dashboard API Key. Never ship the key in client code.

Docs: https://docs.callkaro.ai/api-reference/introduction

## Create outbound call

`POST /call/outbound`

```bash
curl -X POST https://api.callkaro.ai/call/outbound \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $KEY" \
  -d '{"to_number": "+919876543210", "agent_id": "6803fa770b666a64ab1694c1e"}'
```

Success returns `call_id`. Errors: 400 missing params, 403 bad key, 404 agent missing, 500 server.

Useful fields:

```json
{
  "to_number": "+919876543210",
  "agent_id": "6803fa770b666a64ab1694c1e",
  "batch_id": "68433b7b0dee98e59245ebab",
  "metadata": {"name": "Abhinav", "city": "Bangalore"},
  "priority": 1,
  "language": "hi",
  "schedule_at": "2025-12-31T09:30:00",
  "min_trigger_time": "09:00",
  "max_trigger_time": "18:00",
  "carry_over": true,
  "number_of_retries": 3,
  "gap_between_retries": 30
}
```

`metadata` values render in prompts as `{{metadata.name}}`. `gap_between_retries` accepts a number or array like `[30, 60]`. `carry_over` pushes missed calls to next day at min time.

## Campaigns

v1 `POST /call/campaign` needs `name` plus `agent_id`. Every call in it must use that agent. Good for single agent blasts.

v2 `POST /v2/call/campaign` needs only `name`. Each outbound call passes its own `agent_id`. Use v2 for new work unless you need the same agent lock.

Both return `batch_id`. Add calls with outbound API plus that `batch_id`. Track at `/dashboard/batch-calls/{batch_id}`.

## Delete scheduled call

`POST /call/delete-schedule-call?agent_id=YOUR_AGENT_ID` with body `{"to_number": "919876543210"}`. Form data also works. Use before rescheduling to avoid doubles. 400 means missing agent_id or to_number.

## Call history and filters

Dashboard Call History filters: call type (Inbound, Outbound, Outbound API, Outbound Scheduled, Outbound Test, Agent Test), batch scope, agent multi select, disconnect reason, duration buckets (0, 1-10s, 11-30s, 31-60s, 60s plus), date range, phone search. Columns include Type, From, To, Agent, Version, Time, Disposition, Last Stage (Converted, Connected, Not Connected, Voicemail), Duration, Model, Voice, Transcriber, Latency, Cost, Hangup Reason.

## Batch calls via dashboard

Create Batch Call page has Send Now and Schedule For Later. CSV first column is phone numbers. Optional `x_agent_id`, `x_language`, `x_schedule_at` (YYYY-MM-DDTHH:MM:SS) per row override. Download the template instead of hand making CSVs.

## Pricing note

Two models: usage based (pay credits used, all models open) and per minute Pulse (fixed rate, rounds up to full minute, preset model and voice). Costs show per call in history.
