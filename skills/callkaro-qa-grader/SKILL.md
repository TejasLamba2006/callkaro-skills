---
name: callkaro-qa-grader
description: Grade CallKaro QA test calls from history. Use when reviewing tester transcripts, scoring prompt vs function vs config faults, checking dispositions, or writing QA findings back to the team.
---

# CallKaro QA Grader

Grade tester calls from Call History JSON, not from vibes. Pull with `ck calls list --limit N --json`, then score each call on the four fault layers below.

## 1. Pull the batch

```bash
ck calls list --limit 100 --json > qa-calls.json
```

Filter to the tester number and agent. Keep `transcription`, `functions_called`, `call_metadata`, `disposition_reason`, `hangup_reason`, `call_duration` per call.

## 2. Score four fault layers

- Prompt: wrong line, wrong branch, missing branch, contradictory reply ("Sorry to hear that. Glad to hear"), trust-script hijack of a direct question, silent hangup on refusal.
- Function: wrong next_action, wrong spoken_response (long input called shorter), attempts miscounted, partial stitch failure, range speech ("1 to 6") not expanded.
- Config: name spelled letter by letter (stale Custom preformat), Devanagari rendering on English calls, missing `{{var}}` in prompt text drops the Test Call dialog field, voice too fast or shrill.
- Metadata: empty `company_name` / `last_4_digits` / `OTP` in the test set. Blank vars render as silence or "ending in" with nothing. Fix the test set before blaming the prompt.

## 3. Read dispositions with suspicion

`disposition_reason` is LLM-written and often wrong. Known bad patterns: claims "verified" on calls with zero function calls, claims "two attempts" on calls with empty `functions_called`, marks refusal handling as "failed after two attempts". Always cross-check against `functions_called` before quoting a disposition.

## 4. How the tester works (observed)

A good tester runs a matrix, not random calls. Expect these shapes:

- Happy path with correct code first try.
- Short code then full code (partial stitch check).
- Long code then correct code (length branch check).
- Range speech ("1 to 6", "start from 1 ended at 6").
- Wrong code twice (FAILED close check).
- Refusal to share OTP (speak-then-end check).
- "Already verified" repeat call (repeat-caller path check).
- "What is the process" / "what will be verified" (direct-answer vs trust-script check).
- Bare "Hello" with pauses (hello-guard check).
- Hindi mid-call (English-only exit check).
- Wrong-person open ("No") and dispute ("someone else used my number").
- Zero-second `USER_UNRESPONSIVE` calls are dial attempts that never connected. Exclude from grading.

Mark each call: pass, prompt fault, function fault, config fault, metadata fault, or tester-side (no answer, wrong number dialed).

## 5. Write findings back

One line per fault: call id, what the tester did, expected vs actual, layer. Group repeats (same fault across N calls counts once). Anything needing the client (new wording, new branch outcome) goes in a separate ask list, not mixed with fixes.
