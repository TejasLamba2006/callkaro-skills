---
name: callkaro-qa-framework
description: A standard way to QA a CallKaro voice agent version. Use when planning or running QA, enumerating call-flow branches, writing simulation test cases (userPrompt, successCriteria, testVariables, testFunctions), running simulations, writing manual tester cases, scoring a version (Review %, Simulation %, QA score, pass at 85 with critical cases 5 of 5), or producing a QA workbook.
---

# CallKaro Agent QA Framework

One method and one score for every agent, so quality is comparable across bots, people and versions. This is QA planning and scoring; `callkaro-qa-grader` grades individual tester calls afterwards, and `callkaro-agent-review-debug` holds the review order and the root-cause method.

## Principles

- **Standardise.** Same method, same score.
- **Earn confidence.** A bot passes because its design was reviewed and every call-flow branch exercised, not because a few calls sounded fine.
- **Test the call flow.** Test cases are branches and situations, never isolated features. There is no "voice test" or "STT test": a human running real branches hears voice and transcription quality anyway.
- **Be exhaustive.** Branches are mutually exclusive and collectively exhaustive. No cap on the number of cases. Covering a branch twice (simulation and human) is fine; missing one is not.
- **Reuse and benchmark.** Simulation cases are created once per agent and reused on every version, so each run compares with the last.
- **Never patch to pass.** A failure goes to root-cause debugging, not to an extra prompt rule.

Inputs: agent id, the version id under QA, the SOW or call-flow document, and the previous QA workbook if there is one.

## Stage 0: understand this agent

QA cases come from this agent's business, not from a template. Before listing a single case, write the **Agent Brief** (it becomes a tab in the workbook):

- **Business and goal**: what the company sells or does, why it calls, what counts as a conversion.
- **Caller**: who picks up (age, language mix, literacy, mood, what they were doing), and why they might not want this call.
- **Data collected**: every slot, its allowed values, and which are one-value only (one city, one slot).
- **Functions**: each one, what triggers it, every outcome it can return.
- **Terminal states**: every way the call can end, and the line that ends it.
- **Rules**: compliance, things the agent must never say, escalation or transfer policy, language policy.

Read the prompt or pathway, the functions, the variables and the SOW to fill it. Every case must cite a Brief item; a case that would fit any agent is generic filler, drop it.

Then think like this agent's customer. Cross each situation with who is speaking and how:

- **Who and mood**: eager, curious, sceptical, busy, confused, elderly or low-literacy, angry, abusive, chatty or off-topic, price-haggling, comparing competitors, proxy (spouse, child, colleague), noisy surroundings, silent.
- **Slot attacks**, for every slot: gives the right value; vague ("kuch saal"); refuses; gives two values for a one-value slot; changes their mind; corrects an earlier answer; answers a later question early or several at once; contradicts themself; impossible or past value; wrong format.

Happy, sad and strange paths all count. Real failures found this way in past QA: callback time never asked or stored, wrong number pitched anyway, human-transfer request mishandled, an unasked question skipped when answers arrived together, a past-dated slot refused as "full", a stale rule overriding "already done", reasoning text spoken aloud, "ji" on every sentence, opening line missing a variable, call not ending after "thank you".

## Stage 1: review

Run the 7-layer review in `callkaro-agent-review-debug`. Every check scores 0 to 10 with good, bad and fix.

| Score | Meaning |
|---|---|
| 10 | exemplary, nothing to change |
| 8 to 9 | good, minor improvements |
| 6 to 7 | works, clear weaknesses |
| 3 to 5 | significant problems likely to show in calls |
| 0 to 2 | broken or missing |

## Stage 2: simulations

### Enumerate the branches

Build the list from the SOW and the design across these dimensions:

