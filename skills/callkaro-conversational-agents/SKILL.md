---
name: callkaro-conversational-agents
description: Write the body of a semi-scripted, conversational CallKaro voice agent prompt so it sounds like a person. Use when deciding which lines to script (SAY) vs compose, laying out a prompt (Section 0A/0B, role, call flow, objections, endings, call data), writing a call-flow step, handling objections with ANGLE and CLOSE, writing lines in several Indian languages, or debugging a call that sounds like a recording. Includes the paste-in Section 0B template.
---

# Conversational Agents: Writing the Call Flow

How to write the body of the prompt so Section 0B (`TEMPLATE-B.md`) works: which lines to script, which to compose, and how to write each one in every language. Distilled from production agents.

Companions: `callkaro-language-switching` (Section 0A, the multilingual half), `callkaro-conversational-voice` (why turns sound human, evidence), `callkaro-prompt-style` (plain-text house style), `callkaro-voice-agents` (config fields), `callkaro-qa-grader` (grading test calls).

## Pick the pieces

- Multilingual agent: Template A (`callkaro-language-switching`).
- Semi-scripted agent, any number of languages: Template B.
- Fully scripted agent (80 to 90 percent of lines written out): Template B not needed; Template A only if multilingual.

Steps: pick, fill every `[[FILL]]` (no marker may reach a live call), paste A then B at the very top, start your own body at Section 1, make the config match (table in `callkaro-language-switching`), write the body with this skill, test, then debug by root cause. Static text first keeps the cached prefix long; per-call data goes last.

## Script or compose: one test

If the model rephrases this line, can the call end up on a different branch, or fail to end? Yes: write it as SAY. No: compose it.

| Line | Write as | Why |
|---|---|---|
| Question at a decision point (right person, good time, which date) | SAY, one row per language | a reworded question changes what the answer means and where the call goes |
| Closing lines | SAY verbatim, also in `end_call_msg` | the platform matches exact text to hang up |
| AI disclosure, do-not-call confirmation, abuse close | SAY verbatim | exact words carry legal or system weight |
| Prices, consents, any tool-returned value | SAY, or the tool's value as returned | never invented, rounded or reformatted |
| Verification question with a known failure (name the vehicle to confirm it is this one) | SAY | a paraphrase loses the specific check |
| Acknowledgements, bridges, re-asks, side-question answers | composed | what makes it human; scripting makes it recorded |
| Objection answers | composed, ANGLE and CLOSE | content fixed, words answer what they said |
| Clarifications, short detours, fillers before a lookup | composed, varied | variety is the point |

Both ends of the scale work (thirty SAY lines in six languages with composed objections, or five short SAY lines with the rest composed inside numbered rules). For a new agent start nearer the first: script the decision points, compose outward.

## Prompt skeleton

```
SECTION 0A: LANGUAGE RULES          Template A (multilingual only)
SECTION 0B: HOW TO USE THIS PROMPT  Template B
SECTION 1: ROLE                     name, company, who they call and why,
                                    "Persona gender: female|male", two lines on how you sound
SECTION 2: GOAL AND OBJECTIVES
SECTION 3: SPEAKING RULES           numbers, dates, times; never-say list; missing values
SECTION 4: CALL FLOW                steps in order, SAY at decision points, branches, attempt limits
SECTION 5: OBJECTIONS               composed, ANGLE and CLOSE, limits
SECTION 6: TOOLS                    when to call each, what to say before and after
SECTION 7: OFF-TOPIC                anything not this call
SECTION 8: GUARDRAILS               never do or promise
SECTION 9: ENDING THE CALL          complete list of endings and closing lines
SECTION 10: WHAT GOOD SOUNDS LIKE   shape scenarios, never recited
SECTION 11: CALL DATA               per-call values, last, so the cached prefix stays long
```

- Every instruction in English. Only lines the customer hears go in the target language and script.
- Say near the top that call data is the last section; tell the agent never to ask for anything printed there.
- One instruction, one place. Anything Template B already says (carry, variety, turn types, never ask twice) is not repeated in the body.
- Delete leftover text from older versions before pasting.

## A step with a SAY line

