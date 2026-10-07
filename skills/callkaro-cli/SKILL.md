---
name: callkaro-cli
description: Operate CallKaro voice and chat agents, calls, numbers, batches, simulations and analytics through the cku command-line tool. Use for ANY CallKaro task done from a terminal or a script — listing or editing agents, publishing versions, A/B tests, placing calls, reading call logs, managing phone numbers, batch campaigns, audits, or switching between accounts. Prefer this over raw REST when the CLI covers the job.
---

# CallKaro CLI (`cku`)

Terminal interface to CallKaro. One binary, two names in the wild:

- **`cku`** — the unofficial fork (`callkaro-cli-unofficial`). Install this.
- **`ck`** — the official CLI (`@callkaro-official/cli`).

They are **separate programs that share nothing**. Both are usually installed.
`cku` talks to the same backend and the same accounts, so all commands below
work identically on either — substitute `ck` for `cku` if that is what is
available. Check with `cku --version`.

## Before anything else

```bash
cku whoami          # am I logged in, and as whom?
cku config          # endpoints, account in use, where that choice came from
```

If not logged in: `cku login` (opens a browser; no password in the terminal).

**Never invent ids.** Every id must come from a `list` call first. Ids are
24-character hex strings; the backend rejects anything else with
`Invalid id: not a valid id`.

**Prefer `--json` whenever you intend to parse the output.** Human tables are
for people; they are not a stable interface. `--json` prints a bare array or
object; where metadata matters it is opt-in (`cku calls list --json --meta` gives
`{calls, pagination}`, and `--page <n>` walks further pages). Piped output
carries no ANSI colour codes.

**Nothing here waits for a keypress without a terminal.** Destructive commands
need `--yes` when stdin is not a TTY, and commands that would otherwise prompt
fail at once naming the flags to pass. In a script, always pass them.

## Which account am I acting as?

This is the first thing to check when something looks wrong — acting on the
wrong account is the most damaging mistake available here.

```bash
cku accounts status
```

Reports the account in effect *and where the choice came from*:

| Source | Meaning |
|---|---|
| `CK_ACCOUNT` | set in the environment for this invocation |
| `.cku.json` | this folder is pinned to an account |
| global default | no folder binding — the shared fallback |

Resolution order:

```
CK_TOKEN  >  CK_ACCOUNT  >  ./.cku.json  >  ~/.config/callkaro-unofficial/active.json  >  none
```

### If you are working in a folder, bind it — do not switch globally

```bash
cku accounts bind <email>     # writes .cku.json here
cku accounts unbind           # remove it
```

`.cku.json` contains only the account slug, no token, so it is safe to commit.
A bound folder ignores the global default entirely.

**This matters when several agents run at once.** Two agents in two folders both
calling `cku accounts use <email>` will overwrite each other's selection, and
whichever wrote last silently takes effect — one bot then starts operating on
the other's account with no error. `cku accounts use` changes *global shared
state*; `bind` is per-folder and cannot collide. Use `bind` unless you
deliberately want the shared default to change.

`CK_ACCOUNT=<email> cku whoami` overrides for a single command — useful in
scripts, and the safest option when you cannot write to the folder.

## Agents

```bash
cku agents list
cku agents get <agentId>
cku agents versions <agentId>
```

An agent has **agent-level** fields (name, phone numbers, which version is
published) and **version-level** fields (prompt, model, voice, temperature).
This distinction drives the most common error — see Updating below.

```bash
cku agents create --file agent.json          # quote-proof
cku agents create '{"name":"My Agent"}'      # inline
cku agents create @agent.json
cku agents create < agent.json
```

`versionName` defaults to `v1`. The backend fills in the rest.

### Updating — two rules that bite

```bash
cku agents update <agentId> --set '{"name":"New Name"}'
cku agents update <agentId> --set '{"temperature":5}' --versions <versionId>
```

**Rule 1: version-level fields need `--versions`.** Without it the CLI errors
and names the offending fields. Passing `--commit "<msg>"` on an agent-level
update attaches the message to the agent's current version automatically.

**Rule 2: partial objects are merged, not replaced — on `cku` only.** The
backend replaces `voice_configuration`, `transcriber`, and seven other objects
*wholesale*. A partial update would drop every key you did not name, and the
agent would be left with no voice. `cku` merges against the current value first.
On the official `ck`, **it does not** — so with `ck`, always send the complete
object. When a voice or transcriber change "silently does nothing", this is why.

