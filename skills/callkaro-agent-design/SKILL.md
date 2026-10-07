---
name: callkaro-agent-design
description: Design a CallKaro voice agent before writing any prompt. Use when starting a new agent or a new version with new behaviour, choosing between single prompt, multi-prompt capabilities and pathway nodes, deciding what goes in the base prompt vs a capability, sizing capabilities, deciding what a pre-call function should compute instead of the prompt, or when a prompt has grown into if/else ladders and ping-pong switching.
---

# Designing a CallKaro Agent

An agent is designed, then written. Most bad agents are design failures that people try to fix with more prompt text. Know the business problem, the outputs the client needs, the data that arrives, the architecture, the stages and where every function sits before the first prompt line exists.

Next steps after design: `callkaro-conversational-agents` (write the prompt), `callkaro-functions` (pre/in/post-call code), `callkaro-post-call` (variables and outcomes), `callkaro-qa-framework` (test it), `callkaro-agent-review-debug` (review and root-cause fixes). Field reference: `callkaro-voice-agents`. Commands: `callkaro-cli`.

## Intake: collect before designing

If something essential is missing, ask once, in one batch.

1. Client and use case.
2. Call direction (outbound or inbound).
3. Languages, and whether languages switch inside one version.
4. Scope of work (SOW) or call-flow document.
5. Metadata fields that arrive with each call (names and example values).
6. Expected outputs: post-call variables and dispositions. Without a document, derive them from the use case.
7. Integrations and APIs (pre-call data, in-call lookups, post-call writes).
8. Constraints: latency, cost, call length.

Never invent model, voice or transcriber configs, IDs, metadata keys, endpoints or business facts. Discover them (`cku models`, `cku voices`, `cku transcribers`) or ask.

## Choose the architecture

| Type | Name | What the LLM sees each turn | Flow moves by | Best for |
|---|---|---|---|---|
| 0 | Basic (single prompt) | the whole `systemprompt` | the LLM follows the flow in the prompt | short, simple flows; lowest latency, most conversational |
| 1 | Advanced | `role`, `goal`, `instructions`, `callFlow`, `guardrails`, `rebuttals` fields | same as Basic, sections editable separately | platform-supported, rarely used in current builds |
| 2 | Multi-prompt | base prompt + active capability (+ any sticky one) | the LLM calls `switch_capability` | long or branched flows |
| 3 | Pathway | agent persona (base) + active node | the platform switches nodes on transition conditions | complex flows needing deterministic switching |

Why each exists: Basic sends the full prompt every turn, so long flows cost more, hit context limits and hallucinate more. Multi-prompt sends only base + current stage. Pathway fixes multi-prompt's weak point (the LLM misjudging when to switch, or knowing but failing the tool call): the LLM only extracts variables and the switch is programmatic.

Choosing:

1. Short flow, few branches: type 0. Simpler, faster, more natural.
2. Long or heavily branched: type 2 or 3.
3. Prefer 3 when switch points can be written as conditions on metadata or on variables the LLM extracts reliably.
4. A badly designed 2 or 3 performs worse than a well-designed 0. Architecture does not replace design.

### Multi-prompt mechanics (type 2)

- `systemprompt` is the shared base (persona). `capabilities` are the flow blocks; each has a unique `capability` name and `system_prompt`; exactly one has `is_starting: true`.
- `overwrite: true` drops the base prompt while that capability is active. Rarely wanted.
- `stick_capability: true` keeps that capability's prompt in context after switching away; every other capability is swapped out. Typical: a sticky start capability stays while negotiation is swapped for deal closure.
- `functions` and `postcall` on a capability are scoped to it.
- `llms` sets `primary_model`, `secondary_model` (fallback) and `temperature` (0 to 1) per capability, so a small start capability can run a small model and a long negotiation capability a larger one.
- `msg_while_switching_type` is `static`, `dynamic` or `silent`, with `msg_while_switching` holding the line or generation prompt.
- Switching is an LLM tool call: the prompt must say exactly when to switch and to which capability. Never route to the capability you are already in.

### Pathway mechanics (type 3)

Observed, not a rulebook; conventions are still forming.

- Base `systemprompt` is the persona; `capabilities` are nodes. `node_type` is `normal` (moves only through its transitions) or `global` (reachable anywhere via `when_to_jump`).
- `transitions`: `{condition_type, condition, next_capability}`. `condition_type: 1` is a strict bracketed expression, e.g. `((metadata.lead_intention == 30) AND (user_busy == false))`. `condition_type: 0` is a natural-language condition the LLM evaluates ("user wants only a time change, same address").
- `extract_variables` (`string`, `number`, `boolean`; `name`, `description`, `is_required`) are values the LLM extracts while in that node; transition conditions can use them.
- `position` is the canvas location: preserve it on updates. Every node must be reachable from the start node, and every `next_capability` must match an existing node name exactly.
- Seen in practice: the start node extracts `user_busy` and routes with strict expressions mixing metadata and that variable; intent branching uses natural-language transitions; each node prompt opens with a one-line job and, where needed, an entry gate checking it was reached for the right reason.