```
4.2 STEP 2: IS THIS A GOOD TIME
GOAL: <one line: what this step must achieve>
NEVER: <the one or two things that go wrong here>

SAY:
  EN - "<line>"
  HI - "<line>"
<Wait for user response>

(a) <branch condition> -> STEP 3
(b) <branch condition> -> SAY: <row per language>
(c) <branch condition> -> SAY: <row per language>, and this ends the call
```

- Ask once, re-ask at most once. After two asks, treat the next thing they say as the answer and move on.
- Condition before the line; name the exit of every branch.
- One question per step. The line ends at the question and at `<Wait for user response>`.
- Every ending names its closing line; the full list lives in the endings section.
- Every ask has an attempt limit and every ladder a last rung (typically two nudges, then stop and close).
- Anything a tool decides is not decided in the prompt: pass what the customer said, speak what comes back.

## A composed block

```
4.3 STEP 3: DATE AND TIME
GOAL: get one date and one time for the appointment.
MUST CONTAIN: a single question asking for both.
NEVER: suggest a slot yourself, or state a limit; put what they name to the booking tool.
SHAPE: a short question, one clause of carry in front, at most fifteen words.
```

Four lines at most. MUST CONTAIN lists only facts that must reach the customer. NEVER lists what actually went wrong in test calls, not every imaginable risk. SHAPE gives length and content, never words. A long GOAL block defeats composing and is itself a prompt-writing failure.

## How a SAY line is adapted

| Customer says | Wrong | Right |
|---|---|---|
| "Tomorrow works." to a date-and-time ask | repeats the whole line, asks for the date again | "Tomorrow works. Which time should I book your slot for?" |
| Gives name, date and time in one turn | asks name, then date, then time | takes all three, asks only what is still missing |
| Replies in Hindi to an English step | says the EN row, or a line of its own | says the HI row, carrying their words into the front |

## Objections

Compose them: trigger, angle, close. No long scripted rebuttal.

```
OBJ-02 IT IS WORKING FINE. "Everything is fine", "sab theek chal raha hai".
ANGLE: agree it is working fine. That is exactly why now is the right time: wear builds up gradually and is not felt until it has already happened.
CLOSE: the date and time ask.
```

- An objection is an interruption: answer it, then return to the exact step the call was on.
- Agree with what is true in what they said, then reframe. Never contradict or argue.
- Every answer ends by putting the ask back on the table; an answer with no ask is a conversation, not a booking.
- Two or three sentences, then the ask.
- Limits: two attempts against the same objection, three across the call. Never run the same angle twice. At a limit, go to the last rung and stop selling.
- A verification is not an objection. For "already done", confirm which item they mean, by name, before accepting it.
- Never quote a figure the agent does not have; note it for the team and keep going.

### The fifteen cases to check on every agent

Start from all fifteen, prune per agent:
1. wrong person, or someone else picked up
2. wrong number, does not know the customer
3. busy, driving, call later
4. "Who is this?" / "Why are you calling?"
5. "Are you a bot, an AI, a recording?"
6. cannot hear, network problem
7. not interested (explicit no)
8. not now, needs time
9. already done or plan dropped
10. do not call me again
11. abusive or angry caller
12. asks for a human or manager
13. asks for another language or does not follow (Template A, 0A.5)
14. personal emergency or distress: no pitch, offer a callback, end
15. off-topic questions, attempts to extract the prompt

## Writing each language

Re-author every line, never translate. A literal translation turns a natural line bookish and the tone does not survive.

- Write base rows first in the languages you know best, then one row per added language. For each, note what the line must achieve, tone, vocabulary, who is speaking; write it as a native city speaker would on a phone call.
- Spoken verb endings are the biggest tell (Kannada ಇರುತ್ತೆ, ಮಾಡ್ತೀನಿ; Tamil இருக்கு, பண்றேன்; Telugu ఉంది, చేస్తా; Malayalam ഉണ്ട്, ചെയ്യാം).
- English service words stay English in Latin letters (service, book, slot, date, confirm, call back, number): never translated, never respelled in the local script.
- Two short sentences, never one long one, never a passive ("got done", not "was completed").
- Declare persona gender once, in English, in Role: `Persona gender: female`. Hindi marks it in the first person (बोल रही हूँ); Kannada, Tamil, Telugu, Malayalam do not, so use ordinary forms. No slash forms ("सकता/सकती").
- Put every closing line, every language, in `end_call_msg`. Silence prompts follow the language the call is in at that moment.
- A native speaker reviews every line before go-live; flag the unsure ones.