```bash
# correct on both CLIs — send the whole object
cku agents update <id> --set '{"voice_configuration":{
  "voice_provider":"Eleven Labs","voice_model":"eleven_flash_v2_5",
  "voice_id":"abc","voice_language":"en","voice_speed":1.1}}'
```

Values are validated before sending: enum fields list their allowed values,
and a voice/transcriber model belonging to a *different* provider is rejected
locally. Both mistakes otherwise persist silently and only show up as a broken
call.

### Version lifecycle

```bash
cku agents clone-version <id> --versions <src> --name v2 --prompt-type 1 --language hi
cku agents publish <id> --versions <versionId>
cku agents toggle-active <id> --versions <versionId>
```

`--prompt-type` is `0`–`3`; `--language` is one of `en hi kn ta te mr gu bn ml`.
`clone-version --set` only accepts `transcriber`, `secondary_transcriber`,
`voice_configuration`, `secondary_voice_configuration`, `silence_language`.

### A/B testing

```bash
cku agents ab <id> --versions "<vid1>=60,<vid2>=40"   # ratios sum to 100
cku agents ab <id> --disable
cku agents ab-advanced <id> --show                    # inspect rules first
cku agents ab-advanced <id> --rules @rules.json
```

Advanced A/B is an ordered `if`/`elseif`/`else` chain over call metadata.
`returnType: "version"` pins a version; `"language"` overrides only the
language. Rules run before ratio A/B, and only when the call does not pin a
version. Read with `--show` before writing.

### Phone numbers

```bash
cku agents set-inbound  <id> --number <numberId>
cku agents set-outbound <id> --number <numberId>
cku agents set-outbound <id> --clear
```

One inbound agent per number; the server returns 409 on conflict. An outbound
number may be shared by several agents.

## Calls

```bash
cku calls make --agent <id> --to <number> --test   # --test for a safe trial
cku calls list --limit 20
cku calls get <callId>
cku calls export --start 2026-09-01 --file calls.csv
```

`--var k=v` is repeatable and becomes call metadata. Filters shared by `list`
and `export`: `--type --agent --versions --start --end --batch --hangup
--duration --to --converted --lead --buylead`.

### Reading a call's raw log

```bash
cku calls logs <callId>
cku calls logs <callId> "grep -iE 'error|warning' /call.log"
cku calls logs <callId> "grep ERROR /call.log | sort | uniq -c | sort -rn | head"
```

A sandboxed in-process shell over `/call.log` — `grep`, `awk`, `sed`, `cut`,
`sort`, `uniq`, `head`, `tail`, `wc`, pipes. **No process is ever spawned**, so
any query is safe. No default query tails the last 100 lines with trace noise
dropped. Logs are kept 7 days; the blob URL is never printed.

This is the fastest way to diagnose a failed call. Start here before theorising.

## Phone numbers

```bash
cku numbers list
cku numbers catalog          # buyable pool + price
cku numbers buy <numberOrPhone>
cku numbers spam <numberOrPhone> [--off]
cku numbers release <numberOrPhone>
```

Accepts an id *or* the number itself, with or without `+`, spaces or dashes.

## Batches

```bash
cku batches create --file leads.csv --name "Q3 outreach" --agent <id>
cku batches schedule --file leads.csv --name X --at "2026-08-05T10:00:00+05:30" \
  --window 10:00-19:00 --retries 2 --gaps 30,60
cku batches list
cku batches status <batchId>
cku batches send-next-try <batchId>
cku batches download <batchId> --type receipts
```

CSV rows may carry `x_agent_id` and `x_schedule_at` to override per row.

## Simulations

```bash
cku sim create <agentId> --name "cold call" --prompt "..." --criteria "..." \
  --variables '{"lead_id":"900029","city":"Delhi"}' \
  --functions '[{"name":"context_setting","response":{"ok":true}}]'
cku sim run <agentId> --tests <id1>,<id2> --versions <v1>,<v2> [--epoch 3] --wait
cku sim runs <agentId>
cku sim results <batchId> --wait --agent <agentId>
cku sim delete <testCaseId> --yes
```

- `--variables` fills the agent's `{{placeholders}}` for that test. Give a JSON
  object (inline or `@vars.json`); numbers and arrays are
  stringified for you, because the backend stores every value as a string.