## Base prompt vs capability or node

- **Base (agent persona)**: everything true for the whole call: role, goal, objectives, call metadata, instructions (speaking style, language, conversation rules), general objections, guardrails. In types 2 and 3 the base contains no stage-specific flow.
- **Capability or node**: only that stage's call flow and the objections that belong to it. Capabilities are flow-stitching blocks; the persona is who the agent is.

## Sizing and boundaries

- One capability or node per call stage.
- Each should hold at least 2 agent turns or 3 user turns before the next switch. A capability that speaks one line and switches again makes the LLM recall and re-enter capabilities it just left. Go smaller only when the flow forces it.
- Every boundary needs a clear condition: where one stage ends and the next begins.
- Together they must cover every branch: list them (busy, wrong person, not interested, agrees, objects, function fails...) and confirm each has a home and an exit.

## Precompute everything knowable before the call

If a decision can be made from metadata before the call starts, make it in a pre-call function, not in the prompt. An if/else ladder in a prompt works, but not reliably: the LLM approximates logic, it does not execute it. The function computes the branch and injects only the result: the right script block, the right line, the right price in words (patterns in `callkaro-functions`).

Worked example from negotiation agents, two layers of dynamism:

1. A strategy computed before the call from two signals (how well the auction performed; the gap between the customer's expected price and the actual one against a threshold) picks a quadrant that sets tone, number of rebuttals and whether to pivot. The prompt receives only the decided strategy block.
2. Rebuttal cohorts are ranked before the call from metadata about the car (age, kilometres per year, refurbishment cost, ownership, inspection pointers), and the agent delivers them one at a time in that order.

Copy the principle, not the content: compute strategy from data first; the prompt carries only the decided behaviour.

## Keep in-call functions few

Every in-call function is a tool the LLM can choose live. More tools make behaviour more deterministic in theory, but cost humanness. Use one only for live data from an API, a serious calculation that depends on what was said in the call, or an action that cannot be missed. Leave conversational judgment to the LLM. One negotiation agent needed only two: one for the next escalation price, one to validate the closing price.

## Deterministic values

Values that must be exact (prices, approvals, closing amounts) are written by functions, not extracted after the call. Post-call extraction once picked the wrong price from negotiation transcripts, so the final offered price is now maintained through the call: a pre-call function sets the first value, the escalation function updates it, the closing-validation function updates it with the confirmed deal price, and a post-call function reads those results and writes the final field.

## Build order

1. Understand the SOW and the business problem.
2. Choose the architecture.
3. Design stages: what each owns, how they connect, the conditions at every boundary.
4. Design the data flow: metadata in, what the P0 function fetches, what each pre-call function computes and which placeholder it fills.
5. Write the P0 pre-call function first; everything else reads what it produced.
6. Write the persona (base prompt).
7. Write the other pre-call functions; decide exactly which placeholders each replaces.
8. Write each capability or node prompt.
9. Write in-call functions and the `function_calling_snippet`.
10. Define post-call variables, post-call functions, model strategy, `conversion_reason`.
11. Configure the rest (`callkaro-voice-agents`).
12. Review (`callkaro-agent-review-debug`), then QA (`callkaro-qa-framework`).

Write to the platform only as a new agent or a new version (`cku agents create`, or `cku agents clone-version` then `cku agents update --versions <new>`). Never edit a live version in place; do not publish, change routing, phone numbers or A/B rules unless asked.

## The design deliverable

State these before writing prompts, and get agreement unless an end-to-end build was requested:

- Architecture and the reason.
- Capability or node map: name, job, entry condition, exit conditions, model.
- Data flow: metadata in, P0 enrichment, each pre-call function with inputs, outputs and placeholders filled.
- Function inventory: lifecycle, scope, trigger, inputs, outputs, side effects, and which function owns each mutation.
- Post-call variable list with types, and the conversion rule.
- Configuration notes: languages, opening, ending, latency choices.

## Common design mistakes

- If/else ladders on metadata inside the prompt.
- Stage flow in the base prompt, or persona rules repeated in every capability.
- Tiny capabilities that speak one line and switch.
- Patching a bug with another "NEVER" line instead of finding the cause (`callkaro-agent-review-debug`).
- Choosing multi-prompt or pathway because it sounds more advanced, for a flow that fits one prompt.
