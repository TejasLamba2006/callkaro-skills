---
name: callkaro-mcp
description: Use the CallKaro remote MCP server (mcp.callkaro.ai) and decide between it and the cku CLI. Use when an MCP tool named like get_agent, update_agent, inspect_agent_version, search_reference_versions or make_call is available, when the user asks to install, connect or set up the CallKaro MCP in Claude Code, Codex, Cursor or VS Code, or when choosing MCP vs CLI for a CallKaro task. Covers which tool to reach for, the account-mismatch trap, safe agent edits, and one-command setup.
---

# CallKaro MCP

Remote MCP server, Streamable HTTP, OAuth 2.1, no local install.

```
https://mcp.callkaro.ai/api/mcp
```

It sits on the same backend as the CLI and covers the same areas: agents and versions, calls, batches, simulations, numbers, secrets (read only), analytics, audit strategies, chat agents. Tool names get the server name as a prefix, e.g. `mcp__callkaro__get_agent`. The name is whatever the client registered (`callkaro`, `callkaro-probe`), so match on the tail.

## Pick the tool: MCP or CLI

Default: **use whichever is already connected, and prefer the CLI for anything that writes an object or array field.** Then apply this table.

| Task | Use | Why |
|---|---|---|
| Designing a new agent from scratch | MCP | `search_reference_versions` and the `get_agent_*_reference` tools have no CLI equivalent |
| Understanding one big version | MCP | `inspect_agent_version` returns one section at a time (script, functions, pathway graph, post-call). CLI `agents get` returns it all |
| Looking up the authoring rules | MCP | ten `get_agent_*_reference` tools, one per topic (script, functions, post-call, LLM, STT, TTS, settings, translation, creation) |
| Editing `voice_configuration`, `transcriber`, `functions`, `customPronunciations`, `preFormatVariables` | CLI | `cku agents update` merges these against the target version in code. The MCP expects you to send the complete object |
| Any scripted, piped or repeated job | CLI | `--json`, `--wait`, exit codes, no model in the loop |
| Placing a test call | either | needs fresh user approval each time, on both |
| Reading a call and its log | either | `get_call` + `query_call_logs` vs `cku calls get` + `cku calls logs` (same virtual `/call.log`) |
| Running simulations | either | MCP can also step one turn at a time with `generate_simulation_reply`; CLI has `sim run --wait` |
| Batch retries and receipts | MCP | `get_batch_receipts`, `get_not_connected_batch_calls`, `retry_not_connected_batch_calls` |
| KPI board, call analyzers, saved sim variable sets, any dashboard route | CLI only | needs the dashboard cookie, see `callkaro-cli` |
| `ongoing pause/resume/clear`, `agents export/import`, `monitor`, per-folder accounts | CLI only | no MCP tool (the MCP only has `get_queue_status`) |
| A/B routing | either | MCP sets `abTestEnabled`, `abTestVersions`, `advancedAbTestRules` through `update_agent`. Same whole-object caution as below |
| Secrets | CLI to write; MCP can list, rename, remove | MCP `set_secret` only points the user to the dashboard and takes no value, on purpose |
| Billing credits | MCP | `get_account_credit_status`, if the account has billing access |
| Working from Claude web or desktop with no terminal | MCP | nothing to install |

If a task lands in the "CLI only" rows and no terminal is available, say so. Do not improvise through raw REST.

## Rules that stop real damage

1. **Check which account the MCP is signed in as before any write.** The MCP login is an OAuth session, separate from `.cku.json` and `cku login`. Call `get_account_details`, and if the CLI is present compare with `cku whoami`. Two different accounts means the CLI and MCP are editing different workspaces. Stop and tell the user.
2. **Never edit a live agent without an explicit go-ahead.** `update_agent`, `publish_agent`, `toggle_agent_version`, `update_chat_agent`, `publish_chat_agent_version`, `update_number_spam_status` and `release_phone_number` change shared state. A forwarded bug report means diagnose and propose.
3. **Inspect before update.** Run `inspect_agent_version` with `interface_index` plus every section you will touch, with `fullText` and `includeSourceCode` for anything you rewrite. Previews are not enough to modify.
4. **Send only changed fields, and keep whole objects whole.** The MCP's own guidance is "preserve unrelated complete objects", and for `customPronunciations` and `preFormatVariables` "send the complete desired map". Whether the backend merges a partial object has not been verified. Treat a partial `voice_configuration` or `functions` array as destructive. Read the current value, edit it, send the whole thing, then `inspect_agent_version` again to confirm nothing else moved.
5. **Version-level changes need a `versionId`.** Without it the backend rejects the update.
6. **Test calls need fresh approval every time.** `make_call` and `create_batch` or `schedule_batch` start real calls. Simulations (`create_simulation_run`) are fine without asking.
7. **Never invent ids.** Agent, version, number, voice, model and template ids come from a list or inspect call. The MCP says this in every reference tool.
8. **No secrets in chat.** Do not paste a client secret or token into an MCP argument. Point the user to the dashboard vault.
9. **`list_agents` is not paginated** and can return tens of KB. Pipe or truncate before reading, or use the CLI with `--json` and a filter.

