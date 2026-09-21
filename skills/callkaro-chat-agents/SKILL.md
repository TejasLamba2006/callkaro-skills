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

## Functions

Overview, Custom Functions, Send template, Send or Schedule Call, Send Image Document Video Audio. Always wire the prompt trigger to the function or it stays dead.

## Channels

WhatsApp Channel: connect number, templates, campaigns. Instagram Channel: Meta login, DM vs comment scope.

## Test and monitor

Test Chat in builder first, then Monitoring for live conversations. Check Best Practices page before shipping: short replies, clear handoff, no spammy follow-ups.