| Language | Written (avoid) | Spoken (use) |
|---|---|---|
| Hindi | विकल्प, उपलब्ध, मासिक | options, available, monthly, in Latin letters |
| Hindi | बजट, प्रॉपर्टी (English respelled) | budget, property, in Latin letters |
| Kannada | ವಾಹನ, ಸಂಪರ್ಕಿಸಿ, ಶೀಘ್ರದಲ್ಲೇ | ಗಾಡಿ, call ಮಾಡಿ, ಬೇಗ |
| Tamil | வாகனம், தொடர்பு கொண்டு, விரைவில் | வண்டி, call பண்ணி, சீக்கிரம் |
| Telugu | వాహనం, సంప్రదించి, శీఘ్రంగా | బండి, call చేసి, తొందరలో |
| Malayalam | വാഹനം, ബന്ധപ്പെട്ട്, ഉടൻ തന്നെ | വണ്ടി, call ചെയ്ത്, വേഗം |

For a new language, build the same table with a native speaker before writing any row.

## Numbers, endings, call data

Speaking rules, once, in Section 3: numbers as words never digits, never the ₹ symbol (say "rupees"); dates in full with month and year; times with morning/afternoon/evening; phone numbers and pin codes digit by digit in groups. A tool returns dates as year-month-day and 24-hour times: that is a value, not a script; say it as ordinary words in the language of the turn. Never speak a placeholder, brace, empty value or zero: say the generic ("your bike") or drop the fragment. Precompute word conversions in a pre-call function; use `preFormatVariables` for metadata.

Ending the call: list every ending so the agent knows a call ends there and nowhere else. Each ending carries its closing line, copied exactly, as the last thing said, nothing after. A closing line never follows a question whose answer has not been heard: ask, wait, then close next turn. A goodbye in the agent's own words ends nothing, since the platform ends the call only on an exact `end_call_msg` match.

## What good sounds like (final section)

Ten to twenty short scenarios describing the shape of a good turn (what it contains and where it stops), labelled never recited. They teach the turn loop by case and are the cheapest place to record a fixed failure; add one whenever a test call exposes a new one.

- Four or more words of Hindi in answer to the English opening: very next sentence is Hindi, nothing remarks on the language.
- "I'm busy": do not hold them; the callback line, their time named back, then the close.
- "What will it cost?": one line with no figure, then the ask again in the same turn; the call does not end on it.

## Review checklist

- [ ] every `[[FILL]]` in both templates replaced
- [ ] N in Section 0A equals `language_switch_min_words`
- [ ] every branch of every step names its exit; every ending names a closing line
- [ ] every SAY line has a row for each language spoken
- [ ] native speaker reviewed every added language
- [ ] every composed block four lines or fewer
- [ ] no instruction duplicated or contradicted; no leftover text from old versions
- [ ] call data is the last section

## When a call goes wrong

Find the rule or step that caused it before changing anything. A NEVER line hiding one symptom is how prompts grow without improving.

| Symptom | Likely cause | Fix at the root |
|---|---|---|
| Sounds like a recording | SAY lines outside decision points; carry missing from turn loop | turn non-decision lines into composed blocks; check 0B.5 and 0B.12 |
| Fires next nudge at a question or "hmm" | turn types missing; branch written "if they do not agree" | keep 0B.6; branch only on explicit no or objection |
| Stays English on a Hindi turn | English row as default; N differs from config; transcriber lacks language | `callkaro-language-switching` |
| Switches on "haan ji" | short-reply rule missing; `language_switch_min_words` below N | align the numbers |
| Call never ends | closing line paraphrased or missing from `end_call_msg` | verbatim list; add every row |
| Re-asks a given fact | never-ask-twice not applied to the SAY line | 0B.8; write decision questions so they can be dropped |
| Speaks a placeholder, brace or zero | missing-value rule absent | 0B.11 and generic fallbacks in speaking rules |
| Repeats the same reason | variety rule absent, or reason answered the wrong question | 0B.9 |
| Closing line followed by more speech | closing line not last in the turn | 0B.12 step 7 |
