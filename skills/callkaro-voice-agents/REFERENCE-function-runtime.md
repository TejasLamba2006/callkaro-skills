# CallKaro function runtime: what custom function code can see and use

This describes the environment that custom function code (pre-call, in-call, post-call) runs in on a
CallKaro voice agent. It was measured by logging from inside a function on a real call, not read from
documentation. Anything not measured is marked UNVERIFIED. The platform changes, so re-measure with the
recipe at the bottom before relying on a detail.

## Seeing output from a function

- `logger.info(...)` reaches the call log (`cku calls logs <id>`, or the log blob). The line prefix shows
  `[<string>:N]`, where N is the line inside the function body.
- A bare `print(...)` did not show up in the call log. Use `logger.info`. UNVERIFIED whether `print` lands
  in some other sink.
- `logger` is already bound in function code. No import is needed.
- The platform logs `Successfully executed pre-call function <name> for capability <cap>` for each pre-call run.

## Runtime

- CPython 3.12, Linux container on Kubernetes, working directory `/app`.
- About 4,700 modules loaded, 300 distinct top-level packages.
- Importable and confirmed: `os sys json re time datetime asyncio aiohttp httpx requests pytz numpy pandas`
  and `livekit.agents`. Also loaded: `openai pymongo redis rapidfuzz phonenumbers geopy num2words
  number_parser humanize pydantic jinja2 jwt cryptography soundfile onnxruntime PIL PyPDF2 sentry_sdk
  loguru tenacity`.
- Platform packages: `utils` (at `/app/utils`), `core`, `models`, `tools`, `entrypoint`.
- Only the first `def` in a function body runs, so nest helpers inside it. Import inside the function body.

## Pre-call functions

Signature: `async def name(metadata: dict, system_prompt: str) -> str`. Return the (edited) prompt.

- They run once per capability at call start, not only when the model switches into it. A single call
  executed one pre-call function 7 times within about 7 seconds: once per capability, once with an empty
  prompt, and once on the merged prompt. Keep pre-calls idempotent and cheap.
- `metadata` is a dict of the call metadata plus keys written by earlier pre-calls. Values keep their Python
  types (an int stays an int).
- `system_prompt`:
  - on capability entry it is a real `str`;
  - on the merged/base run it is a `CapabilitySystemPrompt` object, not a `str`. Calling `.split()` on it
    raises and fails every call (`PRE_CALL_FN_FAILED`). Guard with `isinstance(system_prompt, str)` or use
    `str(system_prompt)`;
  - it can also be an empty string. Do not assume it is non-empty.
- A pre-call function with `update_call_data=True` writes back to the call data and needs 2 positional args.

### Names already bound in a function's globals (60)

`Any, Attachment, BrokenResourceError, ClosedResourceError, Config, EmailSender, JobContext, List,
RunContext, asyncio, datetime, function_tool, fuzz, httpx, json, logger, logging, math, mcp, num2words,
pytz, re, timedelta, x_secrets`, plus platform helpers:

| Helper | Looks like |
|---|---|
| `convert_to_words`, `num2words`, `year_to_words`, `iso_to_human`, `get_local_time` | number and date to words |
| `get_hubs`, `get_hubs_as_string`, `get_hub_location`, `get_nearest_hub_city`, `get_cities_in_state` | hub and city lookups |
| `get_colors_for_filter`, `get_seating_capacity_for_filter` | catalogue filters |
| `send_email`, `EmailSender`, `Attachment` | email sending |
| `call_mcp_tool`, `ensure_mcp_initialized`, `reset_mcp_server`, `mcp_session_ready` | MCP tools from a function |
| `add_functions_called`, `check_functions_called` | read and write the `functions_called` log |
| `get_job_context`, `set_x_secrets`, `x_secrets` | job context and secrets |
| `custom_llm_completion` | one-off LLM call |

Signatures were not captured: run `inspect.signature` on a helper before calling it. `json` appears in the
globals list, but `json` has been reported unbound in a custom pre-call, so confirm with a bare
`json.dumps(...)` before depending on it, or `import json` inside the function.

### `utils.format_utils` (importable)

`latin_to_devanagari, detect_language_code, get_language, language_code_map, language_unicode_ranges,
number_digit_by_digit, num_to_word, convert_single_value, custom_format, assign_pre_format_variables,
apply_formatted_metadata, remove_punctuations, time_map, DIGIT_WORDS, year_to_words, convert_to_words,
iso_to_human, get_local_time, custom_llm_completion`.

### Other `utils` modules present

`agent_utils, call_utils, capability_utils, chat_message_utils, city_wise_hubs, config, contact_utils,
credit_utils, database, email_utils, error_handler, file_utils, get_best_llm, get_best_stt, location_utils,
mail_utils, openai_utils, prompt_snippets, secrets_utils, socket_notifier, tts_cache, webhook_utils,
whatsapp_utils`, and some client-specific modules. Contents not inspected.