## Common flows

**New agent.** `search_reference_versions` (never for translation) → `inspect_agent_version` on the best matches → `get_agent_script_reference` and whichever other reference covers the fields → draft → `create_agent` → `create_test_case` + `create_simulation_run` → report. Publish only on request. House method for the design itself: `callkaro-agent-design`.

**Translate a version.** `get_agent_translation_reference` → `inspect_agent_version` on the source, complete → `clone_agent_version` with the target language, voice and transcriber (`list_voice_providers`, `get_voice_provider_metadata`, `list_transcribers`) → `update_agent` the clone's spoken text only. Never `search_reference_versions` here.

**Debug a bad call.** `get_call` → `query_call_logs` (`grep -E ' - (ERROR|WARNING) - ' /call.log`) → `inspect_agent_version` on the version that ran → fix at the right layer. Method: `callkaro-agent-review-debug`.

**Failed batch rows.** `get_batch_status` → `get_not_connected_batch_calls` → `retry_not_connected_batch_calls` with the `maxTryCount` the status reports.

## Install and auto-setup

Setup registers the URL once per client, then the user signs in once in a browser. **An agent cannot complete the OAuth step.** It has no browser callback, so do the registration and hand the login to the user.

### One command

From this skill's folder (or wherever it was installed):

```bash
node scripts/setup-mcp.js                 # every supported client it finds on this machine
node scripts/setup-mcp.js --dry-run       # print what it would do, change nothing
node scripts/setup-mcp.js --client claude --scope user
node scripts/setup-mcp.js --client codex|cursor|vscode|all
```

Idempotent: re-running reports `present`. It never reads or writes credentials. It exits 1 if no client is found or a registration fails, and prints the manual command.

Skill installed through `cku skills install`? The script sits under that client's skills directory (`cku skills dir --claude` shows where).

### What it runs, per client

| Client | Registration | Then |
|---|---|---|
| Claude Code | `claude mcp add --transport http --scope user callkaro https://mcp.callkaro.ai/api/mcp` | `claude mcp login callkaro`, or `/mcp` inside Claude Code. Restart after sign-in so the tools load |
| Codex | `codex mcp add callkaro --url https://mcp.callkaro.ai/api/mcp` | `codex mcp login callkaro` |
| Cursor | merges `{"mcpServers":{"callkaro":{"url":"…"}}}` into `~/.cursor/mcp.json` | Settings → Tools & MCP → enable, sign in |
| VS Code | merges `{"servers":{"callkaro":{"type":"http","url":"…"}}}` into `.vscode/mcp.json` | Command Palette: `MCP: List Servers` → start, sign in |
| Claude web or desktop | Settings → Connectors → Add custom connector, name `CallKaro`, paste the URL, leave client credentials empty | sign in when prompted |
| Anything else | find the MCP or integrations screen, add a remote Streamable HTTP server with the URL | sign in when prompted |

`--scope` for Claude Code: `user` (every project, default here), `local` (this project, private), `project` (writes `.mcp.json`, shared with the repo).

### Sign-in without a desktop browser

```bash
claude mcp login callkaro --no-browser   # prints a URL; open it anywhere, paste the redirect URL back
```

In a Claude Code session the user can type `! claude mcp login callkaro` so it runs with a terminal. An agent cannot.

### Verify

1. `claude mcp list` shows `callkaro` as connected, or "Needs authentication" if the login is not done.
2. Call `get_account_details`. It returns the name and email the MCP is acting as. Compare with `cku whoami`.
3. A 401 with `invalid_token` before login is expected: the server rejects even `initialize` without OAuth.

### Remove

```bash
claude mcp remove callkaro
codex mcp remove callkaro
```

For Cursor and VS Code delete the `callkaro` key from the JSON file.

## Do not

- Do not probe `https://mcp.callkaro.ai/api/mcp` with curl and a CLI token. It accepts OAuth tokens only.
- Do not claim a CLI-only feature exists in the MCP, or the reverse. The table above is the checked list; re-check it against the live tool list, because the server is v1 and moves.
- Do not leave the MCP and CLI on different accounts without telling the user.

Related skills: `callkaro-cli` (the terminal tool), `callkaro-agent-design`, `callkaro-agent-review-debug`, `callkaro-qa-framework`, `callkaro-functions`.
