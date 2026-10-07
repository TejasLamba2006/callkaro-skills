---
name: callkaro-language-switching
description: Implicit language switching for multilingual CallKaro voice agents. Use when an agent must follow the caller's language (Hindi, English, Hinglish, Kannada, Tamil, Telugu, Malayalam), stays in the opening language, flips on "haan ji", speaks the English row on a Hindi turn, or when setting language_switching, language_switch_min_words, allowed_languages, transcriber languages, or end_call_msg rows. Gives the paste-in Section 0A, the config-agreement table, a 12-utterance test script and a failure-to-root-cause table.
---

# Language Switching: Implicit, Silent, Testable

The caller's language decides the agent's, with no menu and no announcement. This skill is the rule set that makes that testable, plus the config that must say the same thing as the prompt. Distilled from production multilingual agents.

Paste-in block: `TEMPLATE-A.md` (Section 0A, at the very top of the system prompt, above Section 1). Companions: `callkaro-conversational-agents` (Template B and the call-flow guideline), `callkaro-voice-agents` (field reference), `callkaro-conversational-voice` (why turns sound human).

## The mechanism in one screen

- **Trigger**: N or more words of another language in the latest customer message, counted AFTER setting aside loan words, names, numbers and fillers. N is a number, not a judgment word like "substantive", because a number can be checked in a test call.
- **Never triggers**: a reply shorter than N ("haan ji", "ok", "theek hai", "illa"), one foreign word, a name or place, a garbled turn. No clear signal means stay.
- **Memory**: latest message only, re-tested every turn, in any direction. Never decide from how the call began, from the agent's earlier turns, or from the prompt's own language (the prompt is English; that says nothing about the call).
- **Judge by how the sentence is built** (verbs, grammar, word order), not by its loan words. A Hindi sentence with English nouns is Hindi.
- **Explicit request** ("speak Hindi") switches at once; the test keeps running afterwards. "I don't understand": ask once, in very simple words, which supported language. Unsupported language: say once which ones you speak.
- **Silent**: never announce, ask permission, or apologise. Same step, other language.
- **Reply shape**: one language per reply, own script, never romanised, everyday spoken register, composed natively (never translated from English). Mix back what the customer mixes. Loan words stay in Latin letters inside non-English sentences. Names are written in the reply's script.
- **Lines in the prompt**: a row-per-language line means say the row for this turn (the English row has no priority; saying it on a non-English turn is the most common way a call slips out of the caller's language). A single-language line means say the same meaning natively. A verbatim line (closing, disclosure) is copied exactly, in the language of the turn it ends; never switch language just to reach one.

## Config must agree with the prompt

The prompt writes the words; these fields carry the mechanical half.

| Field | Set to | Why |
|---|---|---|
| `language_switching` | true | switches transcriber and voice when the transcript changes language |
| `language_switch_min_words` | the same N as Section 0A.1 | prompt and platform detector otherwise disagree |
| `allowed_languages` | the supported languages in 0A.1 | limits what the backend may switch into; empty on a multilingual agent is a miss |
| Transcriber languages | every supported language | a language the transcriber lacks is misheard, so the test fails |
| `default_language`, `default_agent_language` | the opening language | platform speaks the first line in it |
| `speakfirst.customMsg` | a line in the opening language | nothing else decides the first sentence |
| `silence_language` | `multi` when more than one language | silence prompts follow the call, not the default |
| `end_call_msg` | every closing line, in every language it can be spoken | the call only ends on an exact match |
| Voices | one per language, same persona gender | gender holds across switches |
| `language_switch_snippet` | optional copy of the rule | a deliberate second placement, only to fix a miss seen in a test call; never contradicts 0A |

Pairs with `callkaro-conversational-voice` section 6: never list a language in the transcriber whose script Hindi speech can land in (a `pa` entry turned Hindi into Gurmukhi); the platform note "Conversation language changed, so reply in X" means the test has already passed; an explicit request outranks that note.

Mismatches found auditing live agents: prompt says N=4 while `language_switch_min_words` is 3; `allowed_languages` empty while the prompt speaks six languages; a language in the prompt missing from the transcriber list; a voice id for one language labelled with another language's code; `language_switch_snippet` empty while the rules live only in the body. Export the agent (`callkaro-cli`) and audit these before touching wording.

Team rules for the flags: keep `language_switching: true` (platform docs call it legacy, but the backend runs the current implementation behind it), leave `language_lockin_time` unset and `language_switching_v1` false, and leave `language_switching_instructions` null unless you need custom behaviour. `switchableLanguages` is a different feature: it hands the call to another published version.

## Choosing N

Default 4. 3 is acceptable. The number must equal `language_switch_min_words` exactly. Lower N flips on filler phrases ("haan ji bolo"); higher N makes the agent slow to follow a real switch.

## Test before going live

Open the call in English with English + Hindi and N = 4. Listen to the voice too: text and accent should change in the same sentence.

| # | Customer says | Expected |
|---|---|---|
| 1 | "Yes, go ahead." | stays English |
| 2 | "haan ji bolo" | stays English (3 words) |
| 3 | "haan mujhe service book karni hai next week" | Hindi from the next sentence, silently |
| 4 | "ok" / "theek hai" after 3 | stays Hindi |
| 5 | "Can you tell me the price for that service?" after 3 | back to English, silently |
| 6 | "Please speak in Hindi" | Hindi at once |
| 7 | "Please book it for kal subah" | stays English (1 word) |
| 8 | garbled turn or "hmm" | no switch |
| 9 | place name in Devanagari inside an English sentence | no switch |
| 10 | "Can you speak Tamil?" (unsupported) | says once which languages, carries on |
| 11 | "I do not understand" | asks once, simple words, preferred language |
| 12 | call ends right after a Hindi turn | closing line in Hindi, or the exact single form if only one exists |

Then run about ten real calls.

## When a call goes wrong

Find the rule that caused it before adding a NEVER line.

| Symptom | Likely cause | Root fix |
|---|---|---|
| Stays English on a Hindi turn | English row treated as default; N differs from config; transcriber lacks the language | 0A.8 wording; align N; add the language |
| Flips on "haan ji" | short-reply rule missing, or `language_switch_min_words` below N | align the two numbers |
| Hinglish judged as English | judged by loan words, not sentence build | keep 0A.3 "judge the language the sentence is built in" |
| Replies in Hindi when the turn was Kannada | went by call history, not script | 0A.5 "go by the script and words in front of you" |
| Mixed-language reply, romanised text | 0A.7 missing | one language, own script |
| "Shall we continue in Tamil?" | 0A.6 missing | switch silently |
| Gender slips after a switch | persona gender not declared once, or slash forms used | declare once in Role; ordinary forms where the language does not mark gender |
| Call never ends after a Hindi turn | closing line paraphrased or missing from `end_call_msg` | verbatim rows for every language in `end_call_msg` |
| Call opens in the wrong language | `default_language`, `speakfirst.customMsg` and voice disagree | align the three |

A second miss of the same rule needs a structural fix (config, snippet placement, a row per language), not louder wording.
