#!/usr/bin/env node
"use strict";

/**
 * Any-PC short launcher — CLI shell by default (no web server).
 *
 *   npx -y --prefer-online angelsj913/Kx-Defender-
 *   npx -y --prefer-online angelsj913/Kx-Defender- kx /h
 *   npx -y --prefer-online angelsj913/Kx-Defender- serve
 */

const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");
const {
  installAgentSkills,
  listSkillDirs,
} = require("./install-agent-skills");
const {
  setupSync,
  ensureSetup,
  runKx,
  log,
  ROOT,
  isWin,
  SETUP_VERSION,
} = require("./npm-setup");
const { printKxBanner } = require("./banner");
const { startEdexShell } = require("./edex-shell");
const { startKxShell } = require("./kx-shell");

function printHelp() {
  printKxBanner();
  console.log(`Kx-Defender (eDEX HUD in PowerShell — no server by default)

PowerShell:
  npx -y --prefer-online angelsj913/Kx-Defender-
  irm https://raw.githubusercontent.com/angelsj913/Kx-Defender-/main/Install-Kx.ps1 | iex

HUD commands:
  /h
  lang ko | lang en
  roast tickets --scope lab --realm lab.local --sim
  exit

One-shot:
  npx -y --prefer-online angelsj913/Kx-Defender- kx /h

Optional:
  --serve     Web Console (eDEX-styled)
  --classic   Plain shell (no HUD panels)
  edex|hud    Force eDEX HUD
`);
}

function parseArgs(argv) {
  const flags = {
    all: false,
    global: false,
    project: false,
    serve: false,
    classic: false,
    bind: process.env.KX_BIND || "127.0.0.1:8787",
    help: false,
  };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") flags.all = true;
    else if (a === "-g" || a === "--global") flags.global = true;
    else if (a === "--project") flags.project = true;
    else if (a === "--serve" || a === "--console") flags.serve = true;
    else if (a === "--classic" || a === "--simple") flags.classic = true;
    else if (a === "--no-serve") flags.serve = false;
    else if (a === "--edex" || a === "--hud") {
      /* default */
    } else if (a === "-h" || a === "--help" || a === "/h") flags.help = true;
    else if (a === "--bind") flags.bind = argv[++i];
    else if (a.startsWith("--bind=")) flags.bind = a.slice("--bind=".length);
    else positional.push(a);
  }
  return { flags, positional };
}

function installUserShims() {
  const binDir = isWin()
    ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"), "Kx-Defender", "bin")
    : path.join(os.homedir(), ".local", "bin");
  fs.mkdirSync(binDir, { recursive: true });
  const entry = path.join(ROOT, "scripts", "npx-entry.js");
  const kxJs = path.join(ROOT, "scripts", "npm-kx.js");
  const shellJs = path.join(ROOT, "scripts", "kx-shell.js");

  if (isWin()) {
    fs.writeFileSync(path.join(binDir, "kx.cmd"), `@node "${kxJs}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-defender.cmd"), `@node "${entry}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-shell.cmd"), `@node "${shellJs}" %*\r\n`);
  } else {
    for (const [name, target] of [
      ["kx", kxJs],
      ["kx-defender", entry],
      ["kx-shell", shellJs],
    ]) {
      const dest = path.join(binDir, name);
      fs.writeFileSync(dest, `#!/bin/sh\nexec node ${JSON.stringify(target)} "$@"\n`, {
        mode: 0o755,
      });
      try {
        fs.chmodSync(dest, 0o755);
      } catch (_) {
        /* ignore */
      }
    }
  }
  log(`CLI shims: ${binDir}`);
  if (isWin()) {
    log(`This session: $env:PATH="$binDir;$env:PATH"`);
  } else {
    log(`Ensure ${binDir} is on PATH`);
  }
  return binDir;
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
  console.log(`[Kx] Starting Kx-Defender v${SETUP_VERSION} (CLI shell)...`);
  setupSync();
  installUserShims();
  if (flags.serve) {
    startServe(flags.bind);
    return;
  }
  // Classic plain shell: --classic ; default = eDEX HUD
  if (flags.classic) {
    startKxShell();
    return;
  }
  startEdexShell();
}

function main() {
  const { flags, positional } = parseArgs(process.argv.slice(2));
  if (flags.help && positional.length === 0) {
    printHelp();
    return;
  }

  const cmd = (positional[0] || "").toLowerCase();
  const rest = positional.slice(1);

  if (cmd === "add" && rest[0] && !rest[0].startsWith("-")) {
    rest.shift();
  }

  if (cmd === "kx") {
    ensureSetup();
    const res = runKx(rest.length ? rest : ["/h"]);
    process.exit(res.status == null ? 1 : res.status);
  }

  if (cmd === "shell" || cmd === "repl" || cmd === "cli") {
    setupSync();
    installUserShims();
    startKxShell();
    return;
  }

  if (cmd === "edex" || cmd === "hud") {
    setupSync();
    installUserShims();
    startEdexShell();
    return;
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
    installUserShims();
    log("Ready. Run: npx -y --prefer-online angelsj913/Kx-Defender-");
    log("Or: npx -y --prefer-online angelsj913/Kx-Defender- kx /h");
    return;
  }

  if (cmd === "help") {
    printHelp();
    return;
  }

  if (cmd === "add" || cmd === "init" || cmd === "install") {
    doSkillInstall(flags);
    return;
  }

  // Bare / --all / -g → CLI shell (not web server)
  if (!cmd || flags.all || flags.global || flags.serve) {
    runProgram(flags, { withSkills: Boolean(flags.all || flags.global) });
    return;
  }

  // Unknown verb → treat as one-shot KxLang: npx ... roast tickets ...
  ensureSetup();
  const res = runKx([cmd, ...rest]);
  process.exit(res.status == null ? 1 : res.status);
}

try {
  main();
} catch (err) {
  console.error(`[Kx] ${err.message || err}`);
  process.exit(err.status || 1);
}
