---
name: callkaro-prompt-style
description: Plain-text house style for CallKaro agent prompts. Use when writing or converting agent prompts, removing markdown, cutting prompt token counts, adding pauses or SSML breaks, writing the custom begin message, or checking placeholders still resolve after a rewrite.
---

# CallKaro Prompt Style

Prompts are raw text handed to an LLM, not a document a browser renders. Markdown in a prompt is pure overhead: it costs tokens, teaches the model to echo formatting into spoken output, and tables/emojis have burned live calls. This is the plain-text house style proven on a production multi-prompt auction agent (converted from full markdown in one pass) plus the platform mechanics that go with it.

Docs: https://docs.callkaro.ai (Voice AI Agents). Companion: `callkaro-voice-agents` for modes, versions, functions.

## House style

Sentinels are the only markdown-looking thing allowed (they are section markers for humans and diffs, not formatting):

```
### BASE PROMPT START ###
### BASE PROMPT END ###
### CAPABILITY: start_capability START ###
### CAPABILITY: start_capability END ###
```

Sections and steps use banner blocks:

```
=========================================
SECTION 2: LANGUAGE CONFIG
=========================================

- plain bullets are fine
- -> for branch arrows, → also fine

STEP 3: CONTEXT SETTING
=========================================
```

Do NOT use any of these in prompts:

- `#` / `##` headings — banners instead
- `**bold**` — the words alone carry it
- backticked `code` — write it plain; keep placeholder braces intact (`{{var}}` stays `{{var}}`)
- tables `| a | b |` — one `key — value` line per row, drop separator rows
- `---` horizontal rules — blank line instead
- emojis (🔴 ⚠ ✅ 🚨) — replace with leading words: `CRITICAL:`, `IMPORTANT:`, `NOTE:`
- markdown numbered nesting beyond simple `1.` `2.` lists

Why, with numbers from the real conversion: stripping markdown, dead heading weight, and one out-of-scope capability took a shared base prompt from 9,787 to 2,486 tokens (cl100k, −75%). The platform docs also say it outright: no emojis or special characters in prompts — they break live calls.

Keep the docs' prompt rules while you are in there: one rule said once, literal instructions ("ask for the 6 digit pincode" not "handle location"), no maths in prompt (precompute and pass facts), and state when to do nothing.

## Spoken-output rules (the model copies your habits)

- Numbers as words, never numerals: "five lakh thirty thousand rupees". Never the ₹ symbol — say "rupees".
- No markdown, emojis, or special characters in anything meant to be spoken.

### Output contract block (highest-priority section, proven pattern)

Opening a base prompt with a hard output contract is the single most effective anti-narration defense. Two production shapes seen in the account (auto service, Payoneer), both placed before everything else and worded as "read before every reply":

```
§0 OUTPUT CONTRACT — READ BEFORE EVERY REPLY
Everything you output is spoken aloud on a live phone call. Therefore:
- Output ONLY the words the customer should hear. Nothing else.
- NEVER speak stage directions, labels, routing decisions, internal state names,
  function names, placeholders, or analysis.
```

```
# SPEECH-ONLY CUSTOMER-FACING OUTPUT
Generate only the final natural customer-facing response intended to be spoken.
Do not output analysis, reasoning, internal state names, labels, routing
decisions, simulation annotations, function calls, or backend data.
```

Related: the Omaxe real-estate agents open with a PRIORITY HIERARCHY block that resolves overlapping rules by explicit precedence (hard opt-out > pricing > primary flow). Use the same shape when rules genuinely conflict — a written precedence list beats hoping the model infers one.
- Language-specific quirks belong in Section-style language config (e.g. Hindi: always "रहाहूँ" with no space, names in Devanagari, Hinglish register).

## Pauses: SSML break tags

The platform TTS honors mid-response SSML. Reference pause table from production prompts:

- `<break time="0.2s"/>` between two short clauses
- `<break time="0.3s"/>` after a price, name, or specific data point
- `<break time="0.5s"/>` after a complete information block
- `<break time="0.7s"/>` after a high-impact statement
- `<emphasis level="moderate">text</emphasis>` (or `strong`) — max 1–2 per response

Rules: tags are mid-response only. NEVER end a response with a break or emphasis tag — the final sentence (especially a closing phrase) must be plain text. Custom longer breaks (e.g. `<break time="3s"/>`) work in the custom begin message; verify by ear on the first call, since only 0.2–0.7s is documented for model responses.

