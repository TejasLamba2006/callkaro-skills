---
name: callkaro-voice-agents
description: Build and tune CallKaro voice agents. Use when creating agents, writing prompts, picking LLM voice transcriber, versions, A/B tests, functions, secrets, knowledge bases, post-call variables.
---

# CallKaro Voice Agents

An agent is an AI voice caller. It starts conversations, answers questions, takes actions, ends calls, then updates the CRM.

Docs: https://docs.callkaro.ai/ (Guides section, Voice AI Agents)

## Setup modes

System prompt plus pre-call variables (name, email, address). Three ways to write it:

- Basic: single prompt, small use cases
- Advanced: structured sections, most production agents
- Multi-Prompt / Capability mode: split skills per capability
- Pathway (Mode 4): visual node flow with conditions and actions

Pick Basic for prototypes, Advanced for real work, Pathway when the flow has strict branches (lead qual, collections, support triage).

## Good prompt rules (from docs)

- One rule said once. Number every rule (A, A.1) so you can point to it.
- Literal instructions: "ask for the 6 digit pincode", not "handle location".
- No arrows, no maths in prompt. Precompute dates and pass as facts.
- State when to do nothing, or the agent invents an action.
- Cover every path: interested, not interested, callback, buy, end call.
- Test with real cases after writing.

Store keys and tokens in Dashboard Settings Secrets as `x_secrets.NAME`. Never paste credential values in prompts or chats.

## LLM

Recommended: `callkaro/arjuna-2.5` for realtime voice. Temperature 0 to 1, higher is more creative. Set a Secondary LLM as failover, caller never notices the switch.

Post-call extraction recommended model: `callkaro/krishna-2.5`.

## Voice

- ElevenLabs (~Rs 6): best for Hindi, English, Tamil. Supports Breaktime pauses.
- Cartesia (~Rs 4): best for other languages. Breaktime works.
- Sarvam (~Rs 4): all languages, Breaktime lags.
- Azure (~Rs 2): budget bots.

Tune speed, stability, similarity boost, style per provider. No emojis or special chars in prompts, they break live calls.

**Always set `secondary_voice_configuration` from a DIFFERENT provider** (Sarvam `bulbul:v3` is the standard partner), so a single provider outage can't take both voices down — the same reasoning as the LLM primary/secondary pair. Realtime LLM models (`*realtime*`) force `voice_provider: "Open AI"`.

**Default voice gender when the script doesn't state one:** masculine for `hi en kn gu ml`, feminine for `mr ta te bn`. And match whatever persona gender the prompt declares — Hindi verb conjugation drifts if the voice and the stated gender disagree.

## Transcriber

- Deepgram: best English accuracy, keywords support.
- Groq: fastest.
- Sarvam: best Hindi and Hinglish, 12 Indian languages.
- Azure: enterprise grade, Indian language coverage.
- ElevenLabs: pairs with ElevenLabs voice.
- Soniox: fine tune via UI, multi language, context and translation terms.

Add brand names and short forms as Keywords so they transcribe right.

**Structured context beats keyword blobs (observed across ~30 production agents).** Soniox accepts `transcriber_general_context` (key/value pairs) and `transcriber_text_context` (free prose), separate from `keywords`. Real usage in the account:

```
transcriber_general_context: [
  {"key": "role", "value": "Female outbound debt-reminder representative for parsaar.co"},
  {"key": "call_purpose", "value": "Verify customer identity before giving any factual payment reminder"},
  {"key": "expected_languages", "value": "Hindi, Hinglish"}
]
transcriber_text_context: "Lokal Matrimony Hindi/Hinglish verification calls. Capture ages,
  years, dates, and heights as digits. Do not drop year digits."
```

Context says what kind of call this is and which forms matter; keywords are only for proper nouns and short forms ("Omaxe Estate", "Chandni Chowk", brand names, model names). Guidelines on keyword count vary by provider — keep the list short, put the rest in context.

**Provider/language shapes seen in production** (from a 301-agent account survey): Soniox with `["hi"]`, `["en","hi"]`, or `["hi","en"]`; Azure with `["hi-IN"]` or `["en-IN"]`; Deepgram `nova-3` with `hi` and language detection on/off; Sarvam `saaras:v4` with `hi-IN`. Deepgram is the most common choice for English-dominant agents, Soniox for Hindi-first ones.

