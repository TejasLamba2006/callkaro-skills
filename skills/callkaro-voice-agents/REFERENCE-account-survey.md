---
name: callkaro-voice-agents
description: Reference data mined from a 301-agent CallKaro account (Sept 2026) — what production agents actually configure, with numbers. Consult when choosing voice/transcriber/model/time-limit/silence values, or sanity-checking a config against real practice.
---

# Account survey reference (301 agents, Sept 2026)

Mined read-only from one CallKaro account via `ck agents list --json` plus deep `ck agents export` of 27 agents across 14 business families (OTP, auction/negotiation, matrimony, auto, health, finance, real estate, education, support, sales, notification, ecommerce, other). No agent was modified. Numbers are what production agents in this account actually use — useful as a sanity check, not as gospel.

## Architecture spread

Prompt types across sampled versions: type 0 (Basic/single) 40, type 1 (Advanced) 6, type 2 (Multi-Prompt) 5, type 3 (Pathway) 4. The account is mostly Basic agents; the multi-prompt agents are the auction/negotiation family.

## Voice

- ElevenLabs `eleven_flash_v2_5`: dominant (21 of 26) — `hi` for most, `en` for several
- ElevenLabs `eleven_v3_conversational`: 4 agents, all `hi`
- Sarvam `bulbul:v3` (hi-IN): 1 agent
- No Cartesia or Azure voices in this account's sample, though both are supported platform-wide

## Transcriber

- Soniox is the default for Hindi-first and mixed agents: `["hi"]`, `["en","hi"]`, or `["hi","en"]`
- Azure for inbound enterprise support: `["hi-IN"]`, `["en-IN"]`
- Deepgram `nova-3` / `nova-3-general` for English-dominant agents
- Sarvam `saaras:v4` (hi-IN) for a couple of agents
- `useMultiTranscribers` true on only 1 of 27 — single-transcriber setups dominate

Structured context (`transcriber_general_context` key/values, `transcriber_text_context` prose) is the common pattern; keywords are used sparingly and only for proper nouns (brand, project, locality names).

## LLM

- `callkaro/arjuna-2.5` is the dominant primary across capabilities (30 of 36 capability configs)
- Secondary models vary widely: `gpt-4.1-nano` (most common, 22), `gemini-2.5-flash-lite` (5), `gemini-3.5-flash-lite` (3), `gpt-5.4-mini`, `gemini-3.1-flash-lite`
- A handful of older agents still run `gpt-4.1` / `gpt-4.1-mini` / `gpt-5-mini` as primary

## Call initiation (speakfirst)

- `value=1` (dynamic begin message) with no custom text: 15 of 26 — the platform default
- `value=2` (custom begin message) with text: 6 agents, `message_interruption: true` on most
- Custom messages are full openers with `{{variable}}` substitution, e.g. `"नमस्ते, मैं Auto power Motors की service team से Alia बोल रही हूँ। क्या मेरी बात {{customer_name}} जी से हो रही है?"`
- One agent uses a prosody-wrapped fragment as its entire custom message: `<prosody rate="50%" pitch="-50Hz" volume="soft">hello—</prosody>`

## Silence and termination

- `silence_wait`: 4s, 6s, or 8s (6s most common)
- `silence_count`: 2 (most), 3, or 5
- `silence_mode`: `default` (most), `custom` (fixed prompts), `dynamic` (platform-generated), `ignore`
- **Zero agents in the sample used a custom termination/end-call message** — every one relies on the prompt's closing phrase

## Time limit

Ranges 180s to 10000s: 300s (short reminders/OTP), 400–900s (qualifiers, support, negotiation), 1500–3600s (long negotiation bots). Set from script length, not template.

## TTS caching

- `response` (full-response cache): most negotiation and qualification agents
- `sentence`: mid-length reminder flows
- `none`: short openers, highly dynamic agents, WhatsApp agents

## Language machinery

- `language_switching: true` on 4 of 27, with no `switchableLanguages` configured on most
- `advancedAbTestEnabled` true on only one agent family (the auction bot) with 2 city rules
- No agent in the sample used `switchableLanguages` with actual entries — mid-call language transfer is rarer than the docs suggest

## Functions

Type frequency: `custom_post_call` 20, `custom_pre_call` 19, `custom_in_call` 15, `end` 11, `transfer` 6, `keep_call_on_hold` 3, WhatsApp types 2.

Recurring names: `end_call` (18 uses), `transfer_call` (4), `verify_otp`, `confirm_pincode`, `calculate_hold_deduction`, `submit_verification_outcome`, and a `route_*` family (`route_escalation_safety`, `route_escalation_security`, `route_dnd_delete_request`, `route_duplicate_profile`, `route_fake_suspected`, `route_profile_correction`).

## Post-call variables

0 (reminder bots) to 96 (one matrimony QC agent). Typical: 11–19 for support/qualifier, 25–40 for negotiation.

## Prompt hygiene

Most agents' prompts are markdown-free already (0 bold, 0 headings) — the house style in `callkaro-prompt-style` is not unusual. A few outliers still carry `#`/`##` headings or bold. Placeholder counts vary 0–81 depending on how much of the prompt is parameterized.

## Structural prompt patterns worth copying

- **Output contract up top** ("everything you output is spoken aloud; output only the customer's words; never speak labels or routing") — seen in the auto-service and Payoneer agents, placed before all other sections
- **Priority hierarchy block** — the Omaxe agents open with an explicit precedence list (hard opt-out > pricing > primary flow) to resolve rule conflicts deterministically
- **Persona gender + verb conjugation pinned** — several agents state "persona gender: female, use consistently feminine Hindi forms in every spoken response," which prevents gender drift in Hindi morphology
- **No-thought-tags guard** — one agent explicitly bans `<thought>` and internal reasoning tags in output
