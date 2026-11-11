---
name: callkaro-functions
description: Write and place CallKaro agent functions. Use when writing pre-call (P0 or prompt-rewriting), in-call, on_connected or post-call functions, deciding global vs capability scope, execution order, internal underscore metadata and cleanup, placeholder replacement, post-call override or failsafe patterns, secrets in function code, or when a function crashes a call (PRE_CALL_FN_FAILED) or two functions fight over a field.
---

# CallKaro Functions

Contracts, scope, order and patterns for custom function code. Skeleton code is in `TEMPLATES.md`. What the runtime exposes (globals, `utils`, `ctx.session`, language switching internals) is in `callkaro-voice-agents/REFERENCE-function-runtime.md`; read it before writing a function that needs more than its arguments. Design context: `callkaro-agent-design`.

## Types and contracts

| Type | Code | Runs | Triggered by | Contract |
|---|---|---|---|---|
| `custom_pre_call`, `update_call_data: true` (P0) | Python | before the call, first of all pre-calls | platform | `async def name(call_data: dict) -> dict`. Mutate `call_data["metadata"]` in place. May create new metadata keys. |
| `custom_pre_call`, `update_call_data: false` | Python | before the call, after P0 | platform | `async def name(metadata: dict, system_prompt: str) -> str`. Start from `system_prompt`, replace placeholders, return a string on every path. Must not create new metadata keys. |
| `on_connected` | Python | once after connection, or once on entering its capability or node | platform | `async def name(ctx: JobContext, metadata: dict)`. Side effects only; return ignored. |
| `custom_in_call` | Python | during the call | the LLM, from the description and prompt | `async def name(ctx: RunContext, arg: str, ...) -> dict`. Typed params (str, int, float, bool, None). Return `{"status": "success", ...}` or `{"status": "error", "message": ...}`. |
| `custom_post_call` | JavaScript | after post-call analysis | platform | `async function name(context)`. Appends exactly one entry to `context.functions_called`. |
| Predefined | none | as configured | LLM or platform | `transfer`, `keep_call_on_hold`, `available` / `booking` (Cal.com only), `send_to_whatsapp`, `assign_chat_agent`. Team rule: do not use the `end` function; end calls through `end_call_msg` lines. |

Injected helpers need no import. Python: `httpx`, `logger`, `x_secrets`, `JobContext` / `RunContext`, `send_email`. JavaScript: `axios`, `moment`, `lodash` as `_`, `console`, `sendEmail`, `x_secrets`. Always set HTTP timeouts. Never use `eval`, `exec`, dynamic imports, filesystem or process APIs. Nest helpers and imports inside the function body. The code is `exec`'d with a shared, cached globals namespace and a separate locals namespace, and the tool is then looked up by name: every other top-level `def` and `import` lands in those locals and is out of scope inside the tool, so calling it raises `NameError` at call time, not at save time. Never assign module-level globals either; that namespace is shared across calls in the process. Log with `logger.warning`; the platform docs say never to use `logger.error`.

The dashboard also offers **Basic mode** for in-call and post-call functions: a single API hit configured in a form, no code. Use it for a plain HTTP call with no transform; everything in this skill is about Advanced (code) functions.

### `x_call_history` (Call Memory)

Read-only list of earlier calls with the same contact, newest first, available in pre-call, in-call and post-call functions when Call Memory is on for the version (`callkaro-voice-agents`, Call Memory). It is an empty list when Call Memory is off or this is the contact's first call. Chat agents have a different variable, `x_history`.

- **Memory is loaded only when the function's code contains the text `x_call_history`.** A helper that receives the list as an argument from another function gets nothing unless the name appears in its own code.
- Entry fields: `call_sid`, `name`, `direction`, `from`, `to`, `time`, `created_at`, `call_duration`, `connected`, `hangup_reason`, `conversion_status`, `disposition_reason`, `post_call`, `call_metadata`, `functions_called`, `language`, `agent_id`, `version_id`, `batch_id`, `workflow_id`, and `transcript` only if "Include call transcripts" is on.
- **Never send the whole `x_call_history` list, or `x_secrets`, to an outside service. The platform rejects function code that does.** Send only the fields you need.
- Typical uses: write a one-line summary of the last call into the prompt from a pre-call function, stop retrying after N unanswered attempts, skip work when the last call already converted.

```python
last = x_call_history[0] if x_call_history else None
note = "The customer asked for a callback on the last call." if last and last["disposition_reason"] == "callback_requested" else "This is a fresh conversation."
```

**Email helpers (`send_email` in Python pre/in-call, `sendEmail` in JS post-call):** neither raises on delivery failure — always `await` and check `result["status"] == "success"` (Python) or `result.status === "success"` (JS), keeping SMTP credentials in `x_secrets["SMTP_USERNAME"]` / `x_secrets["SMTP_APP_PASSWORD"]` and logging the outcome in `context.functions_called` without credentials.