### Never invent catalogue values — discover them

The official CallKaro skills repo (Mail-Daddy-AI/callkaro-skills) is emphatic about this and it matters: a remembered voice id goes stale or belongs to a different provider. Discover from the CLI:

```bash
ck voices --providers                          # every provider + models
ck voices --provider cartesia --fields         # only the keys that provider takes
ck voices --provider sarvam --model bulbul:v3 --language hi-IN --gender female
ck transcribers                                # every provider/model + languages
ck transcribers --provider gnani --fields
```

`--fields` is the fastest way to write a correct config: it prints only the keys that provider actually uses, so you never write one it ignores.

Providers that exist but rarely show up in exports: **Gnani** (`en-IN,hi-IN`), **Speechify** (locale-scoped — requires `--language`), **Murf**, Deepgram, OpenAI. Don't conclude a provider doesn't exist because no sampled agent uses it.

### The three-language consistency rule

`default_agent_language`, `voice_configuration.voice_language`, and `transcriber.transcriber_language` must tell the same story, each in **its own provider's format** — never reshape `"hi"` ↔ `"hi-IN"` ↔ `["hi-IN"]` between them. Mismatches produce an agent that speaks one language and transcribes another, which looks like a model problem and isn't. If `language_switching` is on, the transcriber must cover every language in `switchableLanguages`, which means an array-language provider (Soniox or Azure).

## Versions and A/B tests

One agent, many versions (language, city, goal). Run standard split by percent, or advanced rules on `metadata`:

```
(metadata.city == 'Delhi')
((metadata.age >= 25) AND (metadata.plan == 'enterprise'))
```

Rules run top down, first match wins. Text compare is case insensitive. Missing metadata matches `!=` but not `==`. A rule returns a Version directly, or a Language (then standard split, published version, default config in that order). Splits inside a rule must total 100.

**Always end the rule chain with a trailing `else`.** City/state rules are string equality on whatever key the CRM sends (`lead_information_city` in the Spinny account). Without a final else, leads whose city key is missing or spelled differently fall through to whatever the platform default is — not necessarily your base version. Missing metadata matches `!=` but never `==`, so an equality-based chain silently drops those leads.

**City-list maintenance is manual and drifts.** In the 301-agent account survey, exactly one agent family had geography rules (2 branches: 7 Punjab cities, Delhi NCR) while six other language versions had none — routing for those came from per-row `x_language` on batch CSVs instead. Plan for both: batch `x_language` when the upstream system knows the language, advanced A/B rules for city-driven accents, and a trailing else so nothing is unrouted.

## Functions

- Pre-call: fetch data before dialing.
- In-call: bookTestDrive, check slots (cal.com needs API key plus Event Id), send WhatsApp mid call, EMI math, hold (`keep_call_on_hold`), transfer (`transfer_call`, cold vs warm), end call. Say what the agent should tell the caller while the action runs.
- Post-call: save outcomes, update CRM.

Custom functions come in Basic (one API hit) and Advanced (full logic). Auth via `x_secrets` reference.

### Function types: the full set

Beyond pre-call / in-call / post-call, the platform has **`on_connected`** — a function that runs automatically once after the call connects (or once on entering its capability/node), for side effects the model shouldn't have to remember to trigger. Top-level copy runs at connect; a capability- or node-scoped copy runs on entry. It takes Python `async source_code` like the other advanced functions.

Pattern worth knowing: things you'd otherwise write as "LLM must call this immediately after X" (marking a cohort delivered, recording a state transition, firing a webhook on a specific milestone) are often better as `on_connected` or a deterministic pre-call, because the LLM is the least reliable party in the loop.

### What the account actually uses (301-agent survey, 27 agents deep-exported)

Function type frequency: `custom_post_call` 20, `custom_pre_call` 19, `custom_in_call` 15, `end` 11 (+7 capability-scoped), `transfer` 6, `keep_call_on_hold` 3, plus WhatsApp-specific types (`whatsapp_post_call`, `send_to_whatsapp`).

