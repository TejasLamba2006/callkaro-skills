<!-- Verbatim copy of the official CallKaro workflow spec, fetched 2026-10-13 from https://docs.callkaro.ai/workflows/build-with-claude. Source of truth if it disagrees with SKILL.md. -->

# CallKaro workflows

You produce one thing: a **workflow file** — JSON the user imports with
**Workflows → Import** to get a working workflow on their canvas.

A workflow is a graph of steps. Every contact enrolled in it gets their own
**run**, which starts at the Start node and walks the graph one step at a time:
it places a call and waits for it to end, waits an hour, checks whether the call
connected, sends a WhatsApp message, calls an API, updates the contact, and so
on until it reaches an End.

The runtime is **deterministic**. A Conditions step picks a branch by comparing
values; nothing "decides" freely. If you cannot draw the path, a run cannot walk
it.

This document is the complete contract. Do not invent fields or node types —
an unknown type is rejected on import, and unknown fields are ignored, which
looks like the workflow ignoring your work.

---

## 1. Before you write anything

Ask for, or infer, these. Getting them wrong wastes the whole workflow.

1. **The goal and the steps.** What happens first, what happens next, and what
   decides between paths (did the call connect? did they say they're
   interested? did the API say the payment cleared?).
2. **Where each path ends.** Every path should finish at an **End** node. A
   branch with nothing after it simply stops the run there — legal, but almost
   always a forgotten step.
3. **The account-specific IDs** the steps need. These come from the user's own
   CallKaro account and cannot be guessed:
   - **Voice agent IDs** for every Send Call step. The ID is the last part of
     the agent's URL in the dashboard (`/agent/<agent id>`).
   - **CRM attribute names** for Update Contact steps and for any `contact`
     value. They are listed under **CRM → Attributes**.
   - **WhatsApp**: the sending number and, for templates, which approved
     template. These are easiest to pick in the dashboard after import (§6.6,
     §6.7).
   - **API URLs** and any secrets the API needs (secrets are referenced by
     name, never pasted into the file).

If the user does not have an ID to hand, use an obvious placeholder (§9) and
tell them exactly which steps to fix after importing.

---

## 2. The file you produce

The deliverable is a **complete workflow file**, the same shape the dashboard's
**Export** writes, so an exported workflow can be edited and imported back.

```json
{
  "type": "callkaro_workflow",
  "version": 1,
  "data": {
    "workFlowName": "Lead follow-up",
    "type": "normal",
    "graph": {
      "nodes": [],
      "edges": []
    }
  }
}
```

- `type` must be exactly `"callkaro_workflow"` and `version` exactly `1`.
- `data.workFlowName` is required — the workflow's name in the list.
- `data.type` must be `"normal"`.
- `data.graph` holds the nodes and the edges between them.

Import **creates a new workflow**. It never changes an existing one, and it
does not enroll anyone: contacts are added afterwards from the CRM (**Assign →
Workflow**) or through the Assign to Workflow API.

---

## 3. The graph

### Nodes

Every node has these fields, plus the ones its type needs (§6):

```json
{ "id": "wait-1", "type": "wait", "name": "Wait a day", "x": 660, "y": 180, "minutes": 1440 }
```

(`minutes` is the field a Wait needs; the other four are on every node.)

| Field | Rule |
|---|---|
| `id` | Unique within the workflow. Use `<type>-<n>`: `start-1`, `send-call-2`, `conditions-1`. Never put a `.` in an id — it would break `fn_response` paths (§5). |
| `type` | One of the ten types in §6. |
| `name` | What the card shows. Make it say what the step is for: "Day 1 call", "Interested?", not "Send Call". |
| `x`, `y` | Position on the canvas, top-left of the card. See §7. |

### Edges

```json
{ "id": "edge-3", "from": "conditions-1", "fromHandle": "exit-yes", "to": "wa-message-1" }
```

