# CallKaro Skills

Small helpers for working with CallKaro AI. Each folder under `skills` covers one part of the platform, built from the public docs at docs.callkaro.ai.

I put these together after clicking through the dashboard and reading the docs end to end. They are meant for Claude Code and similar agents, but humans can read them too.

## What is inside

- `callkaro-voice-agents` for building voice agents, prompts, voices, transcribers, versions, functions, secrets, knowledge bases
- `callkaro-chat-agents` for WhatsApp and Instagram chat agents
- `callkaro-calls-api` for outbound calls, campaigns, schedules, history
- `callkaro-webhooks` for realtime events like call ended and message status
- `callkaro-whatsapp` for number connect, templates, campaigns, inbox
- `callkaro-widget-integrations` for website widget and CRM links like HubSpot
- `callkaro-qa-ops` for audits, feedback, analytics, pricing, daily ops

## How to use

Copy the `skills` folder into your project or point your agent at it. Pick the skill that matches your task. Each SKILL.md has the endpoints, payloads, and gotchas inline so you do not need to hunt through docs.

Example: to place a call, open `callkaro-calls-api` and use the outbound curl with your `X-API-KEY`.

## Sources

All content comes from https://docs.callkaro.ai (132 pages, checked Sept 2026) plus a live pass over the dashboard. If docs and dashboard disagree, trust the dashboard and file it as a bug.

## Contribute

Found something stale. Open an issue or send a PR with the doc link and what changed. Keep it short.