## In-call functions

Signature: `async def name(ctx: RunContext, arg: type = default) -> dict`.

`ctx` is a livekit `RunContext` with: `session`, `speech_handle`, `function_call`, `userdata`,
`disallow_interruptions()`, `wait_for_playout()`.

- `ctx.function_call`: `FunctionCall` with `name`, `arguments` (a JSON string), `call_id`, `created_at`, `id`.
- `ctx.userdata` and `ctx.session.userdata`: a dict that holds only platform plumbing (recording and
  dual-STT state such as `executing_fn_tool`, `received_recording`, `processed_recording`,
  `bvc_recording_finalize`, `dual_stt_*`, `audio_sidecar_finalize`). It does not carry call metadata. Call
  metadata is not reachable through `ctx`: pass needed values as function arguments, or have a pre-call
  compute them into the prompt.
- `ctx.speech_handle`: `id`, `interrupted`, `allow_interruptions`, `num_steps`, `scheduled`, `chat_items`,
  `input_details`.
- Output that is not JSON is parsed with `ast.literal_eval` and logged with a warning. Return a dict.
- Each tool call is logged twice by the platform (a self-log and a platform log). That is a logging
  artifact, not double execution.

### `ctx.session` (livekit `AgentSession`)

Methods: `say, generate_reply, interrupt, update_agent, update_options, shutdown, aclose, drain, run, start,
clear_user_turn, commit_user_turn, wait_for_inactive, emit, on, off, once`.
Properties: `history` (ChatContext), `current_agent`, `current_speech`, `agent_state`, `user_state`,
`options`, `output`, `input`, `room_io`, `usage`, `tools`, `turn_detection`, `userdata`, `conn_options`.

Signatures:

```
say(text, *, audio, allow_interruptions, add_to_chat_ctx=True) -> SpeechHandle
generate_reply(*, user_input, instructions, tool_choice, tools, allow_interruptions, chat_ctx, input_modality='text') -> SpeechHandle
interrupt(*, force=False) -> Future
commit_user_turn(*, transcript_timeout=2.0, stt_flush_duration=2.0, skip_reply=False) -> Future[str]
clear_user_turn() -> None
shutdown(*, drain=True) -> None
update_options(*, endpointing_opts, turn_detection, min_endpointing_delay, max_endpointing_delay) -> None
update_agent(agent) -> None
```

- `session.say(...)` speaks a line from code, so a function can deliver a fixed line itself.
- `session.history` is the live conversation, so a function can count what has actually been said.
- `session.llm`, `stt`, `tts` and `vad` read `None`; the models live on the agent (see below).
- `session.update_options` takes endpointing and turn-detection options only. It does not take interruption
  or VAD options.

### Session options in force

`turn_handling`: endpointing mode `fixed` with min and max delay; interruption block (enabled, `min_duration`,
`min_words`, `resume_false_interruption`, `false_interruption_timeout`); `turn_detection` (`vad`);
`preemptive_generation` (enabled, `preemptive_tts`, `max_speech_duration`, `max_retries`). Also
`max_tool_steps`, `user_away_timeout`, `tts_text_transforms` (markdown and emoji filters), `aec_warmup_duration`,
`ivr_detection`, `clear_buffer_if_not_interrupted`.

The agent-level `vad_configuration` keys `interrupt_speech_duration` and `interrupt_min_words` were observed
to land in `turn_handling.interruption` (`min_duration` and `min_words`), even though the log marks some
older keys deprecated. Observed on one version across two calls: likely, not proven for every key.

### `ctx.session.current_agent` (the platform agent class, 103 attributes)

- Tools it exposes are the agent's functions plus the capability-switch tool. Capability-scoped functions
  appear only while their capability is active.
- Language: `_current_lang, _allowed_languages, _language_switching, _language_switching_instructions,
  _lang_locked, _locked_lang, _lang_lockin_time, _lang_lock_window_sec, _lang_switch_min_words,
  _lang_switch_open, _lang_detect_counts, _last_detected_lang, _detect_language, _detect_switch_language,
  _apply_language_switch, _finalize_language_lock, start_language_lock_timer, _maybe_update_tts_language,
  _tts_lang, _TTS_LANG_OPTIONS, _LANG_NAMES, _HINDI_MARKERS, _MARATHI_MARKERS, _SCRIPT_RANGES`.
- Fillers: `_filler_llm, _filler_phrases, _filler_runtime, _filler_type, _handle_filler, _pick_static_filler`.
- Turn and interruption: `allow_interruptions, turn_detection, interruption_detection, min_endpointing_delay,
  max_endpointing_delay, min_consecutive_speech_delay, on_user_turn_completed, _clean_transcript,
  _clean_transcript_event`.