| Field | Rule |
|---|---|
| `id` | Unique. `edge-<n>` is fine. |
| `from` | The node the run leaves. |
| `fromHandle` | Which exit of that node. **`"out"`** for every node type except Conditions, whose exits are its branch ids (§6.5). |
| `to` | The node the run goes to next. |

Rules:

- **Exactly one `start` node.** Nothing may lead into it.
- **An `end` node has no exits.** Nothing may leave it. Use as many End nodes
  as you like — one per branch is normal.
- **One edge per exit.** Each `(from, fromHandle)` pair appears at most once.
  A run follows exactly one path; there are no parallel branches.
- **At least one path must lead from Start to an End**, or import is refused.
- **An exit with no edge ends the run there.** Legal, but say so if you do it
  on purpose.
- **Loops are allowed** — e.g. wait, check an API, and go back to waiting until
  it says "done". A run stops itself after 500 steps, so every loop needs a way
  out.

---

## 4. What a run knows

Each run carries a context that steps read from and write to:

| Name | What it holds |
|---|---|
| `phone_number` | The contact's number, digits only. |
| `lead` | The contact's CRM attributes, by attribute name. Refreshed by an Update Contact step. |
| `call_metadata` | What the contact was enrolled with (their attributes, as text) plus anything a call added. Sent to every call the workflow places. |
| `post_call` | Variables the agent extracted after the most recent call (the agent's post-call variables), and anything an API Advanced step set on it. |
| `last_call` | The most recent call this run placed: `callSid`, `call_id`, `call_duration` (seconds), `hangup_reason`, `conversion_status`, `recordingUrl`. Empty until a Send Call step has finished. |
| `nodes` | Every finished step's result, by node id (§6, "Result"). |

---

## 5. Value sources

Wherever a step takes a value — a condition, a placeholder in a message or URL,
a header, an Update Contact row, a call metadata row — it is a **source** plus,
for most sources, a field:

```json
{ "source": "contact", "value": "city" }
```

(in a condition the field is called `field` instead of `value` — see §6.5).

| `source` | The field (`value` / `field`) is… | Gives |
|---|---|---|
| `static_value` | the literal value | that value |
| `phone_number` | — (leave empty) | the contact's number |
| `contact` | a CRM attribute name | `lead.<name>` |
| `call_metadata` | a key | `call_metadata.<key>` |
| `post_call_variables` | a post-call variable name | `post_call.<name>` |
| `fn_response` | `<node id>.<path>` | an earlier step's result, e.g. `api-basic-1.body.status` |
| `connected_call` | — | `true` / `false`: did the last call connect |
| `voicemail` | — | `true` / `false`: did the last call reach voicemail |
| `hangup_reason` | — | the last call's hangup reason |
| `call_duration` | — | the last call's duration in seconds |
| `conversion_status` | — | the outcome the agent recorded for the last call |
| `secret` | a saved secret's name | that secret — **API Basic headers only** |

Fields are dotted paths, so nested values work: `contact` + `address.city`,
`fn_response` + `api-advanced-1.returned.score`.

A source that has nothing (an attribute the contact lacks, a call that has not
happened yet) gives an empty value. It never fails the step.

`connected_call` counts these hangup reasons as connected:
`CLIENT_INITIATED`, `PARTICIPANT_REMOVED`, `SESSION_TIMEOUT`. Use it rather than
testing `hangup_reason` yourself.

---

## 6. Node types

### 6.1 `start`

Where every run begins. No settings. Exit: `out`.

```json
{ "id": "start-1", "type": "start", "name": "Start", "x": 320, "y": 180 }
```

### 6.2 `end`

The run finishes here. No settings, no exits.

```json
{ "id": "end-1", "type": "end", "name": "Done", "x": 1680, "y": 180 }
```

### 6.3 `send-call`

Calls the contact with a voice agent, then **waits for the call to end** before
moving on (the run shows as *Awaiting call*). If nobody answers and retries
remain, it waits for those too. A call requested outside the account's calling
window is held until the window opens, and the step waits for it. If the call
cannot be placed at all — no credit, a DND number, a number that is not valid —
the step does not wait; it moves on straight away. Follow it with a Conditions
step on `connected_call` rather than assuming the call happened.

| Field | Required | Meaning |
|---|---|---|
| `agentId` | **yes** | The voice agent's ID. |
| `retries` | no (0) | How many more times to call if the contact does not answer. 0–10. |
| `retryGaps` | no | Minutes to wait before each retry, one number per retry: `[30, 120]`. |
| `retryGapMinutes` | no (30) | The gap used for any retry without its own entry. |
| `scheduleAt` | no | Hold the call until this IST date-time, `"YYYY-MM-DDTHH:mm:ss"`. A time already past calls straight away. |
| `metadata` | no | Extra values sent with the call, `[{ "key", "source", "value" }]`. The agent reads each as `{{metadata.<key>}}`. Sent on top of `call_metadata`; a row wins on a shared key. |

```json
{
  "id": "send-call-1", "type": "send-call", "name": "Day 1 call", "x": 660, "y": 180,
  "agentId": "68f1c0a2b3d4e5f6a7b8c9d0",
  "retries": 2, "retryGaps": [30, 120], "retryGapMinutes": 30,
  "metadata": [
    { "key": "customer_name", "source": "contact", "value": "first_name" },
    { "key": "campaign", "source": "static_value", "value": "Diwali offer" }
  ]
}
```

Exit: `out`. Result: `{ placed, call_sid, … }`, then the call's outcome lands in
`last_call` and `post_call`.

### 6.4 `wait`

Pauses the run.

| Field | Required | Meaning |
|---|---|---|
| `minutes` | **yes** | Whole minutes, at least 1. 1440 is a day. |

```json
{ "id": "wait-1", "type": "wait", "name": "Wait a day", "x": 1000, "y": 180, "minutes": 1440 }
```

Exit: `out`. There is no "wait until 10 am"; use minutes, or `scheduleAt` on a
Send Call.

### 6.5 `conditions`

Picks one branch. Branches are checked **in order and the first match wins**.
The branch with **no `condition`** is the fallback ("otherwise") — put it
**last**. Without a fallback, a run that matches nothing ends here.

```json
{
  "id": "conditions-1", "type": "conditions", "name": "Did they pick up?", "x": 1000, "y": 180,
  "exits": [
    { "id": "exit-connected", "label": "Connected",
      "condition": { "source": "connected_call", "field": "", "op": "eq", "value": "true" } },
    { "id": "exit-otherwise", "label": "otherwise" }
  ]
}
```

Each exit:

| Field | Meaning |
|---|---|
| `id` | Unique within this node. **This is the `fromHandle` of the edge leaving the branch.** |
| `label` | Shown on the card. |
| `condition` | `{ source, field, op, value }` — omit it for the fallback. |

`source` and `field` are as in §5; sources marked "—" there take `"field": ""`.
`value` is what to compare against — always text.

| `op` | True when the actual value… |
|---|---|
| `eq` | equals `value` (trimmed, case-insensitive text) |
| `ne` | does not equal `value` |
| `contains` | contains `value` (case-insensitive) |
| `gt` | is a number greater than `value` — false if either side is not a number |
| `lt` | is a number less than `value` — same |
| `empty` | is missing, blank or an empty list (`value` ignored) |
| `not_empty` | is anything else (`value` ignored) |

Booleans compare as text: test `connected_call` / `voicemail` with
`"op": "eq", "value": "true"` (or `"false"`).

### 6.6 `wa-message`

Sends a free-text WhatsApp message.

| Field | Meaning |
|---|---|
| `provider` | `"whatsapp"` (WhatsApp Business connected to CallKaro) or `"heltar"`. |
| `phoneNumberId` | The sending number — **required for `whatsapp`**. Leave `""` and pick it in the dashboard (§9). |
| `displayPhoneNumber` | Set by the dashboard when the number is picked; leave `""`. |
| `message` | **Required.** The text. `{{name}}` placeholders are filled per contact. |
| `parameters` | One row per placeholder: `{ "key": "{{name}}", "source", "value" }`. The key is the placeholder exactly as written, braces included. |

```json
{
  "id": "wa-message-1", "type": "wa-message", "name": "Sorry we missed you", "x": 1340, "y": 400,
  "provider": "whatsapp", "phoneNumberId": "", "displayPhoneNumber": "",
  "message": "Hi {{name}}, we tried calling about your {{product}} enquiry. Reply here and we'll call back.",
  "parameters": [
    { "key": "{{name}}", "source": "contact", "value": "first_name" },
    { "key": "{{product}}", "source": "call_metadata", "value": "product" }
  ]
}
```

**WhatsApp only delivers free text within 24 hours of the contact's last
message to you.** To message someone cold — which is most workflows — use a
template (§6.7). Say this to the user if they ask for a free-text message to a
contact who has not written in.

Exit: `out`. A failed send does not stop the run; the result records `ok: false`.

### 6.7 `wa-template`

Sends an approved WhatsApp template. The template's ID, language, body and
variable slots come from the user's own WhatsApp account, so **write the node
with a placeholder and let the user pick the template in the dashboard** —
picking it fills every one of these fields and creates one row per template
variable for them to map.

| Field | Meaning |
|---|---|
| `provider` | `"whatsapp"`, `"heltar"` or `"aisensy"`. |
| `templateId` | **Required.** Use the placeholder `"REPLACE_ME_TEMPLATE"` unless the user gave you the ID. |
| `templateName`, `languageCode`, `templateBody` | Filled when the template is picked; `""` otherwise. |
| `phoneNumberId`, `displayPhoneNumber` | The sending number for `whatsapp`; `""` and pick it in the dashboard. |
| `parameters` | Filled when the template is picked; `[]` otherwise. |

```json
{
  "id": "wa-template-1", "type": "wa-template", "name": "Missed-call template", "x": 1340, "y": 400,
  "provider": "whatsapp", "templateId": "REPLACE_ME_TEMPLATE",
  "templateName": "", "languageCode": "", "templateBody": "",
  "phoneNumberId": "", "displayPhoneNumber": "", "parameters": []
}
```

Exit: `out`.

### 6.8 `api-basic`

Calls an HTTP endpoint.

| Field | Meaning |
|---|---|
| `method` | `GET`, `POST`, `PUT`, `PATCH` or `DELETE`. Default `POST`. |
| `url` | **Required.** May contain `{{placeholders}}`. |
| `parameters` | Rows for the URL's placeholders: `{ "key": "{{id}}", "source", "value" }`. |
| `headers` | `[{ "key": "Authorization", "source": "secret" \| "static_value", "value" }]`. With `secret`, `value` is the **name** of a secret saved in the account; never put a real token in the file. |
| `body` | Optional JSON text with `{{placeholders}}`. |
| `bodyParameters` | Rows for the body's placeholders, same shape as `parameters`. |

Placeholders in the body: write them **bare** where the value should be a JSON
value (`"amount": {{amount}}` → a number stays a number) and **inside quotes**
where it is part of a string (`"note": "Lead {{name}}"`).

```json
{
  "id": "api-basic-1", "type": "api-basic", "name": "Tell our CRM", "x": 1340, "y": 0,
  "method": "POST",
  "url": "https://api.example.com/leads/{{lead_id}}/status",
  "parameters": [ { "key": "{{lead_id}}", "source": "call_metadata", "value": "lead_id" } ],
  "headers": [ { "key": "Authorization", "source": "secret", "value": "CRM_API_TOKEN" } ],
  "body": "{\"status\": \"interested\", \"phone\": \"{{phone}}\", \"duration\": {{duration}}}",
  "bodyParameters": [
    { "key": "{{phone}}", "source": "phone_number", "value": "" },
    { "key": "{{duration}}", "source": "call_duration", "value": "" }
  ]
}
```

Exit: `out` — whatever the response. Result: `{ ok, status, body }`. Branch on
it with a Conditions step: `fn_response` + `api-basic-1.ok`, or
`api-basic-1.body.<field>`. Timeout 30 s.

### 6.9 `api-advanced`

Runs a JavaScript function, for anything API Basic cannot do.

| Field | Meaning |
|---|---|
| `code` | **Required.** One named function taking one argument: `async function name(context) { … }`. |

`context` holds `call_metadata`, `post_call`, `lead`, `nodes`,
`user_phone_number`, `call_duration`, `callSid`, `hangup_reason`,
`conversion_status`, `userId`, `workflow_id`, `run_id`.

Available inside the function: `axios`, `moment` (with timezones), `_`
(lodash), `console`, and `x_secrets` (the account's saved secrets, by name).
`require`, `process` and the filesystem are not available. 30 s, 256 MB.

- What the function **returns** becomes `nodes.<id>.returned` — read it later
  with `fn_response` + `<id>.returned.<field>`. `nodes.<id>.success` is `false`
  if it threw.
- Anything it sets on **`context.post_call`** is kept, so later steps can read
  it as `post_call_variables`.

```json
{
  "id": "api-advanced-1", "type": "api-advanced", "name": "Score the lead", "x": 1340, "y": 180,
  "code": "async function scoreLead(context) {\n  const budget = Number(context.lead.budget || 0);\n  const score = budget > 500000 ? 'hot' : 'warm';\n  context.post_call.lead_score = score;\n  return { score };\n}"
}
```

Exit: `out`. The function's code is a sketch against the user's systems — say so.

### 6.10 `update-lead` (shown as "Update Contact")

Writes values onto the contact's CRM record. The type key is `update-lead`.

| Field | Meaning |
|---|---|
| `updates` | **Required, at least one row**: `{ "attribute", "source", "value" }`. |

- `attribute` must be an **existing CRM attribute name** (CRM → Attributes). A
  name that does not exist is skipped at run time, not created.
- `source` / `value` as in §5 (`static_value` for a fixed value).
- The value is converted to the attribute's type; one that does not fit (text
  into a number, an option an enum does not have) is skipped and logged.
- A value someone typed into the CRM by hand is never overwritten by a workflow.

```json
{
  "id": "update-lead-1", "type": "update-lead", "name": "Mark interested", "x": 1340, "y": 0,
  "updates": [
    { "attribute": "lead_status", "source": "static_value", "value": "Interested" },
    { "attribute": "callback_time", "source": "post_call_variables", "value": "callback_time" }
  ]
}
```

Exit: `out`. Afterwards `lead` holds the updated record.

---

## 7. Layout

The canvas draws what you give it; there is also a **Re-arrange** button, but a
readable file is better.

- Start at `x: 320, y: 180`.
- Each next step **340 px to the right**.
- Branches of a Conditions step: first branch on the same row, each further
  branch **220 px lower**; a branch that rejoins goes back to its row.
- Never place two nodes at the same position.

---

## 8. What import rejects

Import refuses the file, naming the node, if any of these hold. Check them all
before handing the file over:

1. Not exactly one `start` node.
2. A node with no `id`, or two nodes with the same `id`.
3. A `type` that is not one of the ten in §6.
4. `wait` without a whole `minutes` of at least 1.
5. `send-call` without `agentId`.
6. `api-basic` without `url`; `api-advanced` without `code`.
7. `wa-template` without `templateId`; `wa-message` without `message`.
8. `conditions` with no `exits`, or two exits with the same `id`; a rule whose
   source needs a field but has none.
9. `update-lead` with no rows; a row with no `attribute`, no `source`, or (for
   a source that needs one) no `value`.
10. An edge from or to a node that does not exist; an edge leaving an `end`;
    an edge into `start`; an edge whose `fromHandle` is not one of the node's
    exits (`out`, or a Conditions exit id).
11. No path from Start to any End.

Import does **not** check that IDs are real — an invented agent ID imports
fine and fails on the first call. That is what §9 is for.

---

## 9. Placeholders, and what to tell the user

When the user has not given you a value you need, do not make one up that looks
real. Use these, and list every one in your reply:

| Where | Placeholder |
|---|---|
| `send-call.agentId` | `"REPLACE_ME_AGENT"` |
| `wa-template.templateId` | `"REPLACE_ME_TEMPLATE"` |
| `wa-message.phoneNumberId`, `wa-template.phoneNumberId` | `""` |
| An API URL you do not know | `"https://REPLACE_ME.example.com/..."` |
| A CRM attribute you guessed | use the guessed name, and list it |

Then end with a short checklist, e.g.:

> After importing, open these steps and fix them before enrolling anyone:
> - **Day 1 call**, **Day 3 call** — pick the voice agent.
> - **Missed-call template** — pick the template and the sending number, then
>   map its variables.
> - **Tell our CRM** — the URL is a guess, and it expects a secret named
>   `CRM_API_TOKEN`.
> - **Mark interested** — assumes CRM attributes `lead_status` and
>   `callback_time` exist.

The user can also ask *"which values in this workflow did you invent?"* — answer
that honestly.

---

## 10. What a workflow cannot do

Tell the user instead of faking these:

- **Parallel branches.** A run follows one path. Two things "at the same time"
  means one after the other.
- **Wait until a time of day** ("wait until 10 am"). Wait is in minutes; Send
  Call has `scheduleAt` and the account's calling window.
- **Wait for the contact to reply on WhatsApp.** There is no inbound trigger;
  wait a fixed time, then check with an API step or a condition.
- **SMS or email steps.** Use API Basic / API Advanced against the user's own
  provider.
- **Enroll contacts.** The file defines the workflow only. Contacts are added
  from the CRM or the Assign to Workflow API, after importing.
- **Change an existing workflow on import.** Import always creates a new one.

---

## 11. Converting someone else's plan

When the user hands you a cadence, a spreadsheet or another tool's automation,
map it mechanically:

| They say | You write |
|---|---|
| "Call them" | `send-call` (+ `conditions` on `connected_call` after it) |
| "Retry if no answer, after 30 min then 2 h" | `retries: 2, retryGaps: [30, 120]` on the same Send Call |
| "Next day" / "after 3 days" | `wait` with `minutes: 1440` / `4320` |
| "If interested…" | `conditions` on a post-call variable (`post_call_variables` + its name) |
| "Send WhatsApp" to someone who has not written in | `wa-template` |
| "Update the CRM / mark as…" | `update-lead` (their CallKaro CRM) or `api-basic` (an outside CRM) |
| "Notify our system / webhook" | `api-basic` |
| "Stop" / "close the lead" | `end` |

---

## 12. A complete example

Call the lead; if they pick up and say they are interested, mark them and tell
an outside CRM; if they do not pick up, send a WhatsApp template, wait a day and
call once more.

```json
{
  "type": "callkaro_workflow",
  "version": 1,
  "data": {
    "workFlowName": "New lead follow-up",
    "type": "normal",
    "graph": {
      "nodes": [
        { "id": "start-1", "type": "start", "name": "Start", "x": 320, "y": 180 },
        {
          "id": "send-call-1", "type": "send-call", "name": "First call", "x": 660, "y": 180,
          "agentId": "REPLACE_ME_AGENT", "retries": 1, "retryGaps": [30], "retryGapMinutes": 30,
          "metadata": [ { "key": "customer_name", "source": "contact", "value": "first_name" } ]
        },
        {
          "id": "conditions-1", "type": "conditions", "name": "Picked up?", "x": 1000, "y": 180,
          "exits": [
            { "id": "exit-picked", "label": "Picked up",
              "condition": { "source": "connected_call", "field": "", "op": "eq", "value": "true" } },
            { "id": "exit-missed", "label": "otherwise" }
          ]
        },
        {
          "id": "conditions-2", "type": "conditions", "name": "Interested?", "x": 1340, "y": 180,
          "exits": [
            { "id": "exit-interested", "label": "Interested",
              "condition": { "source": "post_call_variables", "field": "interested", "op": "eq", "value": "yes" } },
            { "id": "exit-not", "label": "otherwise" }
          ]
        },
        {
          "id": "update-lead-1", "type": "update-lead", "name": "Mark interested", "x": 1680, "y": 180,
          "updates": [ { "attribute": "lead_status", "source": "static_value", "value": "Interested" } ]
        },
        {
          "id": "api-basic-1", "type": "api-basic", "name": "Tell our CRM", "x": 2020, "y": 180,
          "method": "POST", "url": "https://REPLACE_ME.example.com/leads",
          "parameters": [],
          "headers": [ { "key": "Authorization", "source": "secret", "value": "CRM_API_TOKEN" } ],
          "body": "{\"phone\": \"{{phone}}\", \"status\": \"interested\"}",
          "bodyParameters": [ { "key": "{{phone}}", "source": "phone_number", "value": "" } ]
        },
        { "id": "end-1", "type": "end", "name": "Interested", "x": 2360, "y": 180 },
        { "id": "end-2", "type": "end", "name": "Not interested", "x": 1680, "y": 400 },
        {
          "id": "wa-template-1", "type": "wa-template", "name": "Missed-call template", "x": 1340, "y": 620,
          "provider": "whatsapp", "templateId": "REPLACE_ME_TEMPLATE",
          "templateName": "", "languageCode": "", "templateBody": "",
          "phoneNumberId": "", "displayPhoneNumber": "", "parameters": []
        },
        { "id": "wait-1", "type": "wait", "name": "Wait a day", "x": 1680, "y": 620, "minutes": 1440 },
        {
          "id": "send-call-2", "type": "send-call", "name": "Second call", "x": 2020, "y": 620,
          "agentId": "REPLACE_ME_AGENT", "retries": 0, "retryGaps": [], "retryGapMinutes": 30
        },
        { "id": "end-3", "type": "end", "name": "Done", "x": 2360, "y": 620 }
      ],
      "edges": [
        { "id": "edge-1", "from": "start-1", "fromHandle": "out", "to": "send-call-1" },
        { "id": "edge-2", "from": "send-call-1", "fromHandle": "out", "to": "conditions-1" },
        { "id": "edge-3", "from": "conditions-1", "fromHandle": "exit-picked", "to": "conditions-2" },
        { "id": "edge-4", "from": "conditions-1", "fromHandle": "exit-missed", "to": "wa-template-1" },
        { "id": "edge-5", "from": "conditions-2", "fromHandle": "exit-interested", "to": "update-lead-1" },
        { "id": "edge-6", "from": "conditions-2", "fromHandle": "exit-not", "to": "end-2" },
        { "id": "edge-7", "from": "update-lead-1", "fromHandle": "out", "to": "api-basic-1" },
        { "id": "edge-8", "from": "api-basic-1", "fromHandle": "out", "to": "end-1" },
        { "id": "edge-9", "from": "wa-template-1", "fromHandle": "out", "to": "wait-1" },
        { "id": "edge-10", "from": "wait-1", "fromHandle": "out", "to": "send-call-2" },
        { "id": "edge-11", "from": "send-call-2", "fromHandle": "out", "to": "end-3" }
      ]
    }
  }
}
```

Fix after importing: the agent on **First call** and **Second call**, the
template and sending number on **Missed-call template**, the URL and the
`CRM_API_TOKEN` secret on **Tell our CRM**, and check that `lead_status` exists
in CRM → Attributes and that the agent extracts an `interested` post-call
variable.