- `--functions` mocks tool calls: a list of `{name, response}`. Which calls are
  mocked is decided by the server; there is no flag to force real functions.
- **Use `--wait`** instead of polling. It blocks until every result of the batch
  exists (`tests x versions x epoch`), prints a PASS/FAIL table, and **exits 1 if
  any test failed or the wait timed out** (`--timeout <seconds>`, default 600).
  Progress goes to stderr, so `--json` stdout stays parseable. On a timeout the
  run is still going: re-attach with `sim results <batchId> --wait --agent <id>`.
- Without `--wait`, runs are asynchronous: `sim run` returns a batch id and
  `sim results` shows whatever has finished so far.
- `sim delete` needs `--yes` when there is no terminal; without it the command
  fails immediately instead of waiting for a keypress.

### Saved variable sets (dashboard credential)

Named sets of test variables, shared across an agent's tests. These use the
dashboard sign-in below, not `cku login`.

```bash
cku sim variables list <agentId>
cku sim variables show <agentId> <name-or-id>
cku sim variables create <agentId> <name> --variables @vars.json
cku sim variables delete <agentId> <name-or-id> --yes
```

A name that matches more than one set is refused, not guessed; use the id.

## Analytics

```bash
cku analytics overview
cku analytics performance
cku analytics version <agentId>
```

## Voices and transcribers

```bash
cku voices --providers                        # which providers, which models
cku voices --provider cartesia --fields       # exact keys that provider takes
cku voices --provider sarvam --language hi
cku transcribers
cku transcribers --provider deepgram --fields
```

`--fields` is the important one: it lists exactly which keys that provider's
`voice_configuration` / `transcriber` object should carry. Writing a key a
provider does not use puts the agent in a state the web UI cannot edit or undo.

### Which models are actually allowed

```bash
cku models                 # per slot, and which field each governs
cku models --slot agent    # the full list for one slot
cku models --json
```

**Models are scoped per slot, and the slots do not agree.** `agent` has 44
models; `post-call` has 9 and excludes `gpt-4o` and `o4-mini`. So this is fine:

```bash
cku agents update <id> --set '{"model":"gpt-4o"}'
```

and this is rejected locally, correctly:

```bash
cku agents update <id> --set '{"postcallmodel":"gpt-4o"}'
```

`model` and `secondary_model` follow the `agent` slot; `postcallmodel` follows
`post-call`. There are other slots the server exposes (`kpi-rca`, `ai-auditor`,
`simulation`, …) that are not agent fields.

`cku models` works with or without a dashboard session — it reads the live
server when you have one, otherwise the copy in `catalog.json` last synced from
it, and it prints which source it used. A model that a stale list omits is
rejected *before* it reaches the server, so a refusal is not proof the model is
unavailable.

## Dashboard commands need a second credential

`cku kpi`, `cku analyzers`, `cku models` and `cku sim variables` talk to the **dashboard** API, not
`/cli/*`. They need their own sign-in:

```bash
cku dashboard login      # separate from `cku login`
cku dashboard whoami     # is the stored token still valid?
cku dashboard probe      # which dashboard routes this token can reach (read-only)
cku dashboard logout
```

Without it these commands fail with `Run 'cku dashboard login'`. That is not a
bug and not a fixable-with-retry condition — the two credentials are genuinely
separate and neither works for the other.

| | `cku login` | `cku dashboard login` |
|---|---|---|
| grants | `/cli/*` — agents, calls, numbers, batches | `/pending-tasks`, `/kpi-manager`, `/v1/*` |
| token | `ck_…` | dashboard JWT (a cookie) |
| lifetime | until logout | **24 hours**, no refresh endpoint |

The dashboard token expires after 24h and the server has no refresh endpoint.
`cku dashboard login` therefore **stores the password by default** (plain text in
the account file, mode 0600 — the same exposure as the tokens beside it), and the
CLI silently signs in again when the token lapses. Pass `--no-save-password` to
opt out; then a long-lived automation that starts failing on `kpi`, `analyzers`
or `sim variables` is just an expired session, and the fix is to re-run
`cku dashboard login`, not to rewrite the script. `cku dashboard logout` removes
the stored password with the session.

### Escape hatch: `cku dashboard api`

