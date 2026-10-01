# CallKaro Skills

Small helpers for working with CallKaro AI. Each folder under `skills` covers one part of the platform, built from the public docs at docs.callkaro.ai.

I put these together after clicking through the dashboard and reading the docs end to end. They are meant for Claude Code and similar agents, but humans can read them too.

## What is inside

- `callkaro-voice-agents` for building voice agents, prompts, voices, transcribers, versions, functions, secrets, knowledge bases
- `callkaro-cli` for driving everything from the terminal with `cku`: agents, calls, numbers, batches, simulations, analytics, multi-account switching, and the dashboard-side KPI board (`cku kpi`) with its own separate sign-in
- `callkaro-chat-agents` for WhatsApp and Instagram chat agents
- `callkaro-calls-api` for outbound calls, campaigns, schedules, history
- `callkaro-webhooks` for realtime events like call ended and message status
- `callkaro-whatsapp` for number connect, templates, campaigns, inbox
- `callkaro-widget-integrations` for website widget and CRM links like HubSpot
- `callkaro-qa-ops` for audits, feedback, analytics, pricing, daily ops
- `callkaro-qa-grader` for grading QA test calls by fault layer and disposition
- `callkaro-prompt-style` for the plain-text house style: de-markdown, banners, SSML pauses, custom begin message, placeholder-safe rewrites
- `callkaro-conversational-voice` for making voice agents sound human: short turns, goals over scripts, example exchanges, rationed fillers, prompt size vs latency, Hinglish and multilingual switching, testing

## Install

### Claude Code plugin (recommended)

This repo is a Claude Code plugin marketplace. One plugin, eleven skills.

```
/plugin marketplace add TejasLamba2006/callkaro-skills
/plugin install callkaro-skills@callkaro
```

Restart Claude Code after install. Type `/` plus the skill name to confirm it shows up, e.g. `/callkaro-calls-api`. The plugin manifest lives in `.claude-plugin/` and lists all eleven skills, so updates come through `/plugin update`.

### npx skills CLI (any harness)

Works with Claude Code, Cursor, Codex, Windsurf, and other supported agents. Run in your project dir:

```bash
npx skills add TejasLamba2006/callkaro-skills
```

Variants:

```bash
npx skills add TejasLamba2006/callkaro-skills -g                             # global, all projects
npx skills add TejasLamba2006/callkaro-skills -s callkaro-calls-api -g    # one skill only
npx skills add TejasLamba2006/callkaro-skills --all                       # all skills, all agents, no prompts
```

Day to day:

```bash
npx skills list                                                           # what is installed
npx skills use TejasLamba2006/callkaro-skills@callkaro-calls-api          # try one without installing
npx skills update                                                         # pull latest
```

### Manual copy (any agent)

If your harness does not support plugins, copy the folders directly:

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

Update later with `git pull` in the clone and copy again.

### Other harnesses

- Codex / Cursor / Windsurf / generic agents: copy the `skills/` folder into your project (e.g. `./skills/` or `./.agent/skills/`) and point the agent at the matching `SKILL.md`. The files are plain markdown with curl and payload examples, no build step needed.
- Plugin style loaders: if your harness supports skill plugins, register each folder under `skills/` as one skill. Entry file is always `SKILL.md`.
- Manual use: open the skill file for your task and follow it. Example: to place a call, open `callkaro-calls-api` and use the outbound curl with your `X-API-KEY`.

## How to use

Pick the skill that matches your task. Each SKILL.md has the endpoints, payloads, and gotchas inline so you do not need to hunt through docs.

## Sources

All content comes from https://docs.callkaro.ai (132 pages, checked Sept 2026) plus a live pass over the dashboard. If docs and dashboard disagree, trust the dashboard and file it as a bug.

### Credits for `callkaro-conversational-voice`

The general voice-agent guidance in that skill is summarised from these articles and docs. Thanks to their authors:

- [LiveKit: Prompting voice agents to sound more realistic](https://livekit.com/blog/prompting-voice-agents-to-sound-more-realistic)
- [Vapi: Voice AI Prompting Guide](https://docs.vapi.ai/prompting-guide)
- [Ultravox: Prompting Guide](https://docs.ultravox.ai/gettingstarted/prompting)
- [Deepgram: Prompting Voice Agents](https://developers.deepgram.com/docs/prompting-voice-agents)
- [Deepgram: Backchannels vs Interruptions in Voice Agents](https://deepgram.com/learn/backchannels-vs-interruptions-voice-agents)
- [Deepgram: Hinglish Voice AI, why ASR fails and how to fix it](https://deepgram.com/learn/hinglish-voice-ai-speech-recognition)
- [CloudTalk: VoiceAgent Prompt Best Practices](https://help.cloudtalk.io/en/articles/11058815-voiceagent-prompt-best-practices)
- [Famulor: How to Write an AI Voice Agent System Prompt in 2026](https://www.famulor.io/blog/how-to-write-an-ai-voice-agent-system-prompt-in-2026)
- [Auto Interview AI: Handling Interruptions, Filler Words, and Latency](https://www.autointerviewai.com/blog/prompt-engineering-voice-ai-interruptions-latency-2026)
- [Retell AI: How Real-Time Voice AI Actually Works](https://www.retellai.com/blog/how-real-time-voice-ai-works-stt-llm-tts)
- [Dapta: Best AI Voice Agents in 2026](https://dapta.ai/blog-posts/best-ai-voice-agents/)
- [DEV Community: AI Voice Agent Prompt Engineering & Conversation Design](https://dev.to/moisi_trungu_31647b7ac300/ai-voice-agent-prompt-engineering-conversation-design-5fk3)
- [SquadStack: Can AI Voice Agents Handle Hinglish and Code Switching?](https://www.squadstack.ai/blog/can-ai-voice-agents-handle-hinglish-and-code-switching)
- [Rootle: Regional Language Mistakes Multilingual Voice AI Makes in India](https://rootle.ai/blog/multilingual-voice-ai-mistake/)

The CallKaro-specific findings (transcriber language list, switch threshold, `<Wait>` stripping, the account audit numbers) come from testing live agents on the platform, not from these sources. Several sources are vendor blogs, so read their product claims with that in mind; the general advice is consistent across them.

## Contribute

Found something stale. Open an issue or send a PR with the doc link and what changed. Keep it short.
