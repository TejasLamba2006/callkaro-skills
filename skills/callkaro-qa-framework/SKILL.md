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
10. **Endings**: every terminal branch ends with a closing line and the call actually ends.

Mark critical cases: the main conversion path, compliance paths (DND, AI disclosure, wrong person), any path that writes data or money.

### Reuse before creating

1. List the agent's existing test cases (dashboard route `cku dashboard api GET /v1/test-simulations --query agentId=<id>`; `cku sim runs <agentId>` lists past runs, not cases).
2. Map them to the branch list.
3. Create only the missing ones. Never delete existing cases.

### Writing a case

| Field | Content |
|---|---|
| `testcaseName` | `<stage> - <branch> - <variant>`, short and distinctive (`Identity - proxy answers - gives callback time`) |
| `userPrompt` | instructions for the simulated caller only: who, what they want, how they behave, what they say at the key moment. Never instructions for the agent. |
| `successCriteria` | observable conditions an LLM grader can check: what the agent must say or do, which function it must call, which line ends the call, what it must never do |
| `testVariables` | realistic values for the version's `{{variables}}`; include missing-data variants where that is the branch |
| `testFunctions` | mock responses for every function on the path, in the real response shape, including failure variants where that is the branch. Simulations never call real systems. |
| `testLLMModel` | the model playing the caller; keep it fixed across runs for comparability |

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

Tab 1, Agent Review. Summary block on top: agent name, agent id, version id and name, date, Review %, Simulation %, QA score, critical cases passed, verdict (Pass / Fail). Columns: Area, Check, Score (0-10), What is good, What is bad, Recommendation, Reference.

Tab 2, Simulation Results. Test id, test case name, branch or situation, critical (Y/N), runs, passed, pass %, previous version pass % (blank on first QA), what happened, comment on agent handling, batch id.

Tab 3, Manual Test Cases. TC id, branch or situation, tester persona and setup, what to say, expected agent behaviour (including how the call should end), critical (Y/N), then tester-filled status, score, comments, call id.

## After QA

- Every failure goes to root-cause debugging with its call or simulation evidence.
- Fixes go into a new version; rerun the same cases on it and compare.
- Release is the lead's decision, made on the QA score, critical cases and manual results.
