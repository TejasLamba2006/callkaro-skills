# funnel.json config reference

One JSON file per report. Copy `references/example-spinny-auction.json` and replace every value the user has not confirmed (Stage 0 of SKILL.md). Values in the example are a working reference, not recommendations.

## Top-level fields

| Field | Meaning |
|---|---|
| `name`, `period_label` | Report title and period text |
| `agent_id` | Agent ID for `cku calls list --agent` |
| `window` | `start_ist`, `end_ist` (`YYYY-MM-DD HH:MM`), `tz_offset_hours` (5.5 for IST), `bins` (`"weekly"`, `"none"`, or a list of `{label, start_ist, end_ist}`) |
| `versions` | `null` for all, or a list of version names or IDs |
| `min_n` | Rates on fewer leads/calls than this are flagged, not coloured (default 5) |
| `city_field` | Dotted path to city on the call record (default `city`) |
| `scenario_field`, `quadrant_field`, `arm_field` | Optional dotted paths for breakdown sheets; omit to skip the sheet |
| `crm_join` | `{call_field, crm_key, status_field, deal_value}` for `--crm` joins |
| `dnd_rule` | Rule for the DND column on City Funnel |
| `success` | Rule defining a deal (counts on any call) |
| `stages` | Ordered list of `{key, label, rule}`; first stage `rule: null` means every called lead |
| `exclude_calls` | Rules; a matching call is dropped before analysis |
| `checks` | Extra pricing/safety rules reported on the Summary sheet, each `{label, rule}` |
| `drop_reasons` | `stages_audited`, `reasons_per_stage` (key to description), `sides`, `llm` (`model`, `gateway`, `key_env`), `sample` |
| `targets` | Starting targets for the Targets sheet (0 = use the period average) |
| `defaults_used` | List of every default taken without asking the user |

## Call record fields (written by `pull_calls.py`)

| Key | Meaning |
|---|---|
| `id`, `at` | Call ID; start time (UTC, ISO without zone) |
| `duration`, `hangup_reason`, `disposition_reason` | Platform fields |
| `version`, `version_id` | Version name and ID (the ID changes on a language handoff, see SKILL.md) |
| `lead` | `metadata.lead_id` (calls without one count as their own lead) |
| `city`, `insp_city`, `phone_last4` | City fields; phone masked to last 4 digits |
| `recording_url`, `sch_id`, `batch_id`, `credits`, `latency` | Platform fields |
| `post_call`, `metadata` | Post-call and call metadata dicts |
| `functions` | Function names called (`functions_called` plus in-chat calls) |
| `function_outputs` | `[{name, output}]` from `function_call_output` items |
| `capabilities_switched` | Capability names from `switch_capability` calls |
| `transcript` | `[role, text, model_name]`; role `u` customer, `a` agent, `f` function (text = function name) |
| `human` | Connected (human) filter result |
| `opening_lang`, `customer_lang` | Dominant script of the first agent turn of 3+ words and of customer turns |

Dotted paths read nested dicts, for example `post_call.mark_dnd`.

## Rule grammar

Rules nest with `all`, `any`, `not`.

Field rules: `{"field": "path", "op": OP, "value": v}`, where OP is one of:

- `==`, `!=` (case-insensitive for strings)
- `>`, `>=`, `<`, `<=` (numeric)
- `in` (value is a list)
- `contains` (substring, or membership in a list), `not_contains`
- `truthy` (non-empty and not false/0/none)
- `regex` (Python regex, case-insensitive)

Built-in predicates:

| Predicate | Example |
|---|---|
| `{"is_human": true}` | Human filter result |
| `{"capability_visited": "deal_closure"}` | Capability appears in `capabilities_switched` |
| `{"function_called": "context_setting"}` | Function name in `functions` |
| `{"transcript_agent_regex": "re"}` | Any agent line matches |
| `{"transcript_customer_regex": "re"}` | Any customer line matches |
| `{"function_output_regex": "re"}` or `{"function_output_regex": {"name": "fn", "regex": "re"}}` | Any function output matches (optionally only for one function) |

## Stage rules: check before trusting

- Stages are cumulative. A lead is at stage k only if it passed stage k-1 on some call. A success call that never passed an earlier stage still counts only at the stages it passed.
- Test each rule by hand on about 10 real calls before the full run.
- Post-call fields are model-filled and can be wrong. Prefer a function call or transcript fact when one exists, and say so in the report.
- Each stage needs an independent check in `verify.py`. The verify evaluator covers the same predicates as `funnel.py`.

## Windows and bins

`bins: "weekly"` splits from `start_ist` into 7-day bins. `bins: "none"` gives one bin. Explicit lists let the user set bins by hand.

## CRM join

When `--crm` is given, `funnel.py` joins CRM rows (CSV or JSON) on `crm_join.crm_key` against the call field `crm_join.call_field`, counts `Both: deal`, `Bot deal, no CRM`, `CRM deal, bot no deal`, `Neither`, and reports CRM rows with no matching call. Unmatched rows are counted, never dropped silently.