**In-call Python parameter types:** use scalar types only (`str`, `int`, `float`, `bool`, `None`) and annotate `-> dict`. Never use `dict`, `list`, `Any` or `Union` in parameter annotations (breaks strict tool schema); for nested payloads take `str` (JSON) and `json.loads` inside `try/except`.

**`on_connected` sandbox:** signature is `async def <name>(ctx: JobContext, metadata: dict):`. Use `ctx.room`, `ctx.proc.userdata`, or `ctx.api` — `ctx.session`, `ctx.userdata` and `RunContext` are not available in `on_connected`.

## Execution order

1. P0 pre-call functions (`update_call_data: true`) first.
2. Then the prompt-rewriting pre-call functions.
3. The call runs; in-call functions fire when the LLM calls them.
4. Post-call analysis fills variables.
5. Post-call functions run, possibly concurrently: array order is not execution order, so each must be correct alone.
6. Webhook.

Pre-call order inside step 1 and 2, from the backend source (read Nov 2026):

1. **P0** functions run once.
2. **Per-node loop.** Each capability or node prompt is processed by the non-P0 pre-call functions, **skipping any function that has `execute_while_switching`**. The start capability is processed twice.
3. **Merged run.** Every pre-call function runs once more on the merged prompt. Here `system_prompt` is not a plain `str` (see the runtime reference).
4. **Metadata fill.** `{{key}}` placeholders are replaced from the metadata as it stands now. That snapshot is reused for the whole call and never refreshed.

**On every switch** only the functions with `execute_while_switching: True` run again, on the merged prompt, with the **live** metadata. P0 never reruns. An exception there is swallowed: the switch still happens and the placeholder stays as it was, so a failure is silent. Log inside the function if you need to see it.

That is why one pre-call can execute many times in a call (once per node, plus the merged run, plus once per switch if flagged). Keep them idempotent and cheap.

## Global vs capability or node scope

| Type | Global (top-level `functions`) | Inside a capability or node |
|---|---|---|
| Pre-call (prompt rewrite) | replaces its placeholders in the base prompt and every capability prompt it finds them in | replaces placeholders only in that capability's prompt |
| In-call | available to the LLM anywhere | available only while that capability or node is active |
| Post-call | runs after every call | runs only if that capability or node was visited at least once |
| on_connected | once after connection | once when the call enters that scope |

- Put an in-call function where the agent needs it; global only if it can be needed anywhere.
- Never tell the LLM to call a function that is not available in the active capability.
- The same function in several capabilities must be the identical object (name, description, parameters, code). Variants need different names.
- `execute_while_switching` is for a pre-call function that must run every time its capability or node is entered. Set it on a capability-scoped function to fire on entering that node. Can also be set on a global function to make it re-run on every node transition — use only when the function is cheap and idempotent, since it fires on every switch in the call. In pathway (type-3) agents, global pre-call functions run once at call start; if a `{{placeholder}}` only appears in a specific node's prompt, set `execute_while_switching: True` on the function that fills it so the replacement happens on node entry, not only at call start.
- **A flagged function repeats its writes on every switch.** If it sets a metadata key that an in-call function updates later (a starting price that a pricing tool then raises), each switch puts the starting value back. Guard the write ("only if the live key is empty") or do not flag that function.
- `{{key}}` text is filled once, from metadata at call start. A key first created during the call stays as literal `{{key}}` in the prompt; an existing key keeps its call-start value. To get live state in front of the model, return it from an in-call function or rewrite the prompt in a flagged pre-call.

## Pre-call patterns

- **P0 first.** One function owns loading data (fetch lead data for inbound or follow-up calls; overwrite only keys that already exist in metadata). Everything else reads what P0 produced.
- **Split by responsibility**: one function per concern (pricing context, negotiation pointers, greeting, each optional pitch block), not one that fetches, calculates and rewrites everything.
- **Placeholders**: replace the ones the function owns, both `{x}` and `{{x}}` forms. Never leave a raw placeholder in the final prompt; substitute a safe default.
- **Missing or malformed data**: parse defensively (treat `None`, `""`, `"None"` as missing), fall back to a usable line, never crash the prompt. A pre-call exception is `PRE_CALL_FN_FAILED` and the whole call is lost.
- **Speech-ready output**: convert numbers to words before injection (`num2words(..., lang='en_IN')` plus "rupees"); format dates and validity windows as spoken text.
- **Choose blocks, don't describe logic**: the function picks the script block for the situation and injects only that.
- **Deterministic**: same inputs, same prompt.

## Internal metadata

- Values computed for internal use are stored with a leading underscore: `_pitch_scenario`, `_active_price_val`, `_rebuttal_cap`.
- In-call functions update them as the call progresses.
- A cleanup post-call function deletes every `_` key so internal state never shows in call history.
- Post-call functions may run concurrently, so one that needs an internal value reads it from `context.functions_called` (the immutable log of in-call results), not from metadata cleanup may already have removed.

## In-call functions