Recurring in-call function names across unrelated businesses — these are the patterns worth copying: `end_call` (by far the most common, 18 uses), `transfer_call` / `transfer_to_human_support`, `verify_otp`, `confirm_pincode` / `update_pincode`, `calculate_hold_deduction`, `submit_verification_outcome`, and a family of `route_*` functions (`route_escalation_safety`, `route_escalation_security`, `route_dnd_delete_request`, `route_duplicate_profile`, `route_fake_suspected`, `route_profile_correction`).

The `route_*` shape is worth stealing for any agent with compliance or QA branching: one small deterministic function per branch condition, each returning a decision the prompt then acts on. It keeps judgment in code and out of the model's improvisation, and it is auditable per branch — exactly like the pattern used to make OCB eligibility deterministic instead of asking the LLM to do the math.

Where negotiation-style agents converge: `calculate_next_negotiation_price` is the standard name for the one-and-only price-increase function, always paired with a `mark_*_delivered` bookkeeping function so the model can never invent a second price step.

## Knowledge bases

Attach large reference material that will not fit in the prompt. Add a Say While Executing line such as "Ek min sir, abhi dekh kar batata hu" so the caller hears something during lookup.

## Post-call variables

Extract Customer Name, Email, Interested Product, Appointment Date. Types: Text, Selector (fixed list), Boolean, Number. Set Conversion Reason (example: Demo Booked) and Call Drop-off Reasons. Use different strategy models per call length segment, skip analysis for very short calls.

**Breadth varies enormously by agent purpose** (301-agent survey): 0–5 vars for reminder/notification bots, 11–19 for support and sales qualifiers, 25–40 for negotiation agents, and 96 on one heavy matrimony verification agent doing profile QC. Match the list to what the business actually reports on — a 40-var negotiation agent and a 5-var reminder bot are both correct, for different reasons. Anything at 0 means the agent reports nothing, which is only right for pure fire-and-forget notifications.

## Key configs

Call initiation: user speaks first, agent natural, or agent with custom message plus initial delay. Call termination: custom closing message ends the call. Call settings: Indian number format, auto reschedule, followup, background noise plus volume, noise cancellation (use Callkaro strategy, strength 1.00 to start), voicemail dynamic or custom, time limit, disconnect timeout. TTS caching: full response (lowest latency), sentence level (balance), none (flexible). Silence, endpointing, interruption, preemptive synthesis, language switching per docs.

### Time limit is a design input, not a default

`time_limit` (seconds) in the 301-agent account ranged from 180s (a one-shot opener) to 10000s (a long dealer-negotiation bot), with most qualifiers landing 300–900s. Set it from your script length, not from a template: a 5-minute call does not need 1500s of headroom, and a long negotiation bot that inherits 300s gets cut off mid-flow. Size it as (longest realistic path × turns per beat) with slack, and note that `switch_capability` chains (start → negotiation → ocb → end) each continue the same clock.

### Silence settings: three knobs, not one

- `silence_wait` (seconds before a silence prompt fires) — most agents in the account run 4–8s; long negotiation bots sit at 6–8s
- `silence_count` (how many consecutive silent gaps before prompting) — 2 is the common floor, 3–5 for patient/browsing flows
- `silence_mode` — `custom` (your own `silence_prompts`) vs `dynamic` (platform free-generates an unscripted line) vs `ignore`

Prefer `custom` with two fixed, on-brand lines. `dynamic` generates plausible-sounding but off-script filler that lands before your real greeting and reads as a double opener — this is a real, confirmed production failure mode. Also remember the related contentless-input trap: a bare "haan"/silence is not a yes, so silence_count and the prompt text must agree with your "re-ask once, then advance" rules.

### TTS caching strategy, by call shape

`caching_strategy` in the account split by flow length: `response` (cache the whole LLM response) dominated long negotiation and qualification agents, `sentence` appeared on mid-length reminder flows, `none` on short/opener-heavy or highly dynamic agents. Full-response caching is lowest latency but wrong when the same prompt text can resolve to different spoken content (any prompt that embeds a changing price or variable).

## Live lessons (OTP verification agent, Sept 2026)

Proven on live calls, not just sims:

