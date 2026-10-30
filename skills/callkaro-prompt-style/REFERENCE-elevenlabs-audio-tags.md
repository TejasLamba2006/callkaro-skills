# ElevenLabs Audio Tags (v3 / v4 voices on CallKaro)

Audio tags are words in square brackets, placed in the text the TTS speaks, that change how the next words are
delivered: `[softly] कोई बात नहीं।`, `[laughs] अरे नहीं जी।`, `[sighs] देखिए honestly...`. They replace SSML on the
new ElevenLabs models. This file lists every tag ElevenLabs publishes, which ones belong on a phone call, and the
CallKaro-specific traps.

Sources: [ElevenLabs audio tags list](https://elevenlabs.io/blog/elevenlabs-audio-tags-list) (blog, the full list),
[Eleven v3 prompting guide](https://elevenlabs.io/docs/best-practices/prompting/eleven-v3) (docs, v4 notes).
Checked 30 Oct 2026. Marked **[CK]** = observed on CallKaro, not from ElevenLabs.

## Which models read tags

| `voice_model` | Tags | SSML `<break>` / `<prosody>` |
|---|---|---|
| `eleven_v4`, `eleven_v4_turbo` (turbo = the real-time one) | yes | **no** |
| `eleven_v3`, `eleven_v3_conversational` | yes | **no** |
| `eleven_flash_v2_5`, `eleven_turbo_v2_5`, `eleven_multilingual_v2` | **no: the tag is read aloud** | break only |
| Cartesia, Sarvam, Azure, any non-ElevenLabs provider | **no: read aloud** | provider-specific |

- v3 scripts work unchanged on v4. Tags work in Create speech, Stream speech and Text to Dialogue.
- **[CK] The secondary voice speaks the same text.** If `voice_configuration` is v4 and `secondary_voice_configuration`
  is Cartesia/Sarvam (the house default), every tag is spoken as a word whenever the call fails over. Either make
  the secondary an ElevenLabs v3/v4 voice, or accept that failover calls say "laughs" out loud. Decide per agent.
- On v3/v4 there is no `<break>`: pauses come from `[pause]`, `[long pause]`, ellipses (`...`) and sentence breaks.
  Old prompts with `<break time="0.5s"/>` must be converted when the voice moves to v3/v4.

## Rules (ElevenLabs)

- Square brackets only. Parentheses `( )` and braces `{ }` are not tags.
- Put the tag before the words it changes (or right after, for reactions: `ठीक है। [sighs]`).
- A delivery tag carries forward until the next tag. Reset with a neutral one when the mood changes.
- Several qualities go in ONE bracket, comma-separated: `[softly, reassuring]`. One tag per clause; two contrasting
  tags on the same words blur the delivery.
- You can write your own descriptive tag (`[warm, unhurried]`, `[nervous, trying to sound confident]`). Describe the
  voice quality; ambiguous tags can come out as a sound effect instead of a delivery.
- Ellipses add a pause and weight. CAPITALS add stress. Normal punctuation sets rhythm.
- Tags land best when the voice has that delivery in its training data. A serious voice may ignore a playful tag.
  If a tag misses, try a neighbouring one and regenerate. Test on the actual voice ID.

## Rules (CallKaro, apply on top)

- **[CK] Never tag a line that `end_call_msg` must match.** The match is character for character; a tag in front of
  "Thank you for your time." stops the call from ending.
- **[CK] Check `substrings_to_remove` before using a tag.** It deletes substrings anywhere in the reply. Retail
  Negotiations removes `thought`, so `[thoughtful]` becomes `[ful]` and is read aloud. Pick another tag or remove
  the entry.
- **[CK] Never put a tag inside a rupee figure, a name or a date** (`चार [pause] लाख` breaks the number). Only
  `[slowly]` or `[pause]` may sit right before one, to make it clearer.
- **[CK] At most one tag per turn**, and none in most turns. A tag on every line sounds acted, which is the
  opposite of the goal. Sales and support calls want warmth and small reactions, not drama.
- **[CK] Prefer tags in code-held lines** (pre-call or in-call function returns, e.g. a `say` line) over telling the
  LLM to add them. The function decides once and the line is identical every call; an LLM told to "add emotion"
  over-tags and invents tags.
- **[CK] Tags stay in English inside Hindi/regional text**: `[softly] कोई बात नहीं जी।`
- **[CK] Post-call analysis and transcripts see the tag text.** If a post-call prompt quotes agent lines or a
  function phrase-matches what the agent said, make sure a leading tag does not break the match.
- **[CK] Verify by ear** before shipping: dashboard Test Audio on the exact voice ID and model, then one test call.
  If a tag is spoken as a word, that model or provider does not support it.

## Every published tag

Phone fit: **use** = suits a sales/support call · **rare** = only in a specific moment · **no** = never on a
customer call.

### Emotion (blog table)

| Group | Tags | Phone fit |
|---|---|---|
| High energy | `[excited]` `[playful]` `[amazed]` `[powerful]` `[proud]` `[optimistic]` `[startled]` | `[excited]` / `[optimistic]` rare (good news only); others no |
| Heated | `[mad]` `[aggressive]` `[bitter]` `[critical]` `[repelled]` | no |
| Tense | `[anxious]` `[stressed]` `[scared]` `[threatened]` `[vulnerable]` `[confused]` `[busy]` | `[confused]` rare (genuinely not understood); others no |
| Low energy | `[tired]` `[bored]` `[distant]` `[despair]` `[let down]` | no |
| Calm and reflective | `[peaceful]` `[content]` `[curious]` `[thoughtful]` `[trusting]` | `[curious]` use; `[thoughtful]` use if `substrings_to_remove` allows; others rare |

Emotion tags used in the blog's sample scripts: `[jittery]` `[intrigued]` `[smug]` `[puzzled]` `[disgusted]`
`[frazzled]` `[hopeful]` `[nervous]` `[triumphant]` `[mischievous]`. Phone fit: `[hopeful]` rare; others no.

Docs list (v3/v4): `[sarcastic]` `[curious]` `[excited]` `[crying]` `[mischievously]`. Phone fit: `[curious]` use;
others no.

### Delivery and volume

`[whispers]` `[shouts]` `[softly]` `[quietly]` `[low, threatening]`; in samples: `[hushed]` `[barely audible]`
`[booming]` `[disbelief]`.
Phone fit: `[softly]` use (empathy, bad news); `[quietly]` rare; everything else no. Whispering is unclear on a phone
line.

### Pacing

`[slowly]` `[rushed]` `[pause]` `[drawn out]`; in samples: `[long pause]` `[snappy]` `[speedy]` `[slightly pause]`.
Phone fit: `[pause]` use (before a price or a decision question); `[slowly]` use (repeating a figure or address);
`[long pause]` rare (the line can feel dropped); `[rushed]` `[snappy]` `[speedy]` `[drawn out]` no.

### Reactions (non-verbal)

Blog: `[laughs]` `[sighs]` `[gasps]` `[clears throat]` `[crying]`; in samples: `[starts crying]` `[gulp]`.
Docs: `[laughs]` `[laughs harder]` `[starts laughing]` `[wheezing]` `[whispers]` `[sighs]` `[exhales]` `[snorts]`
`[swallows]` `[gulps]`.
Phone fit: `[laughs]` rare (short, only when the customer jokes; never at a complaint or a low price);
`[sighs]` / `[exhales]` rare (a soft "honestly..." moment, never at the customer); `[clears throat]` rare;
everything else no.

### Accents and character

`[British accent]` `[French accent]` `[Australian accent]` `[pirate voice]` `[Irish accent]`; docs:
`[strong X accent]` (experimental). Phone fit: no. Accent belongs in voice selection, not tags.

### Sound effects

Blog: `[thunder rumbling]` `[footsteps]` `[door creaking]` `[clapping]`; in samples: `[owl hooting]`
`[twig snapping]` `[many footsteps]` `[zipper opening]` `[dog barking]`. Docs: `[gunshot]` `[applause]` `[clapping]`
`[explosion]`, experimental `[sings]` `[woo]` `[fart]`. Phone fit: no, ever.

### Custom (write your own; examples from the blog)

Combined qualities: `[tense, cautious]` `[whispering, fearful]` `[whispering, playful]` `[whispering, nervous]`
`[hurried, impatient]` `[low, gravelly voice]`. Manner: `[like a sports commentator, speeding up]`. Situation:
`[out of breath after running up the stairs]`. Character: `[a tired detective who has heard it all before]`. Shift:
`[starting calm, then losing patience]` `[sudden, crushed disappointment]`. Other:
`[hushed and reverent, like a nature documentary narrator]` `[barely containing excitement]`
`[slow and suspenseful]` `[nervous, trying to sound confident]`.

Phone-call customs worth testing (not from ElevenLabs, write and verify on your voice): `[warm]`,
`[softly, reassuring]`, `[warm, unhurried]`, `[friendly, matter-of-fact]`, `[apologetic]`, `[gently]`.

## Starter kit for a sales or negotiation call

| Moment | Tag | Example |
|---|---|---|
| Customer is upset, bad news, bereavement | `[softly]` | `[softly] बिल्कुल समझ सकता हूँ, आप अपना ध्यान रखिए।` |
| Before the price or a yes/no decision | `[pause]` or `...` | `तो... क्या इसी price पर deal final करें?` |
| Thinking, honest admission | `[sighs]` (sparingly) | `[sighs] देखिए honestly बोलूँ तो...` |
| Customer jokes | `[laughs]` | `[laughs] हाँ जी, बिल्कुल।` |
| Asking what they mean | `[curious]` | `[curious] अच्छा, किस dealer से offer आया है?` |
| Good news | `[warm]` / `[optimistic]` | `[warm] Good news है, आपकी car का price बढ़ गया है।` |
| Reading back a figure or an address | `[slowly]` | `[slowly] चार लाख पंद्रह हज़ार रुपये।` |

Never: accents, sound effects, shouting or whispering, anger, crying, sarcasm, and any tag on a closing line.