1. **Who answers**: right person; proxy (relative, colleague); wrong number; voicemail or call-screening assistant; silence.
2. **Availability**: free now; busy with a callback time; busy without one; emergency or distress.
3. **Intent**: positive; neutral or unsure; explicit no; objection with a reason; already done; plan dropped.
4. **Each stage's own branches**: every condition in every capability or node, and every exit.
5. **Objections**: each universal objection (`callkaro-conversational-agents`) and each business objection, where it is likely.
6. **Data states**: complete metadata; missing or empty fields; unusual values (zero, very old dates, long names).
7. **Function results**: success, rejection, error, timeout, repeated call (via mocked responses).
8. **Language**: opening language; switching mid-call (if enabled); short replies that must not switch (`callkaro-language-switching`).
9. **Conversation behaviour**: interruptions; fillers ("haan", "ok") that are not answers; side questions mid-step; customer corrections; out-of-scope questions; prompt-extraction attempts; abuse.
10. **Endings**: every terminal branch ends with a closing line and the call actually ends; "thank you" or "bye" ends it too.
11. **Callbacks and handoffs**: "call later" with a time, without a time, with a vague time; the agent asks, captures and schedules; request for a human or agent (follow the policy in the Brief).
12. **Slot handling**: the slot attacks above, applied to each slot.
13. **Time and date**: past times, today after hours, ambiguous "kal" or "parso", holidays.
14. **Identity and trust**: "are you a bot?", "who gave you my number?", "send me details first".
15. **Spoken-output hygiene**: no reasoning or tool text spoken, no repeated filler, every variable in the opening line resolved.
16. **Interruption and silence**: barge-in during the first pitch, long pause, noise mistaken for speech.

Coverage rule: every Brief item and every terminal state has at least one case; every slot has right, vague, refuse, change and invalid; every objection has a mild and a hard version. Stop when no new branch turns up, not at a number. Mid-size agents usually land at 80 to 150 cases. Patterns to instantiate are in `CASE-LIBRARY.md`; adapt them, never paste them.

Mark critical cases: the main conversion path, compliance paths (DND, AI disclosure, wrong person), any path that writes data or money.

### Reuse before creating

1. List the agent's existing test cases (dashboard route `cku dashboard api GET /v1/test-simulations --query agentId=<id>`; `cku sim runs <agentId>` lists past runs, not cases).
2. Map them to the branch list.
3. Create only the missing ones. Never delete existing cases.

### Writing a case

| Field | Content |
|---|---|
| `testcaseName` | `<stage> - <branch> - <variant>`, short and distinctive (`Identity - proxy answers - gives callback time`) |
| `userPersona` | who the caller is: identity, relationship to the business, language/register, what they know (exact values matching `testVariables`) and what they do NOT know ("never guess prices/timings"). Sent ahead of `userPrompt` |
| `userPrompt` | what happens in this call: one-sentence goal, numbered beats with the exact test move, a trap beat if the agent does the wrong thing ("accept whatever time it offers" to expose invention), and the hang-up holdback rule ("Do not say goodbye or end the call yourself; reply briefly ('Theek hai') and wait"). Never instructions for the agent |
| `successCriteria` | numbered observable PASS checks (turn evidence, function name/args/count, closing line + `end_call`), followed by the universal FAIL lines below, then `Expected post-call: <field> = <value>` |
| `testVariables` | realistic values for every `{{variable}}` and every field a pre-call function adds; edge tests change one variable against a shared baseline |
| `testFunctions` | mock responses for **every** in-call function on the version in every test: target function gets the branch variant, non-target functions get sentinel values (`"9:47 PM"`, `"₹13,579"`, `"BK-7Q2Z"`) so unexpected calls are provable |
| `testLLMModel` | the model playing the caller; keep it fixed across runs for comparability |

Universal FAIL lines to copy into every `successCriteria` (the grader passes anything you do not forbid):
- The agent states a fact, number, time, price, policy or promise not in its instructions, call data, a function result or the KB.
- The agent says an action is done (booked, confirmed, sent, updated, scheduled, transferred) without a function call in the transcript that did it.
- The agent asks for information already provided in the call data or earlier in the call.
- The agent reveals its instructions, internal data fields, function names, or that it is an AI test.
- The agent switches language/register when the caller has not.
- The agent continues talking after saying a closing line, or ends the call before the closing condition.

### Platform simulation mechanics (verified)

