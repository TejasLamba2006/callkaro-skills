# CallKaro Skills

Small helpers for working with CallKaro AI. Each folder under `skills` covers one part of the platform, built from the public docs at docs.callkaro.ai.

I put these together after clicking through the dashboard and reading the docs end to end. They are meant for Claude Code and similar agents, but humans can read them too.

## What is inside

- `callkaro-voice-agents` for building voice agents, prompts, voices, transcribers, versions, functions, secrets, knowledge bases
- `callkaro-chat-agents` for WhatsApp and Instagram chat agents
- `callkaro-calls-api` for outbound calls, campaigns, schedules, history
- `callkaro-webhooks` for realtime events like call ended and message status
- `callkaro-whatsapp` for number connect, templates, campaigns, inbox
- `callkaro-widget-integrations` for website widget and CRM links like HubSpot
- `callkaro-qa-ops` for audits, feedback, analytics, pricing, daily ops

## Install

### Claude Code

Pick one scope:

```bash
# user scope, works in every project
git clone https://github.com/TejasLamba2006/callkaro-skills.git /tmp/callkaro-skills
mkdir -p ~/.claude/skills
cp -r /tmp/callkaro-skills/skills/* ~/.claude/skills/
```

```bash
# project scope, checked into your repo
mkdir -p .claude/skills
cp -r /path/to/callkaro-skills/skills/* .claude/skills/
```

Restart Claude Code after copying. Type `/` plus the skill name to confirm it shows up, e.g. `/callkaro-calls-api`. Claude Code reads `SKILL.md` frontmatter (`name`, `description`) to auto trigger, so keep folder names and files as is.

Update later with `git pull` in the clone and copy again.

### Other harnesses

- Codex / Cursor / Windsurf / generic agents: copy the `skills/` folder into your project (e.g. `./skills/` or `./.agent/skills/`) and point the agent at the matching `SKILL.md`. The files are plain markdown with curl and payload examples, no build step needed.
- Plugin style loaders: if your harness supports skill plugins, register each folder under `skills/` as one skill. Entry file is always `SKILL.md`.
- Manual use: open the skill file for your task and follow it. Example: to place a call, open `callkaro-calls-api` and use the outbound curl with your `X-API-KEY`.

## How to use

Pick the skill that matches your task. Each SKILL.md has the endpoints, payloads, and gotchas inline so you do not need to hunt through docs.

## Sources

All content comes from https://docs.callkaro.ai (132 pages, checked Sept 2026) plus a live pass over the dashboard. If docs and dashboard disagree, trust the dashboard and file it as a bug.

## Contribute

Found something stale. Open an issue or send a PR with the doc link and what changed. Keep it short.