For a dashboard route the CLI has no command for yet:

```bash
cku dashboard api GET /v1/test-simulations --query agentId=<id>
cku dashboard api POST /v1/some-route --body '{"a":1}'     # or --body @file.json
```

It uses the stored session, so **never read the token out of the account file or
hand-roll `curl`/`urllib` requests** — that is exactly what this replaces. The
path must start with `/` (full URLs are refused), redirects are not followed, and
only GET/POST/PUT/PATCH/DELETE are allowed. The response body is printed as JSON;
a non-2xx prints `HTTP <status>` and the full error body to stderr and exits 1.
Prefer a real command when one exists.

## KPI manager and the pending-task board

`cku kpi` is the only way to reach the pending-task board from a terminal. The
official `ck` has no KPI commands at all.

```bash
cku kpi agents                          # scored agents, names, severity counts
cku kpi tasks --limit 50                # the board
cku kpi show "<taskId>"                 # one card in full, incl. recommended fix
cku kpi history --agents <id,id>
```

Ids contain colons — **quote them** or the shell will misread them.

Every filter runs locally against the whole board, because the endpoint takes no
parameters. They combine with AND and the header reports `matching of total`, so
a narrow result cannot be mistaken for the whole board:

```bash
cku kpi tasks --severity "Very High,High" --column action_items
cku kpi tasks --agent "Retail" --since 7d --assigned none
cku kpi tasks --search "deal closure" --with-calls
```

**Severities are six, not four:** `Very High`, `High`, `Medium`, `Low`,
`Very Low`, `Negligible`. `--column` takes the id or the display label.

Read the **COLUMN** column in the output. `GET /pending-tasks` returns *every*
column, `done` and `rejected` included — a retired card is still returned, so a
card that is closed is not the same as a card that is gone. `--column action_items`
is the "still open" query; an unknown column is an error, never an empty result.

### Writing to the board

```bash
cku kpi create --cause "Agent did not greet" --fix "Add a greeting line" \
               --severity "Very High" --column action_items

cku kpi move "<taskId>" in_progress
cku kpi move "<taskId>" rejected        # this is how a card is retired

cku kpi comment "<taskId>" "Fixed in v3, shipping Thursday"
cku kpi set "<taskId>" --description "Longer context for the card"

cku kpi assignees                       # who a card can go to
cku kpi assign "<taskId>" --to "Poornesh"
cku kpi assign "<taskId>" --to ai_fde --agent <agentId> --versions <v1,v2>

cku kpi target --agent <id> --value 25  # KPI Manager target %
cku kpi rca --agent <id> --since 2026-09-01 --until 2026-09-30
```

**There is no delete.** Do not look for one and do not try to synthesise it. A
card is retired by moving it to `rejected`, which is reversible. If you need a
card gone from the board permanently, that is a dashboard-side action, not a CLI
one.

**Only `description` is editable after create.** `cause`, `--fix` and
`--severity` are fixed at creation — the board has no route to change them. To
correct one, create a replacement and move the original to `rejected`:

```bash
cku kpi create --cause "corrected cause" --fix "corrected fix" --severity Medium
cku kpi move "<oldTaskId>" rejected
```

`cku kpi target` reads the agent's current config and re-sends it, because the
server replaces the metric *and* the RCA prompt together. You do not need to
pass `--rca-prompt` to keep it, and you should not — a hand-written prompt will
be worse than the one already there.

Assigning to `ai_fde` requires **both** `--agent` and `--versions`; it queues
work that changes a real agent, so confirm the version ids first with
`cku agents versions <agentId>`. `--ab-split` and `--apply-to-published`
widen the blast radius further.

`cku kpi rca` starts a real RCA run over a date range. It is a write against
live agent configuration, not a dry run.

## Chat agents, audits, secrets

```bash
cku chat-agents list
cku chat-agents update <id> --set '{"name":"X"}'
cku audit-strategies list <agentId>
cku audit-strategies models
cku audit-strategies create <agentId> --strategy "Check for consent before ..."
cku secrets list
cku secrets set MY_KEY          # hidden prompt; --stdin to pipe
```

## JSON input: inline vs file

Two parsers, chosen by where the text came from:

- **Inline / argv** — lenient. PowerShell strips double quotes from
  single-quoted arguments, so `--set '{"name":"x"}'` arrives as `{name:x}`.
  The CLI puts the quotes back.
