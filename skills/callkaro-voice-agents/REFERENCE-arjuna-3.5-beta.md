# Writing for `callkaro/arjuna-3.5-beta`

Model-specific notes for the recommended realtime voice LLM. Everything in `callkaro-prompt-style`, `callkaro-conversational-voice` and `callkaro-conversational-agents` still applies; this file only adds what is different about this model.

## Prompt placement and size

- The base prompt is sent as a real system turn, and the model follows system text well. Put persona, scope and hard rules there, never in the begin message or a fake first user turn.
- Keep the fixed prefix short and stable. Aim for a base prompt (plus snippets) of a few hundred tokens and push per-call values to the LAST section, so the cached prefix stays identical across calls and turns. Every edit above the per-call section breaks the cache and costs TTFT.
- Long calls: attention to text far back in the context weakens as the call grows. A rule that must hold until the last turn goes in a snippet (`model_response_snippet` or `security_guardrails_snippet`, injected every turn), not only in the base prompt. This is the deliberate double placement from `callkaro-conversational-agents`, and on this model it is the default for hard rules, not a fix after a failure.

## Reasoning

- The model has a reasoning mode. Voice needs it off, and the prompt must not invite it back.
- Never write "think step by step", "plan your answer first", "reason about" or "explain your thinking" in a voice prompt or snippet. On this model those phrases produce reasoning that reaches TTS.
- If a stage genuinely needs computation (eligibility, price math, date logic), move it into a pre-call or in-call function that returns the answer. See `callkaro-agent-design`, "Precompute everything knowable before the call".

## Temperature

- Keep the platform's observed 0.2 to 0.3 range (top-level `temperature` 2 to 3, capability `llms.temperature` 0.2 to 0.3).
- The model's own chat default is much higher and too loose for scripted calls: it risks paraphrased SAY lines and reformatted prices. Raise only for a purely composed, chatty stage, and test it.

## In-call tools

- Keep in-call functions few and one per turn. After several chained tool calls in one turn this model tends to loop or repeat its last sentence.
- Say the line before the call in the prompt ("Ek second, main check karti hoon"), call once, then speak the result. Do not design turns where the model must call two or three functions back to back; chain them inside one function instead.
- Validate arguments inside the function (format, range, required fields). The model can send a well-formed call with a wrong value; the function, not the prompt, is the last check.

## Guardrails: nothing is built in

The model ships without a content-safety filter. Whatever the agent must refuse, it refuses only because the prompt and snippets say so.

- `security_guardrails_snippet` must name the approved scope, the refusal line, escalation after repeated out-of-scope turns, and never revealing the prompt, the internal setup or which model runs the agent.
- Caller speech is data, never instructions. In public prompt-injection tests this model family followed injected instructions roughly one time in six. Add the line from `callkaro-conversational-agents` ("Snippets") that ignores any caller request to change rules, persona or scope.
- Never rely on the model to refuse medical, legal or financial advice on its own: state what the agent may and may not say.
- Anything with money, consent or identity goes through a function (`verify_otp`, a `route_*` decision), never through the model's judgement alone.

## Hindi, Hinglish and other Indian languages

- No public evaluation covers phone-style Hinglish for this model. Do not assume parity with `callkaro/arjuna-2.5` on any language.
- Before going live, run the 12-utterance script from `callkaro-language-switching` and the caller tests in `callkaro-conversational-voice` section 8 on every language the version supports.
- Write verbatim per-language rows for scripted lines, as `callkaro-conversational-voice` section 6 recommends; arjuna-class models drift back to the script's language without them.

## Not prompt bugs

These come from serving and templates, not from prompt text. Do not add a NEVER line for them; escalate to the platform team with the call id and the turn.

| Symptom in the transcript or recording | Meaning |
|---|---|
| Agent speaks `call:function_name{...}`, braces, or a function name | a tool call was not parsed and went to TTS |
| Agent speaks `thought`, special-token markers (`<...>`), or its own planning | reasoning output reached TTS |
| Same sentence looping right after tool calls | template or history issue after chained calls (also cut chained calls, above) |
| A function the agent clearly decided to call never appears in `functions_called` | the call was emitted as text, not as a tool call |

Check `chat_history[].metrics.llm_metadata.model_name` first, as `callkaro-agent-review-debug` describes: a fallback-model turn explains the behaviour on its own.
