---
name: callkaro-chat-agents
description: Build CallKaro chat agents for WhatsApp and Instagram. Use when creating chat agents, writing system prompts, configuring follow-ups, functions, channels, testing and monitoring.
---

# CallKaro Chat Agents

Docs: https://docs.callkaro.ai/chat-agents/introduction (Chat Agents section)

## Create one

Dashboard, Agents (a Voice Agents / Chat Agents toggle sits at the top), "Create an Agent", pick Chat Agent, pick channel now. Channel is fixed forever. WhatsApp and Instagram need separate agents. Instagram also picks DM, Comment, or DM and Comments.

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

| Panel | What is in it |
|---|---|
| LLM Model | Start on `callkaro/arjuna-2.5`, the default. The secondary model is used **only when the primary errors** (timeout, 5xx, rate limit); it is not a quality fallback, so pick one from a different provider. Reasoning models get a Reasoning Effort control. Max Function Rounds caps tool-call loops per reply. |
| Conversation and Features (WhatsApp) | Context Length 5 to 100 messages (default 10). Max Bot Messages per Session 0 to 200 (default 50; a session is a 4-hour window; never set 0). Switches: Audio Transcription (off), Support Interactive Messages (off; needed for buttons and lists), Multiple Messages per Reply (on), Reply to Specific Message (off), Image Context (off), Gap Between Messages (0.1 s). |
| Follow-Ups (WhatsApp) | **Exactly one follow-up, Send After at least 60 minutes.** Both are platform limits the backend enforces whatever the builder saved. Follow-Up Action: Auto, Always send a message, or Always schedule a call (needs a Send / Schedule Call function in the follow-up function list). "When Not to Follow Up" is plain English, judged by the model at the moment the follow-up is about to go out. There is no DONE state machine. |
| Instagram Settings (Instagram) | Reply mode including "Decide before replying" (the agent stays silent if a reply is not appropriate), and **Human transfer**: once handed off, the bot stops replying to that contact until someone releases it manually. Human handoff lives here, not under Conversation and Features. |
| Webhook | `message_received`, `message_sent`, `template_sent`, `message_status_updated` (high volume, two or three per outbound message). `call_ended` is not offered on a chat agent. See `callkaro-webhooks`. |

## Agent modes

`agentMode` is fixed at creation. Basic is a single prompt plus a model. Advanced (`agentMode: "advanced"`) builds the prompt from `role`, `goal`, `instructions`, `rebuttals` and a `flowGraph` of numbered steps (`text`, `interactive`, `template`, `ask`, `function`, `end`, `global`, condition branches). The model follows the steps; code sends exact messages and fills variables. `flowGraph` is replaced whole on each save. Publish blocks empty or invalid steps (a Send text or Ask & save with no message, for example). **An unconnected exit is allowed** and is only a warning: it means nothing more is planned there, and the AI keeps helping inside the persona's role and goal. Max 150 steps, 12 exits per step.

The builder has thirteen step types: Start, Send text, Send buttons, Send template, Send media, Ask & save, Custom function, Update contact, Condition, Schedule call, Send contact card, Global intent, End. The keys above cover the common ones; for the rest (media, update contact, schedule call, contact card) export an agent that uses the step and copy its key, do not guess.

Workflow (`agentMode: "workflow"`) has no prompt and no model. Code walks the graph on every inbound message: Python `code` steps (with `async def run():`, timeout 1-30 s, success/failure exits), condition routing, contact updates, sends, and `assign_agent` / `assign_version` hand-offs to a Basic or Advanced agent. Graph may not loop; run capped at 40 steps and 60 s. Use for keyword or button menus, order lookups, spam limits and routing. WhatsApp only.

Chat Center Workflow steps: Start, Run code, Condition, Update contact, Send text, Send template, Send media, Send buttons, Assign chat agent, End. Three rules that are easy to get wrong:

- **Buttons are not branches.** A tap comes back as the user's next message and runs the workflow again from Start. Route on `x_message["button_id"]` in a Condition or Run code step.
- **Run code runs for real in Test Chat**, including calls to your APIs. `x_context["is_test"]` is `True` there: use it to skip anything that charges, books or messages someone. Code gets `x_message`, `x_contact`, `x_context`, `x_history`, and `update_contact_custom({...})` to save contact attributes (not saved in Test Chat).
- **Assign chat agent** hands the message to a Basic or Advanced WhatsApp agent at its **published** version; that agent's model cost and follow-ups then apply.

Versions and history (CLI): `cku chat-agents import --file <path>` (create from export JSON), `import-versions <agentId> --file <path>`, `delete-version <agentId> --versions <id>` (refused if published or assigned), `commits <agentId>`, `commit <commitId>`, `revert <agentId> <commitId>`. The AI auditor takes `cku chat-audit create|update --chatflow-summary "..."` to describe the intended conversation flow.

Full step tables and create examples: `chat-agents-advanced.md` and `chat-agents-workflow.md` in `callkaro-skills-official`. Testing: `chat-simulations/chat-simulation-playbook.md`.

## Functions

Overview, Custom Functions, Send template, Send or Schedule Call, Send Image Document Video Audio. Always wire the prompt trigger to the function or it stays dead.

- **Custom function, Direct Send** (off by default). On: the return value is sent to the customer as is, with no second model call, so it must be exactly `{"status": ..., "message": ...}`. Use it for wording that must be exact (a disclaimer, a reference number, an OTP). Off: the model reads the dict and writes its own reply, any shape works.
- **Execution timeout** 5 to 120 seconds, default 30. Set your HTTP client timeout below it. `x_context` (phone numbers, ids, time, `is_test`) is available in every function.
- **Send or Schedule Call**: a call is never placed outside the configured window (Asia/Kolkata), whether immediate or scheduled by the AI. Outside it, `defer` moves the call to the next open window and `cancel` drops it. Leave it on `defer` unless a late call is worse than none.
- **Send media**: WhatsApp agents only. The link must be an uploaded file or a public `https://` URL.

## Channels

WhatsApp Channel: connect number, templates, campaigns. Only `CLOUD_API` numbers can have a chat agent, and it is one agent per number. Free-form replies go out only inside the 24-hour window after the customer's last message; outside it, use a template.

Instagram Channel: Meta login, DM vs comment scope. An agent is In-Progress (answering nothing) or Live. **Publish the version you want before flipping to Live**: Live serves the published version, not what is open in the builder.

## Test and monitor

Test Chat in builder first, then Monitoring for live conversations. Check Best Practices page before shipping: short replies, clear handoff, no spammy follow-ups.

- Publish ships the **last saved** version, not what is on screen. Test Chat always runs the version open in the builder.
- Simulation tab: WhatsApp Basic and Advanced agents only (not Chat Center Workflows, widget flow agents or Instagram). A batch is test cases x versions x epochs, at most 100 epochs and 500 runs. Pass is 7/10 or higher. Nothing is sent and no contact is changed. From a terminal: `cku chat-sim` (`callkaro-cli`).
- Monitoring, Clear Chat clears the model's context for that customer, not the display. In Analytics, "excluding campaigns" is the filter that shows what the agent itself is doing.