- Few, and only for live data, conversation-dependent calculation or unmissable actions.
- The `description` is the model-facing trigger: say exactly when to call, what must be collected first, what to do with each result.
- The detailed gates live in `function_calling_snippet`: preconditions, the line to speak before calling, result branches, anti-fabrication ("never claim an action that did not happen", e.g. never say "I spoke to my manager" without calling the escalation function).
- Revalidate inside the function before any side effect (price ceiling, identity, eligibility). The prompt alone is not a correctness boundary.
- Make repeated calls safe: return an already-done or no-op result instead of repeating a booking, write or escalation.
- Return compact data: status plus the next spoken value. Never return secrets, raw upstream payloads or internal limits the caller must not hear.
- Spoken message while running: `msg_while_executing_type` or the prompt, never both. For code (Advanced) in-call tools only `static` does anything: it speaks a random line from `msg_while_executing`. **`static` with an empty list plays an empty line that cannot be interrupted, so never use it as "silent".** `dynamic` and `silent` do nothing and make no extra LLM call. Default to `silent`; use `static` with real lines only when the caller should hear something. (Earlier versions of this skill recommended `static` with `[]` and said `dynamic` costs an LLM call. Both were wrong.)
- Function-first for exact work (digit compare, length judging, math): the model gets these wrong, code gets them right (`callkaro-voice-agents`, live lessons).

### What the platform does around an in-call tool

From the backend source (read Nov 2026). Each of these has caused a live bug.

- **The docstring is model text.** The tool description sent to the LLM is `description` plus the function's docstring, on every turn. Keep the docstring to purpose, when to call and what comes back. No change history, no fix notes, no long examples: one production tool carried about 5,700 characters of it into every turn. A docstring is still required (the save-time judge checks for one).
- **The platform logs every in-call result into `functions_called` itself.** Calling `add_functions_called` from your code writes a second entry for the same call, which reads in call history as the function having run twice. Do not log manually. When the model batches several tool calls in one turn, only the first is auto-logged. A `None` return is logged as `{"status": "no_output"}`.
- **Returning `None` means the bot says nothing after the tool.** Use it on purpose (a silent bookkeeping call), never by falling off the end of a branch. Every other path returns a dict with `status`.
- **`executing_fn_tool` blocks switching.** While that flag is true, `switch_capability` is refused with "Already executing a function tool" and the silence monitor is paused. Any function that sets it must clear it in a `finally`, including on the early-return and exception paths. One init-failure branch that returned without clearing it blocked every switch for the rest of the call.
- `keep_call_on_hold` only sets a hold duration (default 20 s).

### The save-time judge

Every save of a changed function, from `cku agents update` or the dashboard, runs three checks in order, and a rejected save writes nothing:

1. A fixed code policy: blocked imports and builtins, an allow-list of `ctx` attributes, audio only from `assets/*.wav`.
2. An LLM judge that answers yes/no questions about the code and rejects at a probability of 0.5 or more. Because it is a model, **the same code can pass on one try and fail on the next**.
3. A build check.

What the judge looks at: a `status` key on **every** return of an in-call function (including early returns and `except` branches); every path of a prompt-rewriting pre-call returning the prompt string; a docstring; secrets read through `x_secrets` and no hardcoded credentials; and anything that looks like harm or data leaving (files, processes, environment, dynamic code, sending call data or secrets out).

Reading a "This code can't be saved" error: the message names the rule. Fix the code for that rule; do not resubmit unchanged and hope. Typical ones: "A return value isn't a dict with a `status`" (find the return without it, often `return None` or a bare dict in a helper branch), and a false "works with files or folders" on legitimate asset audio, which a one-line docstring note explaining the call clears. Functions saved before the judge existed keep working until their next edit, then fail on rules they never met: budget for that when touching an old function.

## Post-call functions

- **Override**: analysis runs first, so a function can correct its output (replace a value that came back 0 with the metadata value).
- **Failsafe**: any condition can be enforced after analysis by rewriting a post-call value.
- **Deterministic**: compute exact values from in-call results (final price from the approved closing result, else the escalated price, else the offered price).
- Write a derived value to both `context.post_call.<field>` and `context.post_call_detail.<field>` (`{value, comment}`).
- **One writer per field**: two post-call functions never update the same field.
- Wrap the body in try / catch / finally and always push exactly one log entry (`name`, `parameters`, `success`, `response`, `timestamp`).
- Build explicit outbound payloads; never send the whole context.

## Secrets

New code reads from the vault: `x_secrets["API_KEY"]` in Python and JavaScript, `"x_secrets.API_KEY"` as a header value in declarative configs and webhook headers. Older agents hardcode client keys in function code; that is common and not a review finding, but new code should use the vault. `cku secrets set NAME` creates one.

## Common function bugs

- A placeholder no function replaces, or a function replacing one that no longer exists.
- Two post-call functions writing one field; a post-call reading an internal key cleanup already deleted.
- Prompt tells the LLM to call a function that exists only in another capability.
- Expected values read from `ctx` metadata in an in-call function (not visible there): pass them as arguments.
- A side effect without an idempotency guard, so a retry books twice.
- Missing timeout on an HTTP call, stalling the live call.
