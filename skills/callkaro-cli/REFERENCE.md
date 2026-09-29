# cku — flag reference

Generated from the CLI's own `--help` output. Do not hand-edit: regenerate with

```bash
node scripts/gen-cli-reference.js
```

Start at [SKILL.md](./SKILL.md) — it has the decision rules and the traps. This file is
the exhaustive flag list.

## Global

```
-v, --version   show version
-h, --help      show help
```

## `cku accounts`

Subcommands: `list` `use` `bind` `unbind` `status` `remove`

## `cku agents`

Subcommands: `list` `get` `versions` `export` `import` `create` `update` `set-inbound` `set-outbound` `clone-version` `publish` `toggle-active` `ab` `ab-advanced`

## `cku analytics`

Subcommands: `overview` `performance` `version`

## `cku batches`

Subcommands: `create` `schedule` `list` `get` `status` `send-next-try` `send-untriggered` `download`

## `cku calls`

Subcommands: `make` `list` `get` `logs` `export`

## `cku chat-agents`

Subcommands: `models` `templates` `template` `list` `get` `versions` `create` `update` `create-version` `publish`

## `cku numbers`

Subcommands: `list` `catalog` `buy` `spam` `unspam` `release`

## `cku ongoing`

Subcommands: `status` `pause` `resume` `clear`

## `cku secrets`

Subcommands: `list` `set` `remove` `rename`

## `cku sim`

Subcommands: `tests` `create` `delete` `run` `runs` `results`

## `cku skills`

Subcommands: `install` `update` `dir`

## `cku audit-strategies`

Subcommands: `list` `get` `filter-options` `models` `create` `update`

## `cku voices`

```
Options:
  --provider <p>                filter by an account-available provider
  --model <m>                   filter by voice model (e.g. sonic-3, bulbul:v3,
                                aura-2)
  --language <l>                filter by language (e.g. hi, en, hi-IN)
  --gender <g>                  provider-specific gender (e.g. female or
                                feminine)
  --query <text>                search provider voice names and descriptions
  --voice-id <id>               filter by provider-native voice id
  --voice-name <name>           filter by provider-native voice name
  --style <style>               filter by voice style
  --locale <locale>             filter by provider locale
  --languages <list>            languages, comma-separated
  --accent <accent>             filter by accent
  --use-cases <list>            use cases, comma-separated
  --category <category>         filter by provider category
  --voice-type <type>           filter by voice ownership/type
  --high-quality                only high-quality voices
  --voice-ids <list>            voice ids, comma-separated
  --collection-id <id>          filter by collection id
  --sort <field>                provider sort field
  --sort-direction <direction>  sort direction: asc | desc
  --is-owner                    only voices owned by the account
  --include-archived            include archived voices
  --type <type>                 provider-specific voice type
  --project-id <id>             filter by project id
  --id <id>                     filter by provider-native id
  --limit <n>                   maximum voices to return
  --providers                   list providers and their models instead of
                                voices
  --fields                      show the voice_configuration keys a provider
                                takes (needs --provider)
  --json                        raw JSON
```

## `cku transcribers`

```
Options:
  --provider <p>  filter: soniox | deepgram | sarvam | azure | elevenlabs |
                  groq | cartesia | gnani | callkaro
  --language <l>  filter by language (e.g. hi, en, hi-IN)
  --fields        show the transcriber keys a provider takes (needs --provider)
  --all           include admin-gated providers
  --json          raw JSON
```

## `cku config`

## `cku login`

```
Options:
  --password       use the classic email + password prompt instead
  --email <email>  email address (with --password)
```

## `cku logout`

## `cku whoami`

```
Options:
  --json      output raw JSON
```

## `cku register`

```
Options:
  --google         sign up with Google in your browser (skips the picker)
  --email <email>  email address
  --name <name>    your name
```

## `cku update`

```
Options:
  --skip-skills  update the CLI only
```
