---
name: callkaro-workflows
description: Build, import, enroll into and debug CallKaro Workflows, the visual automations that walk each contact through calls, waits, WhatsApp, API calls, branches and CRM updates. Use when turning a follow-up plan or sales cadence into a workflow JSON file, choosing step types, writing Conditions, enrolling contacts from the CRM or POST /workflow/assign, or finding why a run took the wrong path.
---

# CallKaro Workflows

Docs: https://docs.callkaro.ai/workflows/introduction. Dashboard: Workflows, Create Workflow, Normal Workflow (type is fixed at creation).

A workflow is a graph drawn once. Every enrolled contact gets their own run that walks it from Start to End. The runtime is deterministic: Conditions compare values, nothing decides freely. No parallel branches, a run follows one path.

## Steps

| Type key | Step | Notes |
|---|---|---|
| `start` / `end` | Start, End | Exactly one Start. End has no exits. One End per path is normal. |
| `send-call` | Send Call | Needs `agentId`. Waits for the call and all retries (run shows Awaiting call). If the call cannot be placed (no credit, DND, bad number) the run moves on at once, so follow it with a Conditions step on `connected_call`. |
| `wait` | Wait | `minutes`, whole, at least 1. 1440 is a day. No "wait until 10 am". |
| `conditions` | Conditions | Ordered exits, first match wins, exit with no `condition` is Otherwise, put it last. No Otherwise means an unmatched run stops there. |
| `wa-template` | Send WhatsApp Template | Provider whatsapp, heltar or aisensy. Sending number required. Use this for anyone who has not written in. |
| `wa-message` | Send WhatsApp Message | Free text. Only inside the 24h window after the contact's last message, WhatsApp and Heltar providers only. |
| `api-basic` | API Call Basic | `method`, `url`, `headers`, `body`, with `{{placeholders}}`. Result `{ok, status, body}`. 30 s. |
| `api-advanced` | API Call Advanced | `code`: one named `async function name(context)`. Sandbox: axios, moment, lodash `_`, `sendEmail`, `x_secrets`. No require, no fs. 30 s, 256 MB. |
| `update-lead` | Update Contact | `updates: [{attribute, source, value}]`. Attribute must already exist in CRM, Attributes. Hand-edited CRM values are never overwritten. |

## Send Call fields

`agentId` (required), `retries` 0 to 10, `retryGaps` (minutes per retry, `[30,120]`), `retryGapMinutes` (default 30), `scheduleAt` (IST `YYYY-MM-DDTHH:mm:ss`), `metadata` rows `{key, source, value}` that the agent reads as `{{metadata.<key>}}`.

## Value sources

Used by conditions, placeholders, headers, Update Contact rows and call metadata: `static_value`, `phone_number`, `contact` (CRM attribute), `call_metadata`, `post_call_variables`, `fn_response` (`<nodeId>.<path>`, e.g. `api-basic-1.body.status`), `connected_call`, `voicemail`, `hangup_reason`, `call_duration` (seconds), `conversion_status`, `secret` (API Basic headers only).

The last-call sources are empty until a Send Call has run. Put a Send Call before any Conditions that tests them. `connected_call` is true for `CLIENT_INITIATED`, `PARTICIPANT_REMOVED`, `SESSION_TIMEOUT`; use it instead of testing `hangup_reason` yourself.

## Condition operators

`eq`, `ne` (trimmed, case-insensitive), `contains`, `gt`, `lt` (both sides numeric, text never matches), `empty`, `not_empty`. Booleans compare as text: `{"source":"connected_call","field":"","op":"eq","value":"true"}`. Order rules specific to general: a broad "connected is true" above "interested is yes" sends the interested ones down the wrong path.

## Run statuses

Running, Waiting (Wait step or scheduled start), Awaiting call, Completed, Failed, Cancelled.

## Import file (Workflows, Import)

Same shape as Export, so an export can be edited and imported back. Import always creates a new workflow and never enrolls anyone.

```json
{ "type": "callkaro_workflow", "version": 1,
  "data": { "workFlowName": "Lead follow-up", "type": "normal",
            "graph": { "nodes": [], "edges": [] } } }
```

Node: `{id, type, name, x, y, ...type fields}`. Ids unique, form `<type>-<n>`, no `.` in ids (breaks `fn_response` paths). Edge: `{id, from, fromHandle, to}`, `fromHandle` is `"out"` for every node except Conditions, whose handles are the exit ids. One edge per exit. Layout: Start at x 320, y 180, each next step 340 px right, each extra Conditions branch 220 px lower.

Import rejects: not exactly one Start; missing or duplicate node id; unknown type; `wait` without minutes; `send-call` without `agentId`; `api-basic` without `url`; `api-advanced` without `code`; `wa-template` without `templateId`; `wa-message` without `message`; Conditions with no exits, duplicate exit ids, or a rule missing its field; `update-lead` with no rows or a row missing attribute, source or needed value; edge to a missing node, out of an End, into Start, or with a bad `fromHandle`; no path from Start to an End. Import does not check that IDs are real, so an invented agent id imports fine and fails on the first call.

On the canvas: Add Node menu (End, Send Call, Send WhatsApp Template, Send WhatsApp Message, Wait, Conditions, API Call Basic, API Call Advanced, Update Contact), "Tidy up" lays nodes out left to right, "Find a node" jumps to one, zoom controls, a "Cannot save" counter lists blocking problems, and a new workflow is saved with the "Create Workflow" button (named "Save" in the docs). Create is at `/workflows/create-normal`. Clicking a node opens its settings panel with Delete node.

