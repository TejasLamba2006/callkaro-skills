---
name: callkaro-webhooks
description: Receive CallKaro realtime events. Use when setting up webhook destinations, handling call_ended, message_received, message_sent, template_sent, message_status_updated payloads.
---

# CallKaro Webhooks

Docs: https://docs.callkaro.ai/webhook/introduction

Every event uses one envelope. Switch on `event`, read `data`. Ignore unknown events so new ones never break you.

```json
{"event": "call_ended", "data": {}}
```

## Events

- `call_ended`: fires once per finished voice call. On by default.
- `message_received`: one per inbound chat message. Opt in.
- `message_sent`: one per outbound non template reply. Opt in.
- `template_sent`: one per WhatsApp template send. Never doubles as `message_sent`, pick the one you want.
- `message_status_updated`: sent, delivered, read, failed. Highest volume (2 to 3 per outbound message). Only enable if you track delivery.

## Destinations (max 3, independent)

- Account level (Dashboard Webhook): all agents, any of the five events. One central CRM sync.
- Voice agent level: that agent only, `call_ended` only, not configurable.
- Chat agent level: own Webhook panel, message events.

Turning message events on account wide does not flip every agent on. Each destination keeps its own subscription.

## call_ended payload

POST JSON. Key fields: `callSid`, `name` (call type), `agent`, `versionId`, `from`, `to`, `recordingUrl`, `call_duration` seconds, `time`, `transcription`, `batchId`, `hangup_reason`, `call_metadata`, `try_count` (-1 inbound, 0 first try), `post_call`, `post_call_detail`, `functions_called` (name, success, timestamp), `disposition_reason`, `conversion_status`, `next_call_scheduled`, `call_link`.

## Message events payload

`message_received`, `message_sent`, `template_sent` share one shape: `userId`, `agentId`, `channel`, `message_id` (CallKaro id), `msg_id` (wamid), `direction`, `type`, `body`, `template`, `template_json`, `from`, `to`, `contact_number`, `status`, `agent_phone_number_id`, `wa_campaign_id`, `timestamp`.

## Status event payload

Same ids plus `previous_status` and current `status`. Expect sent, delivered, read in order.

## Handler tips

- Return 200 fast, process async. WhatsApp status bursts will hammer slow endpoints.
- Dedup on `message_id` plus `msg_id`.
- Treat only `delivered` and `read` as arrived. `sent` means accepted, not on device. `failed` never shows in history pulls.
- Verify ownership expectations: sends from numbers you do not own return 403 upstream, so a 403 in logs means wrong `phone_number_id`, not your handler.