- Dashboard Test Call dialog builds its variable fields from `{{vars}}` in prompt text only. Every metadata key the agent needs at test time must appear literally in the prompt, even if only a function reads it. Removing `{{OTP}}` from wording silently drops the OTP input.
- Function-first for digit compare. Read-back confirm, length judging, match judging all broke in the model and all worked first try in code. Script the ask line with exact quotable wording ("The 6 digit SMS code was sent..."), name the real cases (4 vs 6 digit), and ban the vague form. Abstract instructions ("say N digit") get paraphrased into mush.
- Bare "hello"/"hi"/silence is not a yes. Any flow that advances on confirmation must define contentless input: re-ask the SAME question once, then close. Tune `silence_count`, `silence_wait`, endpointing delay, and `interrupt_min_words` so pauses stop counting as answers.
- Refusal closes are speak-then-end. "End immediately" gets silent hangups. Template: exact closing line first, then `end_call`, in that order, always.
- Check Pre Format Variables on every version. DigitByDigit only for digit fields, passthrough for names. One stale Custom rule spelled every plain name letter by letter.
- **Pre Format Variables (`preFormatVariables` / `variableSource`) format `{{vars}}` in prompt text only, never inside function code.** A pre-call function that reads `metadata["lead_information_customer_name"]` gets the raw Latin value even with `Latin:Devanagari` set, so a greeting it builds says "NITHIN जी" instead of "नितिन जी". Format inside the function with the platform helper, and keep any detection (company tokens etc.) on the raw value:
  ```python
  from utils.format_utils import latin_to_devanagari   # import inside the function body
  spoken_name = latin_to_devanagari(first_name) or first_name
  ```
  Wrap it in try/except so a missing helper falls back to the Latin name instead of failing the call (a pre-call exception = `PRE_CALL_FN_FAILED`). Keep the preformat entries too: they still cover every `{{var}}` the prompt reads directly. Diagnose from the call log: the pre-call's own log line shows the name it actually saw.
- Custom in-call functions cannot see call metadata via `ctx` on this platform (proven over live calls). Expected values must arrive as function args. Normalize both sides of any digit compare: the platform delivers codes as words ("four eight two...") through DigitByDigit preformat, so raw digit-strip turns them into empty string. Reference pattern: word-plus-range normalizer handling digits, number words, doubles/triples, and ranges ("1 to 6", "start from 1 ended at 6").
- Partial digit input ("123" then "456") must stitch across turns in `userdata`, not fail. Fresh full-length input replaces the buffer (re-read, not continuation). Short input appends without burning an attempt.

## Live lessons (auction negotiation agent, multi-prompt, Sept 2026)

From building and live-testing a capability-mode agent over ~10 test calls. Read the whole call log before diagnosing — the timeline answers questions the transcript cannot:

- **A custom begin message does not hand off to the model.** With speakfirst customMsg, the platform speaks that text, then the model waits for customer speech before its first turn. If the opening is supposed to be a sequence (intro, pause, identity question), all of it belongs inside customMsg — the capability prompt's first turn must be written as "handle the customer's reply to the opening".
- **Injected variables must be re-exercised per capability.** Because the base prompt merges into every capability at runtime, each capability's pre-call functions run on entry; a function that reads state another function writes can see stale or missing values depending on which capability fired last. Log the key facts per function and check the real runtime prompt, not the source, when a value looks wrong on a live call.
- **Scripted "ask the customer X" questions need a "already answered? never ask again" clause.** A literal line in a prompt ("Then ask where the price came from") gets spoken on every entry to that branch, including after the customer already answered. The source question became a loop on a real call; the fix was an explicit once-per-call cap plus a branch for "the source was our own prior quote".
- **Check `chat_history[].metrics.llm_metadata.model_name` before trusting any transcript.** A platform-wide degraded-mode event sent multiple agents to livekit's generic `FallbackAdapter` even though the agent was correctly configured for arjuna-2.5 — off-script phrasing, missed tool calls, restarted sentences, and a leaked control token all traced back to that, not to prompt bugs. Discard fallback-tainted calls before drawing conclusions.
- **"Never calculate yourself, call the function" is not enough for pricing steps.** A one-call-per-call guard plus a re-entrancy guard worked, but the model still looped a "would you reconsider?" push line instead of routing onward. Scripts need explicit advance-and-exit conditions, not only prohibitions.
- **End the call through the end capability, not by speaking a closing phrase from wherever you are.** On a real call the closing phrase came directly from the negotiation capability with no end-capability switch, skipping the callback and wrap-up steps that lived in the end checklist. State the switch explicitly wherever a refusal or "call me later" appears in any capability.