Create/Save also checks one Start, a Start to End path, live connections, complete node settings. It only warns on unreachable nodes and dead-end branches. Loops are allowed, a run stops itself after 500 steps.

## Placeholders to use when an ID is unknown

`REPLACE_ME_AGENT` for `agentId`, `REPLACE_ME_TEMPLATE` for `templateId`, `""` for `phoneNumberId` (pick the number in the dashboard), `https://REPLACE_ME.example.com/...` for unknown URLs. List every placeholder and every guessed CRM attribute or secret name back to the user. Account-specific things the user must fix after import: voice agent ids, WhatsApp template and sending number (picking the template fills the variable rows), API URLs and the secret names headers refer to, CRM attributes, and that the agent actually extracts any post-call variable a condition reads.

## Cannot do

Parallel branches, wait until a time of day, wait for a WhatsApp reply (no inbound trigger), built-in SMS or email (use API Basic or Advanced), changing an existing workflow by import. Say so instead of faking it.

## Plan to node mapping

| They say | Write |
|---|---|
| call them | `send-call`, then `conditions` on `connected_call` |
| retry after 30 min then 2 h | `retries: 2, retryGaps: [30,120]` |
| next day, after 3 days | `wait` 1440, 4320 |
| if interested | `conditions` on `post_call_variables` + name |
| WhatsApp to someone who has not written | `wa-template` |
| mark lead, update CRM | `update-lead` (CallKaro CRM) or `api-basic` (outside CRM) |
| notify our system | `api-basic` |
| stop, close the lead | `end` |

## Enroll

CRM, Leads, filter, Assign, Assign to Workflow, pick it, start now or Schedule Later. Toolbar Assign covers every page of the filter. A contact already mid-run in this workflow is skipped. CRM attributes ride into the run: the `contact` source reads them and they are copied into call metadata, so `{{city}}` works in the agent prompt.

From your own system, `POST https://api.callkaro.ai/workflow/assign`, header `X-API-KEY` (key of the account that owns the workflow):

```json
{ "to_number": "+919876543210", "workflow_id": "<id from the workflow URL>",
  "attributes": [{ "key": "first_name", "value": "Rahul", "replace": true }],
  "schedule_at": "2026-12-31T09:30:00" }
```

`schedule_at` optional, IST, two digits everywhere, past time starts now. Attribute keys match CRM attributes ignoring case, spaces, underscores, hyphens. `replace: false` (default) only fills empty values, hand-edited values always win. The response lists `updated`, `kept_existing`, `ignored` (no such attribute, never auto-created) and `invalid`; check `ignored` for typos. Errors: 404 wrong id or key from another account, 409 number already running here (attributes still saved), 400 no steps or bad `schedule_at`. Never retry 400, 404, 409. Retry only 5xx, which can start the run twice.

## Monitor and debug

Workflows, open one: Total Leads, Active, Completed, Failed, Cancelled, search by phone. Columns: Status, Current Step, Enrolled, Calls Attempted, Last Call, Duration, Cost. Click a row for the timeline: each step, call SID and outcome, API response, the branch taken and why, errors. Wrong path: open the timeline, look at the Conditions step, it shows the value each rule compared. Usual causes are an empty or differently spelled field, rule order, a last-call source tested before any Send Call, or a post-call variable the agent never extracts.

## Terminal (`cku workflows` and `cku contacts`)

Operate workflows and CRM contacts directly from the CLI (see `callkaro-cli`):

- **Schema & CRUD:** `cku workflows schema`, `list`, `get <id>`, `create <name> --file graph.json`, `import --file wf.json`, `update <id>`, `validate [<id>] [--file graph.json]`, `export <id>`, `duplicate <id>`, `delete <id> --yes`.
- **Surgical node edits:** `cku workflows add-node <id> --type <type> [--after <nodeId>] [--handle <exitId>] [--set <json>]`, `set-node <id> <nodeId> --set <json>`, `remove-node <id> <nodeId> [--reconnect] --yes`, `connect <id> --from <aId> --to <bId> [--handle <exitId>]`, `disconnect <id> --from <aId> [--handle <exitId>]`.
- **Runs & debugging:** `cku workflows leads <id>`, `lead <id> <phone>`, `run <id> <phone> [--json]` (step-by-step timeline, `action_results` and run variables), `journey <id> <phone>` (every call in the workflow for that phone).
- **Enrolling from CRM via CLI:** `cku contacts assign --workflow <id> [--phones a,b | --attr k=v] [--at <ISO>] [--force] --dry-run` (always preview with `--dry-run` first). Manage contacts and CRM attributes with `cku contacts list|get|create|update|delete|upload|export` and `cku contacts attributes list|set|delete`.

## Full spec

`REFERENCE-official-spec.md` in this folder is CallKaro's own complete workflow spec (every field, layout rules, what import rejects, a full worked example). Read it before writing or editing a non-trivial workflow file, and treat it as the source of truth if it disagrees with the summary above. It is also published at https://docs.callkaro.ai/workflows/build-with-claude. Give the model the voice agent ids and CRM attribute names up front, or it returns placeholders. Import creates the workflow, fix the placeholder steps, then enroll.
