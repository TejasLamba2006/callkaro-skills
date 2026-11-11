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

`metadata` values render in prompts as `{{metadata.name}}`. `gap_between_retries` is in minutes and accepts a number or array like `[30, 60]`. `carry_over` pushes missed calls to next day at min time.

Limits from the API spec: `priority` -100 to 100 (default 0), `number_of_retries` 0 to 10, `language` one of `hi en kn mr ta te bn gu ml`, trigger times as `HH:MM`. The intro page shows the success id as `call_id` and the endpoint spec as `call_sid`; read both until you have seen a live response.

## Campaigns

v1 `POST /call/campaign` needs `name`; `agent_id` is optional. With it, calls added with only the `batch_id` use the campaign's agent, and a call can still pass its own `agent_id`. Without it, every call must bring one, or it is rejected with `no agent found with given batch_id`.

v2 `POST /v2/call/campaign` needs only `name`. Each outbound call passes its own `agent_id`.

Errors worth recognising: 400 "You don't have enough credits. Recharge now!", 400 "Buy Phone Number", 403 "API KEY Mismatch", 404 "Agent not found!".

Both return `batch_id`. Add calls with outbound API plus that `batch_id`. Track at `/dashboard/batch-calls/{batch_id}`.

## Delete scheduled call

`POST /call/delete-schedule-call?agent_id=YOUR_AGENT_ID` with body `{"to_number": "919876543210"}`. Form data also works. Use before rescheduling to avoid doubles. 400 means missing agent_id or to_number.

## Call history and filters

Dashboard Call History filters: call type (Inbound, Outbound, Outbound API, Outbound Scheduled, Outbound Test, Agent Test), batch scope, agent multi select, disconnect reason, duration buckets (0, 1-10s, 11-30s, 31-60s, 60s plus), date range, phone search, conversion status, provider, plus account-specific text filters (seen: metadata keys such as a lead id) and a More Filters section. Columns in order: Type, From, To, Agent, Version, Time, Disposition, Last Stage (Converted, connected, Not Connected, voicemail; Converted means connected and conversion status true), Duration, Model, Voice, Provider, Transcriber, Latency, Billing Duration, Cost, Hangup Reason. Page: `/dashboard/call-history`.

## Assign to workflow

`POST /workflow/assign` with `to_number`, `workflow_id`, optional `attributes`, IST `schedule_at` and `batch_id` (an existing campaign on the same account; tags the run and its calls). It creates the contact if needed and saves the attributes, so it replaces a create-then-assign pair. 409 "This number is already running in this workflow"; 404 "Workflow not found" or "Batch not found". Do not retry a 400, 404 or 409. Full contract in the `callkaro-workflows` skill.

## Contacts

| Call | Notes |
|---|---|
| `POST /contact/create` | Body `to_number` plus `attributes: [{key, value, replace}]` (max 50 rows, values up to 1000 characters). 201 on success. 409 "Contact already exists. Use /contact/update to change it." |
| `GET /contact/get` | `?page=1&page_size=20` (page size 1 to 100) or `?to_number=919876543210` (no `+` in the URL). Returns a `pagination` object. |
| `POST /contact/update` | Same body. Values are overwritten unless a row sends `replace: false`. 404 "Contact not found". |

`+919876543210`, `919876543210` and `9876543210` are the same contact. Contact pages answer a missing or unknown key with 401, the outbound page says 403: handle both.

## Batch calls via dashboard

Create Batch Call page has Send Now and Schedule For Later. CSV first column is phone numbers. Optional `x_agent_id`, `x_language`, `x_schedule_at` (YYYY-MM-DDTHH:MM:SS) per row override. Download the template instead of hand making CSVs.

## Pricing note

Two models: usage based (pay credits used, all models open) and per minute Pulse (fixed rate, rounds up to full minute, preset model and voice). Costs show per call in history.
