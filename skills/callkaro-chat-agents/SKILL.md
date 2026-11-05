---
name: callkaro-chat-agents
description: Build CallKaro chat agents for WhatsApp and Instagram. Use when creating chat agents, writing system prompts, configuring follow-ups, functions, channels, testing and monitoring.
---

# CallKaro Chat Agents

Docs: https://docs.callkaro.ai/chat-agents/introduction (Chat Agents section)

## Create one

Dashboard Agents Create Agent, pick Chat Agent, pick channel now. Channel is fixed forever. WhatsApp and Instagram need separate agents. Instagram also picks DM, Comment, or DM and Comments.

Builder has three panes: System Prompt, Agent Configuration, Test Chat. Nothing exists on server until you save. Name it by job, copy the Agent ID for API use. Versions work like voice agents: draft, publish, switch.

Panels by channel: LLM Model both. Conversation and Features WhatsApp only. Instagram Settings Instagram only. Follow-Ups WhatsApp only. Functions all types on WhatsApp, custom only on Instagram. Webhook both.

## System prompt

The prompt decides what the agent says and when it acts. Cover five things:

- Identity and scope: who it is, what topics are allowed, where the boundary is.
- Tone and length: chat is short, two or three sentences, reply in customer language, bullets only for steps.
- When to call each function: name every trigger ("when customer asks for price list, call send_price_list"). Unmentioned functions never run.
- What not to do: no competitor talk, no unauthorised discounts, no legal or medical advice, no delivery promises.
- What ends it: order placed, question answered, not interested. Follow-ups refer back to this.

Skeleton:

```
You are Riya, support for Acme Appliances on WhatsApp.
SCOPE: orders, delivery, warranty, service visits only.
STYLE: customer language, two short sentences max.
ACTIONS: order status calls get_order_status (ask for order id first), warranty PDF calls send_warranty_pdf, angry or wants human calls schedule_callback.
DONE: question answered and customer confirms, or says not interested.
```

## Configuration

LLM Model: pick model and temperature. Conversation and Features: greeting, fallback, handoff to human. Follow-Ups: nudge silent chats, stop when DONE state hits. Webhook: per agent events.

## Agent modes

`agentMode` is fixed at creation. Basic is a single prompt plus a model. Advanced (`agentMode: "advanced"`) builds the prompt from `role`, `goal`, `instructions`, `rebuttals` and a `flowGraph` of numbered steps (`text`, `interactive`, `template`, `ask`, `function`, `end`, `global`, condition branches). The model follows the steps; code sends exact messages and fills variables. `flowGraph` is replaced whole on each save; publish refuses unconnected or empty steps. Max 150 steps, 12 exits per step.

Workflow (`agentMode: "workflow"`) has no prompt and no model. Code walks the graph on every inbound message: Python `code` steps (with `async def run():`, timeout 1-30 s, success/failure exits), condition routing, contact updates, sends, and `assign_agent` / `assign_version` hand-offs to a Basic or Advanced agent. Graph may not loop; run capped at 40 steps and 60 s. Use for keyword or button menus, order lookups, spam limits and routing.

Versions and history (CLI): `cku chat-agents import --file <path>` (create from export JSON), `import-versions <agentId> --file <path>`, `delete-version <agentId> --versions <id>` (refused if published or assigned), `commits <agentId>`, `commit <commitId>`, `revert <agentId> <commitId>`. The AI auditor takes `cku chat-audit create|update --chatflow-summary "..."` to describe the intended conversation flow.

Full step tables and create examples: `chat-agents-advanced.md` and `chat-agents-workflow.md` in `callkaro-skills-official`. Testing: `chat-simulations/chat-simulation-playbook.md`.

## Functions

Overview, Custom Functions, Send template, Send or Schedule Call, Send Image Document Video Audio. Always wire the prompt trigger to the function or it stays dead.

## Channels

WhatsApp Channel: connect number, templates, campaigns. Instagram Channel: Meta login, DM vs comment scope.

## Test and monitor

Test Chat in builder first, then Monitoring for live conversations. Check Best Practices page before shipping: short replies, clear handoff, no spammy follow-ups.