- **File or stdin** — strict. The shell never touched these, so a real typo is
  reported rather than guessed at.

**When a shell is involved, prefer the file form.** It is quote-proof on every
platform:

```bash
cku agents update <id> --set @patch.json
cku agents create --file agent.json
cku agents create < agent.json
```

BOMs are stripped automatically, so a file saved by Windows PowerShell is fine.

## Database-managed fields are rejected

`_id`, `__v`, `createdAt`, `updatedAt`, `userId`, `agentId` in any payload →
hard error. This is deliberate. `cku agents get --json` output includes them, so
do not feed it straight back into `create`. Use `cku agents export`, which is
already sanitised.

## Known gap: export output often fails import

```bash
cku agents export <id> --versions <v> --file a.json
cku agents import a.json --dry-run
```

`export` writes a bare agent object (an array for several versions), and
`import` reads that shape. But the backend's export response leaves out fields
that `import` requires. In a sweep of 109 versions, 95 were rejected, usually
for a mix of `language_switching_instructions`, `silence_instructions`,
`language_lockin_time`, `allowed_languages` and `language_switch_min_words`.
This is a backend gap, not a CLI one.

To round-trip, run `--dry-run`, add each field it names to the JSON, then
re-run. `null` is what the backend stores for an unset field (`[]` for
`allowed_languages`, `3` for `language_switch_min_words`), and
`cku agents get <id> --versions <v> --json` shows that version's real value:

```bash
cku agents get <id> --versions <v> --json > full.json   # has every field
```

Always `--dry-run` first: it validates without creating anything.

## Skill pack

```bash
cku skills install --claude        # this fork's pack
cku skills install --claude --official   # upstream pack
cku skills update                  # refresh every install
cku skills dir --claude            # where it landed
```

Targets: `--claude --cursor --copilot --gemini --windsurf --roo --opencode
--cline --codex --all`, plus `--project` to install into the repo instead of
your user account. Skills ship from GitHub, so a new skill reaches users
without a CLI release.

## Exit codes and errors

`0` success, `1` handled failure. Errors are written to be **acted on** — they
name the field, state what is allowed, and give the command to run next. Read
the message before retrying; retrying the same command will fail the same way.

Common ones:

| Message | Cause |
|---|---|
| `Invalid id: not a valid id` | invented or malformed id — run the `list` command |
| `Not logged in. Run \`cku login\`` | no session for the account in effect |
| `Run \`cku dashboard login\`` | dashboard command (`kpi`, `analyzers`, `models`) with no dashboard session — a *separate* sign-in from `cku login`, and it expires after 24h |
| `--versions is required to update version field(s)` | version-level field without a target |
| `Invalid value for "postcallmodel"` | that model is valid for `model` but not for post-call — the slots differ, see `cku models` |
| `contains database-managed field(s)` | round-tripping `get --json` output |
| `Unknown column "…"` | a `--column` value that is not one of the six board columns |
| `Forbidden: no permission` | the account lacks that capability — not a CLI bug |

## Reference

Full flag surface per command group: `REFERENCE.md`.

`cku <group> --help` for any group, `cku --help` for the list.

## Handbook step to command map

For agent engineering work (`callkaro-agent-design`, `callkaro-agent-review-debug`, `callkaro-qa-framework`), the steps map to these commands. Handbook steps with no CLI command are marked.

| Step | Command |
|---|---|
| Understand a version | `cku agents get <id>`, `cku agents export <id> --versions <v> --file a.json`, `cku agents versions <id>` |
| Valid models, voices, transcribers | `cku models --slot agent`, `cku voices --provider <p> --fields`, `cku transcribers --provider <p> --fields` |
| Write a new version | `cku agents create`, `cku agents clone-version`, then `cku agents update <id> --set @patch.json --versions <new>` |
| Publish | `cku agents publish <id> --versions <v>` (only when asked) |
| Read a call and its log | `cku calls get <id>`, `cku calls logs <id> "grep ..."` |
| Calls across a window | `cku calls list`, `cku calls export --start ...` |
| Create or run simulation cases | `cku sim create`, `cku sim run --wait`, `cku sim results` |
| Analytics | `cku analytics overview`, `performance`, `version <agentId>` |
| Search reference versions for a new build | no command yet (MCP-only) |
