---
name: callkaro-agent-review-debug
description: Review a CallKaro voice agent or find the root cause of a bad call. Use when auditing an agent version or prompt, scoring it, hunting contradictions and duplication, or when a call went wrong and someone wants to add a rule. Covers the 7-layer review order, the most common findings, and a root-cause debug method (evidence, frequency, layer, existing text, smallest fix, verify) that forbids patching with another NEVER line.
---

# Reviewing and Debugging an Agent

Two jobs, one discipline: find the cause before touching the prompt. The failure to avoid: someone pastes an issue into an LLM, it appends another rule, the rule ships, and nobody knows why the issue happened or whether it is fixed. Each patch adds duplication and contradiction until the prompt cannot be maintained.

Companions: `callkaro-agent-design` (what a good design looks like), `callkaro-conversational-agents` (prompt body), `callkaro-functions`, `callkaro-post-call`, `callkaro-qa-framework` (scored review plus simulations), `callkaro-qa-grader` (grading tester calls), `callkaro-cli` (commands).

## Review order

Each layer depends on the one before it.

1. **Design.** Read the SOW first. Does the architecture fit the flow? Are stages real stages (at least 2 agent turns or 3 user turns)? Boundaries and transition conditions defined? Do capabilities or nodes together cover every branch? Is everything knowable before the call handled by pre-call functions, not prompt logic?
2. **Prompt structure and content.** Numbered, titled sections in order. Base vs capability content in the right place. No duplication, contradiction, leftover text, emoji or exaggeration. Instructions clear and short. SAY lines at decision points, GOAL blocks short, "how to use this prompt" present where required. Universal objections covered. Endings correct. Metadata placement right for latency (per-call data last).
3. **Functions.** Right type and scope for each. P0 loads data; other pre-calls replace the placeholders they own and none stays raw. In-call functions few and justified, gates in `function_calling_snippet`. Post-call functions follow the concurrency and logging rules. No function mentioned by the prompt is missing from the active scope.
4. **Post-call variables and metadata.** Every metadata field the flow needs is used; every output the SOW asks for exists; descriptions self-contained and English; dispositions and `conversion_reason` match the SOW; exact values come from functions.
5. **Data flow.** Trace one call end to end: metadata in, P0, each pre-call, each placeholder, in-call updates, post-call overrides, cleanup, webhook. Nothing read before it is written; nothing written twice by different owners.
6. **Configuration against the SOW**: opening, endings and `end_call_msg`, silence, voicemail, time limit, background noise, language settings (`language_switch_min_words` equals the prompt rule), pronunciations, pre-formatting.
7. **Model-size flag**: an expensive, large model on a very small capability or prompt.

Out of scope for review: LLM, STT and TTS selection (except flag 7) and hardcoded API keys in older functions.

Inspect completely before scoring: full prompt text, full capability prompts, function source. Previews are for discovery only. `cku agents get <id>` and `cku agents export` give the full version; `cku agents versions <id>` lists versions.

Score each check 0 to 10 with what is good, what is bad, the smallest fix and a precise reference (section, capability, function, field). Scoring bands and workbook: `callkaro-qa-framework`.

Output format when not producing the workbook:

| Area | Check | Score | Good | Bad | Fix | Reference |
|---|---|---|---|---|---|---|

## Most common findings

- Contradictions between base prompt and a capability, or between two capabilities.
- The same instruction written three times in different words.
- Prompt if/else logic a pre-call function should resolve.
- Persona-wide rules repeated inside capabilities, or stage flow inside the base.
- One-line capabilities that cause ping-pong switching.
- Placeholders no function replaces, or a function replacing a placeholder that no longer exists.
- Post-call descriptions referring to prompt-only terms the analysis cannot see.
- A terminal branch with no closing line.

## Debugging: root cause, never a patch

1. **Evidence.** Get real call ids. Read the transcript (`cku calls get <id>`) and the raw log (`cku calls logs <id> "grep -E ' - (ERROR|WARNING) - ' /call.log"`). Note the exact turn where behaviour went wrong and which capability or node was active. Check `chat_history[].metrics.llm_metadata.model_name` first: a `FallbackAdapter` turn means the platform's degraded model ran, so behavioural faults in it are infrastructure, not prompt.
2. **Frequency.** How often? Look across calls (`cku calls list`, post-call flags) and reproduce in simulation (several runs, `cku sim run ... --epoch 5 --wait`). A one-off and a 40 percent failure are different problems.
3. **Root-cause layer.**

| Layer | Typical symptoms |
|---|---|
| Data / metadata | wrong or missing value spoken, placeholder spoken aloud, wrong branch from the start |
| Design | agent stuck or bouncing between capabilities, branch with no home, switch at the wrong moment |
| Prompt | contradictory behaviour across calls, a rule ignored because another overrides it, ambiguous instruction |
| Function | wrong result, error, timeout, repeated side effects, agent claims an action that did not happen |
| Configuration | call does not end (closing line not in `end_call_msg`), wrong language, silence handling, transcription or voice issues |

4. **Check existing text first.** Search the prompt and snippets for anything that already covers or contradicts the behaviour. Most "missing rules" are present but overridden elsewhere. Quote what you find.
5. **Fix at the root, smallest change.** Prefer, in order: fix data or a pre-call function; fix design; remove or merge conflicting text; fix the function; add a rule only when one is genuinely missing. For a rule the agent keeps missing, deliberate double placement in prompt and snippet is allowed; contradictions between the two never are.
6. **Verify.** Apply in a NEW version (`cku agents clone-version`, then `cku agents update --versions <new>`). Rerun the failing case 5 times plus related regression cases; compare with the old version.
7. **Report**: symptom, evidence, frequency, root cause, fix, verification result.

### Do not

- Add a rule because one call misbehaved.
- Fix without reading the transcript and the log.
- Declare it fixed without rerunning the case.
- Edit a live version in place.

## Using an LLM for this well

An assistant with the CLI amplifies whatever method you give it. Ask it for the root cause with evidence and frequency, to check existing prompt text for conflicts, and to show the smallest fix; then verify with simulations. Never ship a suggested patch without that loop.
