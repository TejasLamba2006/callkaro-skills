---
name: callkaro-conversational-voice
description: Make a CallKaro voice agent sound like a person on the phone, not a script reader. Use when calls feel robotic, turns run long, the agent repeats itself, reads scripts over the customer, sounds too polished, or handles Hinglish and multilingual (Indian language) callers badly. Covers turn length, script-vs-goal prompting, example exchanges, rationed fillers, reacting first, prompt size vs latency, multilingual switching, and how to test.
---

# Conversational Voice: Sounding Human on CallKaro

A voice agent sounds like an AI for a few repeatable reasons: long polished turns, lines read over
the customer, the same sentence twice, and details read back every turn. This skill lists the fixes
the published voice-agent guides agree on, then adds what we learned tuning a live multilingual
Hinglish negotiation agent on CallKaro. Sources are linked inline and in the repo README.

Companions: `callkaro-prompt-style` (plain-text layout, SSML pauses), `callkaro-voice-agents`
(capabilities, functions, language settings), `callkaro-qa-grader` (grading calls).

## 1. The root cause: script-first prompts

A language model writes clean, grammatical text because it was trained to. Speech is not like that,
so a perfectly polished sentence is exactly what makes a caller hear a machine
([LiveKit](https://livekit.com/blog/prompting-voice-agents-to-sound-more-realistic),
[Vapi](https://docs.vapi.ai/prompting-guide)). A prompt that says "say these lines exactly, in
full, in order", with lines of three to five sentences, guarantees a monologue on every turn. More
rules won't fix that. Shorter lines and fewer verbatim ones will.

Keep verbatim ONLY for lines that must be exact for legal, money or platform reasons (a hold notice,
a deductions disclaimer, the closing phrase that `end_call_msg` must match character for character).
Everything else becomes a goal plus one short example line the model may say in its own words.

## 2. Turn rules

- One or two sentences per turn and one question at a time
  ([CloudTalk](https://help.cloudtalk.io/en/articles/11058815-voiceagent-prompt-best-practices):
  "Never speak more than 2 sentences at a time";
  [Ultravox](https://docs.ultravox.ai/gettingstarted/prompting);
  [Vapi](https://docs.vapi.ai/prompting-guide)).
- Split a long script into beats. Say one beat, let them react, then the next. The price, then (on
  their reaction) the validity window, then the question. Never all three bundled every turn.
- React first, then content. Answer what they just said, even in one word, before any line. A
  customer question followed by the next script line is the most robotic thing an agent does.
- Match energy: a brisk caller gets fewer words and a faster pace; a chatty one gets a quick riff
  before the next step ([Vapi](https://docs.vapi.ai/prompting-guide)).
- Don't read back soft data every turn. Say the price and the validity once per phase unless asked
  ([Vapi](https://docs.vapi.ai/prompting-guide)).
- Never the same sentence twice in a call. If they say "what?" / "kya hua?", give the point again in
  one short NEW sentence, not the same long line. (Live finding: a repeated long line after "ఏమైంది?"
  made the call feel like a loop.)
- An unclear or garbled reply gets one short clarifying question, never a repeat of the pitch and
  never "don't you understand" ([Vapi](https://docs.vapi.ai/prompting-guide) "one short clarifier").

## 3. Speak like speech

- Allow spoken fragments and sentences that start with "and / but / so" ("और", "पर", "तो")
  ([LiveKit](https://livekit.com/blog/prompting-voice-agents-to-sound-more-realistic)).
- Fillers, rationed: a few "hmm", "achha", "dekhiye", "toh" on neutral turns. Vapi suggests 2 to 4
  per turn as a ceiling; none on serious moments (price, deductions, bad news, closing), where a
  filler sounds worse than silence
  ([Auto Interview AI](https://www.autointerviewai.com/blog/prompt-engineering-voice-ai-interruptions-latency-2026)).
  On TTS, too many fillers sound glitchy: start low.
- Vary the short reaction ("samajh raha hoon", "bilkul", "sahi baat hai", "achha") and never use the
  same one twice in a row. Empathy openers are only for pushback; a "yes" gets an agreement reaction
  ("bahut badhiya", "perfect"), never "I understand" or a repeated question.
- Name use: once every two or three turns at the start of a line ("Rahul ji, ..."). Never "ji {name}
  ji" and never the name in every line.
- Write for the ear: numbers, dates, years and times as words ("twenty twenty-three", "ten thirty
  pm") ([Deepgram](https://developers.deepgram.com/docs/prompting-voice-agents),
  [Dapta](https://dapta.ai/blog-posts/best-ai-voice-agents/)). In Hindi use Hindi number words, and
  put a space before the punctuation after है (see `callkaro-voice-agents`, Hindi TTS).

## 4. Show, don't only tell: example exchanges

Rules alone produce rule-shaped speech. Add 4 to 6 short example exchanges: a happy path, an
objection, an unclear reply, an interruption. Write them as a bad line vs a better line
([LiveKit](https://livekit.com/blog/prompting-voice-agents-to-sound-more-realistic): "I can
definitely handle that for you" vs "Yeah, um so, I can do that, no problem";
[Vapi](https://docs.vapi.ai/prompting-guide): at least a happy path, an edge case, an error
recovery). Take them from the best real calls: mine recordings of your best human agents, or your
best human-answered agent calls, for phrasing to copy
([LiveKit](https://livekit.com/blog/prompting-voice-agents-to-sound-more-realistic);
[DEV: prompt engineering & conversation design](https://dev.to/moisi_trungu_31647b7ac300/ai-voice-agent-prompt-engineering-conversation-design-5fk3)).

Hinglish example pair:
```
Robotic: "जी राहुल जी, आपकी car की evaluation हुई है और अब तक का best offer यही है। Price अगले एक दिन तक valid है। क्या हम इस price पर आगे बढ़ें?"
Human:   "हम्म, समझ सकता हूँ। देखिए, अभी तक इससे ऊपर कोई नहीं गया है... आपके mind में कितना था?"
```

## 5. Prompt size is latency

The whole system prompt is sent on every turn. A bloated prompt means a longer time to the first
token, which the caller hears as dead air ([Vapi](https://docs.vapi.ai/prompting-guide)). On a
multi-prompt agent the base prompt plus the current capability are both sent every turn, so:
- Deduplicate. A turn contract copied into every capability costs its size five times.
- Keep per-language rows in the capability that uses them, not in the base.
- Replace a space-joined `{{var}} {{var}}` registry with labelled `name: {{var}}` lines. The engine
  substitutes values only, so an unlabelled registry renders as one meaningless line of values.
- Delete placeholders nothing fills: the model sees them literally.

## 6. Multilingual and Hinglish callers (India)

- Mirror the caller's language mix; never ask them to pick a language. Keep English business words
  (price, offer, payment) inside Indian-language sentences
  ([SquadStack](https://www.squadstack.ai/blog/can-ai-voice-agents-handle-hinglish-and-code-switching)).
- Don't translate scripts word for word; write each language's line in its own everyday spoken
  register and have a native speaker check it
  ([Rootle](https://rootle.ai/blog/multilingual-voice-ai-mistake/)). Unnatural cadence is the top
  reason people disengage, often in the first ten seconds.
- Most Hinglish failures start in speech recognition
  ([Deepgram](https://deepgram.com/learn/hinglish-voice-ai-speech-recognition)). CallKaro lessons
  from a live 10-language agent:
  - Never list a language in the Soniox `transcriber_language` whose script Hindi speech can land in.
    With `pa` listed, a Hindi speaker was transcribed in Gurmukhi and the agent answered in Punjabi.
    The prompt can still speak that language; only the transcriber list changes.
  - Script is not language: the model must judge the words, not the script of the transcript.
  - A reply of three words or fewer never switches the language ("nahi", "illa", "ledu" are usually
    the transcriber guessing).
  - Set `language_switch_min_words` to the same count your prompt uses (we use 4). A mismatch makes
    the platform detector and the prompt disagree.
  - The platform's "Conversation language changed, so reply in X" note is an automatic guess. A
    customer's explicit request for a language must win over it, and switches are silent: "I will
    continue in Tamil from now on" is wrong.
  - On arjuna-class models, capabilities with Hindi-written scripts drifted back to Hindi on English
    calls; verbatim per-language rows for their lines fixed it (a gpt-4.1 capability did not drift).

## 7. Interruptions and turn-taking

Stop, listen, respond; never keep reading after a barge-in, and never restart the cut sentence
([Vapi](https://docs.vapi.ai/prompting-guide)). Much of "feels human vs robotic" is the turn-taking
layer, not the prompt ([Retell](https://www.retellai.com/blog/how-real-time-voice-ai-works-stt-llm-tts)).
Backchannels ("mm-hmm") mean "keep going", not a bid for the turn
([Deepgram](https://deepgram.com/learn/backchannels-vs-interruptions-voice-agents)). On CallKaro,
`<Wait>` in a prompt is only text: models sometimes echo it into speech, so add `<Wait>`, `<wait>`,
`<Wait for response>` and `<Wait for user response>` to `punctuations_to_remove`.

## 8. Test like a caller

- Call it and interrupt it; talk over the greeting. A natural agent stops and listens
  ([Dapta](https://dapta.ai/blog-posts/best-ai-voice-agents/)).
- Test with mumblers, interrupters and multi-request callers, and with people who did not build it.
  Change one rule per iteration so you can see its effect
  ([Famulor](https://www.famulor.io/blog/how-to-write-an-ai-voice-agent-system-prompt-in-2026)).
- Track engagement, not completion: bot words per turn, % of turns over two sentences, repeated
  sentences, customer words per turn, and hangups right after a long bot turn. Robotic calls often
  show as "completed" in the logs.
- Always test on a real phone line; a browser demo hides latency and transcription problems
  ([Deepgram](https://deepgram.com/learn/hinglish-voice-ai-speech-recognition)).

## 9. Evidence from a CallKaro account audit (136 calls, 2026-09)

An audit of one negotiation agent's calls, compared with five well-performing agents on the same
account (auction, retail and service reminders; 329 calls with at least five customer turns). It
backs every rule above with numbers from the platform itself:

| metric | script-first agent | the good agents |
|---|---|---|
| median words per bot turn | 32 | 17 to 20 |
| turns over 35 words or 2 sentences | 50% | 20 to 28% |
| turns re-reading the validity window | 22% | rare |
| turns bundling price + validity + question | 18% | rare |
| repeated sentences per call | 1.8 | about 0 |

- The script-first agent had 301 quoted lines averaging 23 words (114 over 25 words). A good auction
  agent had 36, averaging 6.7 words, none over 25. The long argument blocks (60 to 130 words each)
  came out as monologues on every agent that used them, old and new builds alike.
- A prescribed list of opening reactions ("start with X, Y or Z") put the same opener on almost
  every turn (one phrase opened 37 turns). Let the model react only when it adds meaning.
- Rules like "never repeat" and "answer off-script questions" were in the prompt and were still
  broken. When scripts dominate a 100k-character prompt, the behaviour rules drown. Cut the script
  text first, then put the turn-length rule at the top.
- What the good prompts say, in their own words: "An ordinary turn is one idea, at most two short
  sentences, and exactly one question... A short sentence is about twelve words." "GOAL / MUST
  CONTAIN / NEVER, freely phrased. You compose the words yourself, fresh, every time." "A question
  is never a refusal. Answer it in one short line, then return to the step that was open." "Never
  reuse one of your own sentences, and never open two turns in a row with the same word."
- Price and validity only when asked, in one line: "अभी तक मिला price छह लाख सतहत्तर हजार रुपये
  है। यह offer अगले छह घंटे तक valid है, क्या आप इसी price पर proceed करना चाहेंगे?" (average bot
  turn in that call: 11.6 words).
- Longer turns and larger prompts showed up as a latency tail: p90 end-to-end latency 3.3 s against
  2.2 s on the leaner build.

## Quick checklist

- [ ] Turn-length rule at the TOP of the prompt: one idea, at most two short sentences, one question
- [ ] Verbatim only for legal/money/closing lines; the rest are GOAL / MUST CONTAIN / NEVER, freely phrased
- [ ] Every scripted line is at most two sentences; long ones split into beats
- [ ] React to the customer before any line; one question per turn; no prescribed opener list
- [ ] Price and validity said once per phase, not every turn
- [ ] No sentence ever said twice; "what?" gets a short new sentence
- [ ] 4 to 6 example exchanges from real calls, bad vs better
- [ ] Fillers rationed, none on price/deductions/closing
- [ ] Prompt deduplicated; labelled CALL DATA; no unfilled placeholders
- [ ] Soniox list has no script-colliding language; min words matches the prompt
- [ ] `<Wait>` tokens in `punctuations_to_remove`
- [ ] Tested by people who didn't build it, on real phone lines
