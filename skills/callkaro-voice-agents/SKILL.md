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

## Transcriber

- Deepgram: best English accuracy, keywords support.
- Groq: fastest.
- Sarvam: best Hindi and Hinglish, 12 Indian languages.
- Azure: enterprise grade, Indian language coverage.
- ElevenLabs: pairs with ElevenLabs voice.
- Soniox: fine tune via UI, multi language, context and translation terms.

Add brand names and short forms as Keywords so they transcribe right.

## Versions and A/B tests

One agent, many versions (language, city, goal). Run standard split by percent, or advanced rules on `metadata`:

```
(metadata.city == 'Delhi')
((metadata.age >= 25) AND (metadata.plan == 'enterprise'))
```

Rules run top down, first match wins. Text compare is case insensitive. Missing metadata matches `!=` but not `==`. A rule returns a Version directly, or a Language (then standard split, published version, default config in that order). Splits inside a rule must total 100.

## Functions

- Pre-call: fetch data before dialing.
- In-call: bookTestDrive, check slots (cal.com needs API key plus Event Id), send WhatsApp mid call, EMI math, hold (`keep_call_on_hold`), transfer (`transfer_call`, cold vs warm), end call. Say what the agent should tell the caller while the action runs.
- Post-call: save outcomes, update CRM.

Custom functions come in Basic (one API hit) and Advanced (full logic). Auth via `x_secrets` reference.

## Knowledge bases

Attach large reference material that will not fit in the prompt. Add a Say While Executing line such as "Ek min sir, abhi dekh kar batata hu" so the caller hears something during lookup.

## Post-call variables

Extract Customer Name, Email, Interested Product, Appointment Date. Types: Text, Selector (fixed list), Boolean, Number. Set Conversion Reason (example: Demo Booked) and Call Drop-off Reasons. Use different strategy models per call length segment, skip analysis for very short calls.

## Key configs

Call initiation: user speaks first, agent natural, or agent with custom message plus initial delay. Call termination: custom closing message ends the call. Call settings: Indian number format, auto reschedule, followup, background noise plus volume, noise cancellation (use Callkaro strategy, strength 1.00 to start), voicemail dynamic or custom, time limit, disconnect timeout. TTS caching: full response (lowest latency), sentence level (balance), none (flexible). Silence, endpointing, interruption, preemptive synthesis, language switching per docs.