- Models: `llm, stt, tts, vad, update_llm, _get_llm_name, _multi_stt_enabled`.
- Prompt and tools: `instructions, update_instructions, tools, update_tools, chat_ctx, update_chat_ctx`.
- Other: `dial_info, participant, set_participant, session_manager, _gender_detector, volume`.

All of this is callable from function code, which is a lever and a risk: it is platform internals with no
stability promise. Prefer documented behaviour, and use these for diagnosis unless a probe on a throwaway
version proves a call is safe.

Full attribute list (names only, `dir()` output):

```
_HINDI_MARKERS, _LANG_NAMES, _MARATHI_MARKERS, _SCRIPT_RANGES, _TTS_LANG_OPTIONS, _activity, _adjust_volume_in_frame, _adjust_volume_in_stream, _allow_interruptions, _allowed_languages, _apply_language_switch, _chat_ctx, _clean_transcript, _clean_transcript_event, _current_lang, _detect_language, _detect_switch_language, _filler_llm, _filler_phrases, _filler_runtime, _filler_type, _finalize_language_lock, _gender_detector, _get_activity_or_raise, _get_llm_name, _handle_filler, _id, _instructions, _interruption_detection, _is_english, _lang_detect_counts, _lang_lock_task, _lang_lock_window_sec, _lang_locked, _lang_lockin_time, _lang_switch_min_words, _lang_switch_open, _lang_switch_started_at, _language_lock_timer, _language_switching, _language_switching_instructions, _last_detected_lang, _llm, _locked_lang, _max_endpointing_delay, _maybe_update_tts_language, _mcp_servers, _min_consecutive_speech_delay, _min_endpointing_delay, _multi_stt_enabled, _multi_stt_last_user_end_ts, _on_gender_detected, _pick_static_filler, _stt, _stt_collector_indices, _stt_collector_tasks, _stt_deactivate_consumer, _tools, _tts, _tts_lang, _turn_detection, _turn_handling, _use_tts_aligned_transcript, _vad, allow_interruptions, chat_ctx, create, default, dial_info, id, instructions, interruption_detection, label, llm, llm_node, max_endpointing_delay, mcp_servers, min_consecutive_speech_delay, min_endpointing_delay, on_enter, on_exit, on_user_turn_completed, participant, realtime_audio_output_node, realtime_llm_session, session, session_manager, set_participant, start_language_lock_timer, stt, stt_node, tools, transcription_node, tts, tts_node, turn_detection, update_chat_ctx, update_instructions, update_llm, update_tools, use_tts_aligned_transcript, vad, volume
```

A leading underscore means internal.

### Agent method signatures

```
create(*, dial_info, ctx, chat_ctx=None, tools=None, vad=None, llm=None, filler_llm=None)   async, classmethod
update_llm(new_llm)                          async  "Update the LLM mid-call for non-realtime sessions"
update_tools(tools)                          async
update_instructions(instructions: str)       async  prompt objects must be flattened to str
update_chat_ctx(chat_ctx, *, exclude_invalid_function_calls=True)   async
on_user_turn_completed(turn_ctx, new_message)  async
on_enter() / on_exit()                       async
stt_node(audio, model_settings) / tts_node(text, model_settings) / llm_node(chat_ctx, tools, model_settings) / transcription_node(text, model_settings)
_detect_language(text, is_english) -> str | None            dominant Unicode script of the text
_detect_switch_language(text) -> str | None                 language if it qualifies for a switch
_apply_language_switch(lang)                 async  "Lightweight language switch: fetch new system prompt + tools only"
_maybe_update_tts_language(text)                            switch TTS language to match LLM text
_finalize_language_lock(reason)              async  lock by max selector detections, close other STT streams
start_language_lock_timer()
_clean_transcript(text) / _clean_transcript_event(event)    strip configured punctuation from transcripts
_handle_filler(filler_llm_ctx, new_message) / _pick_static_filler()
```

## Language, STT, TTS, LLM and turn handling

Measured by reading the objects, without calling any of them. Whether any of it can be changed mid-call is
UNVERIFIED (see "Open questions").

### STT (`agent.stt`, a livekit `FallbackAdapter`)

- Providers are tried in the configured order (primary, then fallback). `attempt_timeout` 10 s,
  `max_retry_per_stt` 1, `retry_interval` 5 s. `switch_to_next()` exists and the silence monitor uses it.
- Soniox (realtime websocket): the languages are passed as a `language_hints` list that equals the version's
  transcriber language list, with `language_hints_strict` true, plus a context object (`general`, `text`,
  `terms`, `translation_terms`). The stream is opened with `language=NOT_GIVEN`: languages travel as hints,
  not as a stream argument. The class has no `update_options`; it has `pause_all_streams` and
  `resume_all_streams`.
