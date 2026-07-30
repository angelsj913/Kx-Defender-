#!/usr/bin/env node
"use strict";

/**
 * Any-PC short launcher (no npm publish required):
 *
 *   npx -y angelsj913/Kx-Defender-
 *   npx -y angelsj913/Kx-Defender- --all -g
 *
 * npm user/repo shorthand installs from GitHub; our CLI stays quiet
 * (no third-party `skills` CLI, no Eve/PromptScript noise).
 */

const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");
const {
  installAgentSkills,
  listSkillDirs,
} = require("./install-agent-skills");
const { setupSync, ensureSetup, runKx, log, ROOT, isWin, SETUP_VERSION } = require("./npm-setup");
const { printKxBanner } = require("./banner");

function printHelp() {
  printKxBanner();
  console.log(`Kx-Defender

PowerShell:
  irm https://raw.githubusercontent.com/angelsj913/Kx-Defender-/main/Install-Kx.ps1 | iex
  npx -y --prefer-online angelsj913/Kx-Defender-

Run:
  npx -y --prefer-online angelsj913/Kx-Defender-
  npx -y --prefer-online angelsj913/Kx-Defender- --all -g

Skills only:
  npx -y --prefer-online angelsj913/Kx-Defender- add --all -g

Other:
  npx -y --prefer-online angelsj913/Kx-Defender- setup
  npx -y --prefer-online angelsj913/Kx-Defender- serve [--bind host:port]
  npx -y --prefer-online angelsj913/Kx-Defender- kx <KxLang args...>

Flags:
  --all           Install all bundled agent skills
  -g, --global    User skill dirs + CLI shims
  --no-serve      Setup/skills only (do not start Console)
  --bind host:port   Console bind (default 127.0.0.1:8787)
`);
}

function parseArgs(argv) {
  const flags = {
    all: false,
    global: false,
    project: false,
    noServe: false,
    bind: process.env.KX_BIND || "127.0.0.1:8787",
    help: false,
  };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") flags.all = true;
    else if (a === "-g" || a === "--global") flags.global = true;
    else if (a === "--project") flags.project = true;
    else if (a === "--no-serve") flags.noServe = true;
    else if (a === "-h" || a === "--help" || a === "/h") flags.help = true;
    else if (a === "--bind") flags.bind = argv[++i];
    else if (a.startsWith("--bind=")) flags.bind = a.slice("--bind=".length);
    else positional.push(a);
  }
  return { flags, positional };
}

function installGlobalShims() {
  const userPrefix = path.join(os.homedir(), ".local");
  const attempts = [
    ["install", "-g", ROOT],
    ["install", "-g", "--force", "--prefix", userPrefix, ROOT],
  ];
  for (const args of attempts) {
    const res = spawnSync("npm", args, {
      cwd: ROOT,
      stdio: "ignore",
      shell: isWin(),
    });
    if (res.status === 0) return true;
  }
  try {
    const binDir = path.join(userPrefix, "bin");
    fs.mkdirSync(binDir, { recursive: true });
    const entry = path.join(ROOT, "scripts", "npx-entry.js");
    const kxJs = path.join(ROOT, "scripts", "npm-kx.js");
    for (const [name, target] of [
      ["kx-defender", entry],
      ["kx", kxJs],
    ]) {
      const dest = path.join(binDir, isWin() ? `${name}.cmd` : name);
      if (isWin()) fs.writeFileSync(dest, `@node "${target}" %*\r\n`);
      else {
        fs.writeFileSync(dest, `#!/bin/sh\nexec node ${JSON.stringify(target)} "$@"\n`, {
          mode: 0o755,
        });
        fs.chmodSync(dest, 0o755);
      }
    }
    return true;
  } catch {
    return false;
  }
}

function startServe(bind) {
  process.env.KX_BIND = bind;
  process.env.KX_OPEN = process.env.KX_OPEN || "1";
  require("./npm-start.js");
}

function doSkillInstall(flags) {
  const names = listSkillDirs();
  if (!names.length) {
    console.error("No bundled skills found.");
    process.exit(1);
  }
  const useGlobal = flags.project ? false : true;
  const result = installAgentSkills({ global: useGlobal });
  console.log(`Installed ${result.names.length} skills`);
  for (const name of result.names) console.log(`  ✓ ${name}`);
  for (const t of result.targets) console.log(`  → ${t}`);
  if (useGlobal && (flags.global || flags.all)) installGlobalShims();
  console.log("Done.");
}

function runProgram(flags, { withSkills = false } = {}) {
  printKxBanner();
  if (withSkills || flags.all || flags.global) {
    try {
      doSkillInstall(flags);
    } catch (err) {
      console.error(`[Kx] skill install skipped: ${err.message || err}`);
    }
  }
  console.log(`[Kx] Starting Kx-Defender v${SETUP_VERSION}...`);
  setupSync();
  if (flags.global) installGlobalShims();
  if (flags.noServe) {
    log("Ready. Try: npx -y --prefer-online angelsj913/Kx-Defender- kx /h");
    return;
  }
  startServe(flags.bind);
}

function main() {
  const { flags, positional } = parseArgs(process.argv.slice(2));
  if (flags.help && positional.length === 0) {
    printHelp();
    return;
  }

  const cmd = (positional[0] || "").toLowerCase();
  const rest = positional.slice(1);

  // Format-only token after `add` (never fetch a remote skill pack)
  if (cmd === "add" && rest[0] && !rest[0].startsWith("-")) {
    rest.shift();
  }

  if (cmd === "kx") {
    ensureSetup();
    const res = runKx(rest);
    process.exit(res.status == null ? 1 : res.status);
  }

  if (cmd === "serve") {
    ensureSetup();
    let bind = flags.bind;
    for (let i = 0; i < rest.length; i++) {
      if (rest[i] === "--bind" && rest[i + 1]) bind = rest[++i];
    }
    startServe(bind);
    return;
  }

  if (cmd === "setup") {
    setupSync();
    if (flags.global) installGlobalShims();
    log("Ready. Try: npx -y angelsj913/Kx-Defender- kx /h");
    return;
  }

  if (cmd === "help") {
    printHelp();
    return;
  }

  // Skills-only: add / install / init
  if (cmd === "add" || cmd === "init" || cmd === "install") {
    doSkillInstall(flags);
    return;
  }

  // Bare / --all / -g → run the program (any PC short command)
  if (!cmd || flags.all || flags.global) {
    runProgram(flags, { withSkills: Boolean(flags.all || flags.global) });
    return;
  }

  printHelp();
  process.exit(1);
}

try {
  main();
} catch (err) {
  console.error(`[Kx] ${err.message || err}`);
  process.exit(err.status || 1);
}
