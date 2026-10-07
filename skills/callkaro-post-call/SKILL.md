---
name: callkaro-post-call
description: Define CallKaro post-call analysis. Use when choosing or writing post-call variables, selector and reason fields, the post-call analysis prompt, conversion_reason, dispositions and drop-off reasons, the per-duration post-call model strategy, global vs capability scope, or delivering results by webhook vs post-call function; also when extracted values are wrong, empty or inferred from a promise that was never completed.
---

# Post-Call Variables and Outcomes

Post-call analysis turns a finished call into the fields the client reports on. It sees very little, so descriptions must stand alone. Exact values should not be extracted at all (`callkaro-agent-design`, `callkaro-functions`).

## What analysis can see

Four inputs only:

1. the call transcript
2. the call metadata
3. the functions called during the call, with results
4. the description of the variable being filled

It does NOT see the agent's prompt, function code or any other configuration. A description that leans on prompt-only terms ("the Step 3 outcome", "scenario S2") cannot be filled correctly. Define everything in the description itself.

## Choosing variables

- Start from the outputs the client needs in the SOW or call-flow document.
- With no document, derive from the use case: the outcome, the reason, the callback, the customer's stated facts, flags the client acts on (DND, wrong number, language), and a detailed call summary.
- Values that must be exact (prices, amounts, IDs, approvals) are written by functions, not extracted.
- Breadth follows purpose: a handful for reminder or notification bots, roughly 10 to 20 for support and sales qualifiers, 25 to 40 for negotiation agents. Zero means the agent reports nothing, right only for pure fire-and-forget.

## Writing variables

- **Name**: letters, numbers, underscores, starting with a letter; snake_case for new ones. Keep existing names a client contract depends on exactly (e.g. `Mark_DND`).
- **Type**: `boolean` for flags, `selector` for a closed set, `number`, `text` for free text, `object` for structured data, `call_drop_off_reason` for the drop-off reason.
- **Description**: English, written as a precise extraction instruction: when the value is true or what it holds, when it is false or empty, and what to do when the transcript does not show it.
- **Selectors**: list the closed set of allowed values inside the description.
- **Reason pattern**: pair a coded field with a verbatim one, e.g. `reason_code` (selector, closed set) and `reason_verbatim` (text, the customer's own words). Free wording never goes into a coded field.
- **Defaults**: `defaultValue` must match the type (`{}` for objects). Global fields may take their default from metadata through `defaultValueConfig`.

### The analysis prompt (`post_call_analysis_prompt`)

Global rules for extraction. A pattern that works: extract only what the transcript supports; never infer a booking from an agreement that was not followed by a successful write; leave unevidenced fields at default; a wrong value is worse than a missing one.

## Scope

- Top-level `postcall` fields are extracted for every call.
- A capability- or node-level `postcall` belongs to that stage.
- Do not repeat one output name across scopes unless the consumer expects it.

## Model strategy

| Duration bucket | Model |
|---|---|
| `1-10` seconds | `DEFAULT_VALUES` |
| `11-30`, `31-60`, `>60` | `callkaro/krishna-2.5` |
| `only_agent_turns` | `DEFAULT_VALUES` |

`DEFAULT_VALUES` skips extraction and uses the configured defaults. `postcallmodel` is a legacy fallback; use `post_call_strategy`. Model ids come from `cku models --slot post-call` (slots differ: some agent models are not allowed here).

## Conversion and disposition

`conversion_reason` is the rubric analysis uses to judge conversion. Write it as a checklist:

```
CONVERSION EVALUATION
<one line: what conversion means for this call>

MARK TRUE ONLY IF ALL ARE MET
T1. <observable condition, ideally tied to a function result>
T2. ...

MARK FALSE IF ANY ONE IS TRUE
F1. <e.g. the agent announced success but the function did not return success>
F2. ...
```

- Tie conversion to function evidence (the booking function returned success; the closure function approved), not to the customer saying yes.
- `default_disposition_reason` is the fallback disposition; `useOthersDropOffReason` allows an OTHER drop-off reason.
- Post-call functions can set `context.conversion_status` and `context.disposition_reason` deterministically when tool evidence decides the outcome.

## Delivery

- `webhook` sends the standard call payload to one URL; `webhook_headers` carry vault references (`x_secrets.NAME`). Event payloads: `callkaro-webhooks`.
- Use a post-call function instead when delivery needs branching, transformation, several requests or email (`callkaro-functions`).

## Debugging wrong values

| Symptom | Likely cause | Fix |
|---|---|---|
| Field empty or wrong although the call showed it | description relies on prompt-only terms | rewrite self-contained |
| "Booked" true but nothing was written | conversion judged from the customer's yes | tie to the function result in `conversion_reason` |
| Wrong price or amount | extracted from transcript | write it by function (`callkaro-functions`) |
| Value differs between runs | selector set not closed in the description | list allowed values |
| Field overwritten | two functions write it | one writer per field |
| Short calls get junk values | extraction ran on a 1 to 10 s call | `DEFAULT_VALUES` for that bucket |