- Sarvam realtime: options `language`, `mode`, `stream_type`, `endpointing`, `sample_rate`, `prompt`; it has
  `update_options(language, stream_type, mode, endpointing, sample_rate, prompt, return_timestamps,
  vad_sot_threshold, vad_min_speech_ms, vad_min_silence_ms, vad_prefix_padding_ms)`.

### What the platform's own language switching does

State: `_language_switching`, `_allowed_languages`, `_lang_lockin_time`, `_lang_lock_window_sec`,
`_lang_switch_min_words`, `_lang_locked`, `_current_lang`, `_multi_stt_enabled`. On each user turn it runs the
detector and logs either a switch or "No qualifying language detected; keeping current language".

A switch changes the prompt, the tools and the TTS language. In the logs the platform never retargets the
Soniox stream itself: it relies on the `language_hints` list already covering every language. So the
transcriber language list is a configuration decision, not something the switch logic repairs. A list that
omits a language will transcribe a speaker of that language badly even if the prompt switches correctly.

### VAD

Silero on ONNX/CPU. Options: activation threshold, deactivation threshold, `min_silence_duration`,
`min_speech_duration`, `prefix_padding_duration`, `max_buffered_speech`, 16 kHz. `vad.update_options(...)`
takes those same six values.

### TTS (`agent.tts`, a `FallbackAdapter`)

Primary and fallback providers with `max_retry_per_tts` 2. Both observed providers have `update_options`:

- Sarvam: `model, target_language_code, speaker, pitch, pace, loudness, temperature, output_audio_bitrate,
  min_buffer_size, max_chunk_length, enable_preprocessing, dict_id, enable_cached_responses,
  send_completion_event, output_audio_codec`.
- ElevenLabs: `voice_id, voice_settings, model, language`, pronunciation dictionary locators.

### LLM (`agent.llm`, a `FallbackAdapter`)

`attempt_timeout` 6 s, `max_retry_per_llm` 0, `retry_interval` 0.5 s, `retry_on_chunk_sent` false. The primary
is served through the platform's own LLM gateway; the fallback is an Azure OpenAI model through the Responses
API. The agent's model name in config (for example `callkaro/arjuna-2.5`) is not the name the object carries:
the object reports the gateway's internal model name.

Consequence seen on a real call: a primary that gives no answer within 6 s is abandoned for the fallback with
no retry, and the caller can hang up before the fallback answers. That call ended with zero LLM tokens and no
greeting, so a first-turn greeting that depends on the LLM is exposed to this. `update_llm` is what the
platform calls on every capability switch.

### Open questions (UNVERIFIED)

- Does `tts.update_options(...)` mid-call take effect, and does it survive the next
  `_maybe_update_tts_language`?
- Does editing the Soniox `language_hints` have any effect on an already-open stream?
- Does the language lock overwrite a manual change?

Test these on a throwaway version, one change per call, reading the object back after each.

## Environment

About 280 environment variables are visible to function code. Names include provider API keys (LLM, STT,
TTS), database URIs, webhook URLs, LiveKit and Kubernetes service variables, and per-client secrets. A probe
that must list the environment should print names only, never values.

Treat this as a risk, not a feature: function code can read secrets that belong to the platform and to other
integrations. Use `x_secrets` (Dashboard Settings > Secrets) for your own.

## Probe recipe (to re-measure or go deeper)

1. Clone a version: `ck agents clone-version <agent> --versions <src> --name "<probe name>" --prompt-type 2
   --language hi`. Never probe on a live or published version.
2. Add two functions with `ck agents update <agent> --versions <new> --set @file.json` (only `functions` and
   `capabilities`): a `custom_pre_call` that logs and returns `system_prompt` unchanged, and a `custom_in_call`
   taking `ctx` that logs and returns a dict.
3. Add one sentence to the first capability prompt telling the model to call the in-call probe once, silently,
   before speaking.
4. Filter every logged value. Drop the whole value when the name looks secret (key, secret, token, password,
   auth, cookie, credential). Masking only part of a secret leaves its tail in a stored log.
5. Dial with `cku calls make --agent <a> --to <n> --metadata "$(cat compact.json)" --versions <new> --test`
   (git-bash; metadata must be one-line JSON). Test calls need the owner's go-ahead each time.
6. Read the log and write the results to a file (terminal output can be swallowed). Check that the probe's
   start and end marker lines are both present before concluding anything: a call can fail before the probe
   runs, for example when the primary LLM times out and the caller hangs up before the model's first turn.

Not yet probed: `inspect.signature` and docstrings for the global helper table; the contents of
`utils.webhook_utils`, `utils.whatsapp_utils` and `utils.database`; what `x_secrets` is (dict, object or lazy
loader), keys only; whether `print` goes anywhere.