### Prosody tags (rate / pitch / volume), confirmed in production

Beyond `<emphasis>`, the platform honors full prosody spans. Real usage found in the account (Omaxe estate agents):

- `<prosody rate="85%" pitch="-20Hz" volume="soft">...` — wrap a whole sentence or a perspective shift to sound slower, lower, softer
- `<prosody rate="50%" pitch="-50Hz" volume="soft">hello—</prosody>` — an entire customMsg is just a prosody-wrapped fragment (a soft, drawn-out opener)
- One Omaxe rule: "wrap only the perspective in prosody; in that turn ask no question, offer no callback" — i.e. use prosody to mark an advisory aside, not to decorate everything

Use sparingly: 1 span per turn max, on the sentence that should carry the tone shift. Empirically prosody is more expressive than emphasis for Hindi, and the rate/pitch values are honored rather than spoken.

## Custom begin message (speakfirst)

Call initiation for outbound has three modes: user speaks first, AI dynamic begin message, AI custom begin message (+ initial delay seconds before it speaks).

- `speakfirst.customMsg` is a SEPARATE template from the system prompt. No pre-call function touches it. It supports `{{variable_name}}` substitution (the field's own hint says so), formatted via `variableSource` — that is where dynamic name transliteration happens (Latin "Tejas" → तेजस), so never hardcode names or maintain a static name table in functions.
- Gotcha, confirmed from a call timeline: after a custom message finishes, the model does NOT continue proactively — its first turn waits for customer speech. So the full automatic opening (intro line, pause, identity question) must live inside customMsg. The capability prompt's first turn should then be written as "handle the customer's REPLY to the opening", not "deliver the greeting".
- Example pattern: `Hello, मैं Aryan बोल रहाहूँ, Spinny से।<break time="3s"/>क्या मेरी बात {{lead_information_customer_name}} जी से हो रही है?`

## Placeholder wiring (check after every rewrite)

- `insert_metadata_in_prompt` is false on these agents: the platform will NOT auto-substitute prompt placeholders. Every `{{token}}` / `{token}` needs a writer (a pre-call function's replacements dict, or a dynamic `.replace(placeholder, ...)` loop).
- Two-layer naming: prompts reference short RESOLVED keys (`customer_name`, `active_price`, `step_2_context`); functions read raw NAMESPACED call-metadata keys (`lead_information_customer_name`, `car_metadata_atp`, `cep`). The dashboard Variables panel only shows the resolved layer — typing there cannot test raw-input branching.
- Style transforms must be placeholder-safe: strip backticks AROUND tokens, never strip the braces; keep `{{x}}` byte-identical.
- Before pushing any rewrite, run a wiring audit: extract every placeholder from base + all capability prompts, cross-check against what each function actually substitutes/writes, and fail on orphans. The classic live bug is a literal `{{customer_name}}` spoken aloud.
- Keep function-side name handling dynamic: extract the first name raw (skip Mr./Mrs./Shri prefixes, drop surname if the script wants first-name-only), let variableSource plus the prompt's language rule render the script. No curated name dictionaries.

## Portable de-markdown algorithm

Order matters; run it per prompt file, then verify idempotent (converting twice changes nothing):

1. Drop leading `# h1` title; ensure `### ... START/END ###` wrappers exist.
2. `## heading` → banner block (strip any emoji from the title first).
3. Tables: skip `|---|` separators; join cells of each row as `a — b`.
4. `**bold**` → inner text; backticks → inner text (braces untouched).
5. Emoji → leading `CRITICAL:` / `IMPORTANT:` / `NOTE:` word.
6. `---` → blank line; collapse 3+ blank lines to one.
7. Verify: zero `**`, `^#{1,2} `, `|`-rows, emoji left (sentinel `###` lines excepted); placeholders unchanged; token-count before/after; wiring audit green; unit tests green.

## Verify checklist

- Token count before vs after (tiktoken or any tokenizer site; cl100k and o200k both interesting — Devanagari-heavy prompts differ a lot between encodings).
- Placeholder audit exit code 0.
- One live or sim call: no spoken `{{`, no spoken `Step N:` system text, no emoji/SSML tag read aloud, opening fires without the customer speaking first.
