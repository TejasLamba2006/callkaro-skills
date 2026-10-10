#!/usr/bin/env node
// Registers the CallKaro remote MCP server in the AI clients found on this machine.
// Idempotent. Never handles credentials: sign-in is OAuth in a browser and cannot be scripted.
//   node setup-mcp.js [--client claude|codex|cursor|vscode|all] [--scope user|local|project] [--dry-run]
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const NAME = 'callkaro';
const URL = 'https://mcp.callkaro.ai/api/mcp';

const args = process.argv.slice(2);
const flag = (n, d) => { const i = args.indexOf(`--${n}`); return i >= 0 ? args[i + 1] : d; };
const dry = args.includes('--dry-run');
const want = flag('client', 'auto');
const scope = flag('scope', 'user');

function has(cmd) {
  return spawnSync(cmd, ['--version'], { shell: process.platform === 'win32', stdio: 'ignore' }).status === 0;
}

function run(cmd, cmdArgs) {
  console.log(`  $ ${cmd} ${cmdArgs.join(' ')}`);
  if (dry) return 'dry';
  const r = spawnSync(cmd, cmdArgs, { shell: process.platform === 'win32', encoding: 'utf8' });
  const text = `${r.stdout || ''}${r.stderr || ''}`;
  if (r.status === 0) return 'added';
  if (/already exists|already configured/i.test(text)) return 'present';
  console.log(text.trim().split('\n').map((l) => '    ' + l).join('\n'));
  return 'failed';
}

function mergeJson(file, key, entry) {
  let cfg = {};
  if (fs.existsSync(file)) {
    try { cfg = JSON.parse(fs.readFileSync(file, 'utf8')); }
    catch { console.log(`  ${file} is not strict JSON (comments?). Add the entry by hand:\n  ${JSON.stringify({ [key]: { [NAME]: entry } })}`); return 'failed'; }
  }
  if (cfg[key]?.[NAME]) return 'present';
  if (dry) { console.log(`  would write ${file}`); return 'dry'; }
  cfg[key] = { ...cfg[key], [NAME]: entry };
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(cfg, null, 2) + '\n');
  console.log(`  wrote ${file}`);
  return 'added';
}

const clients = {
  claude: { detect: () => has('claude'), next: `claude mcp login ${NAME}   (or /mcp inside Claude Code, then restart)`,
    setup: () => run('claude', ['mcp', 'add', '--transport', 'http', '--scope', scope, NAME, URL]) },
  codex: { detect: () => has('codex'), next: `codex mcp login ${NAME}`,
    setup: () => run('codex', ['mcp', 'add', NAME, '--url', URL]) },
  cursor: { detect: () => fs.existsSync(path.join(os.homedir(), '.cursor')), next: 'Cursor Settings > Tools & MCP: enable callkaro, sign in when prompted',
    setup: () => mergeJson(path.join(os.homedir(), '.cursor', 'mcp.json'), 'mcpServers', { url: URL }) },
  vscode: { detect: () => fs.existsSync(path.join(process.cwd(), '.vscode')), next: 'MCP: List Servers > callkaro > Start, sign in when prompted',
    setup: () => mergeJson(path.join(process.cwd(), '.vscode', 'mcp.json'), 'servers', { type: 'http', url: URL }) },
};

const targets = want === 'all' ? Object.keys(clients)
  : want === 'auto' ? Object.keys(clients).filter((k) => clients[k].detect())
  : [want];

if (!targets.length) { console.log('No supported client detected. Re-run with --client claude|codex|cursor|vscode.'); process.exit(1); }
if (targets.some((t) => !clients[t])) { console.log(`Unknown client. Use one of: ${Object.keys(clients).join(', ')}, all.`); process.exit(1); }

let failed = false;
for (const t of targets) {
  console.log(`${t}:`);
  const res = clients[t].setup();
  failed ||= res === 'failed';
  console.log(`  ${res}. Next: ${clients[t].next}`);
}
console.log('\nSign-in is OAuth in a browser; this script cannot do it. Restart the client after signing in so the tools load.');
process.exit(failed ? 1 : 0);