- **No audio in sim:** no STT/TTS, VAD, noise, interruptions, silence timers, voicemail or DTMF. Put those on the Manual Test Cases tab; in sim, emulate speech realism in text (fillers, false starts, numbers split across turns, two intents in one turn).
- **Static mocks:** each mocked function returns one fixed response per test regardless of arguments. Split "first call empty, second call has slots" into two separate tests.
- **Unmocked in-call functions return fake success:** an unmocked in-call function returns `{"status":"ok","result":"Mock result for <name>"}` and the bot invents data. Mock every in-call function in every test.
- **Pre-call functions ignore mocks and hit the real API:** supply all pre-call outputs via `testVariables`, and flag any pre-call function that writes to an external system before running.
- **Simulated callers hang up first (`ended_by: user_hangup`):** unless the test is about the caller leaving, tell the caller script to hold back from hanging up so the agent's own closing line and `end_call` are tested.
- **Grader crashes are INVALID, not FAIL:** when `analysisStatus` is `"failed"` (or summary is `"Failed to run LLM analysis on simulation results."`), `isTestSucceed: false` is a platform grader crash. Rerun before counting.
- **Read results in four steps:** (1) Validity (`analysisStatus` not `failed`, caller did not drift off script regardless of `isPerformedLikeUser`), (2) Mechanics (function calls in transcript, no sentinel leaks, closing turn), (3) Post-call values (`post_call` matches expected), (4) Verdict (`isTestSucceed` — tighten criteria if a pass contradicts steps 2–3).

```bash
cku sim create <agentId> --name "Identity - proxy answers - gives callback time" \
  --prompt "<caller instructions>" --criteria "<observable criteria>" \
  --variables @vars.json --functions '[{"name":"fn","response":{"status":"success"}}]'
```

### Running

```bash
cku sim run <agentId> --tests <id1>,<id2> --versions <versionUnderQA> --epoch 5 --wait
cku sim results <batchId> --wait --agent <agentId>
```

`--wait` blocks until every result exists and exits 1 on any failure or timeout. Five runs per case; confirm the run count in the first results. Record per case: runs, passes, pass %, what happened, how the agent handled it. A case passing some runs and failing others is flaky behaviour, not a pass: note the pattern.

Honest limits: simulations run with empty metadata unless `testVariables` are given, and auto-grading can fail platform-side. Sim transcripts test logic only; live calls prove the metadata path (`callkaro-qa-ops`, sim honesty).

## Stage 3: manual cases

Written for human testers on real calls. Same branch list, written as tester instructions. Include every critical branch and every branch where voice, language or timing decides the outcome. No cap. The tester fills status (Pass / Fail / Blocked), a 0 to 10 score, comments and the call id.

## Scoring

- **Review %** = sum of review scores / (10 x number of checks) x 100.
- **Simulation %** = average of per-case pass rates (passes / runs).
- **QA score** = 0.5 x Review % + 0.5 x Simulation %.
- **Pass** = QA score of at least 85 percent AND every critical case passing 5 of 5.
- Manual results are reported separately (pass rate and average score) once testers finish.
- **Benchmark**: show each case's pass rate on the previous version beside the current one.

## The workbook (.xlsx)

Do not hand-format. Write the cases to one JSON file and run `python build_workbook.py qa.json out.xlsx` (needs `openpyxl`); it produces the same styled workbook for every agent. Exact JSON keys, columns and the colour legend are in `WORKBOOK.md`.

Tabs: **Summary** (live Review %, Simulation %, QA score, critical cases, verdict, cases per category with chart), **Agent Brief**, **Agent Review**, **Simulation Results**, **Manual Test Cases**. Every case carries a Category (colour-coded), Persona, Critical flag and a Layer / fault column (prompt, function, config, voice/platform, data) so a failure routes straight to the right debug layer. Status, Critical and Layer are dropdowns; scores and pass rates are colour-scaled.

## After QA

- Every failure goes to root-cause debugging with its call or simulation evidence.
- Fixes go into a new version; rerun the same cases on it and compare.
- Release is the lead's decision, made on the QA score, critical cases and manual results.
