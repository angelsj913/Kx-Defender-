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
  console.log(`Kx-Defender (eDEX HUD in PowerShell)

PowerShell:
  kx                          # start Kx-Defender (HUD)
  npx -y --prefer-online angelsj913/Kx-Defender-
  login kx                    # re-enter after Ctrl+C / exit
  [login kx]                  # same

HUD:
  Ctrl+C           lock session → type [login kx]
  update           pull latest without full reinstall
  /h | lang ko|en | exit

One-shot:
  kx /h
  kx roast tickets --scope lab --sim
  npx -y --prefer-online angelsj913/Kx-Defender- update

Optional:
  --serve     Web Console
  --classic   Plain shell
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

function preferPersistentApp() {
  if (process.env.KX_FROM_APP === "1" || process.env.KX_DEV === "1") return false;
  // Local git clone: stay on the working tree (avoid surprising redirects)
  if (fs.existsSync(path.join(ROOT, ".git"))) return false;
  try {
    const { getAppRoot } = require("./kx-update");
    const app = getAppRoot();
    if (!app || path.resolve(app) === path.resolve(ROOT)) return false;
    const entry = path.join(app, "scripts", "npx-entry.js");
    if (!fs.existsSync(entry)) return false;
    const res = spawnSync(process.execPath, [entry, ...process.argv.slice(2)], {
      stdio: "inherit",
      env: { ...process.env, KX_FROM_APP: "1" },
      windowsHide: true,
    });
    process.exit(res.status == null ? 0 : res.status);
    return true;
  } catch (_) {
    return false;
  }
}

function installUserShims() {
  try {
    const { ensurePersistentInstall } = require("./kx-update");
    ensurePersistentInstall(ROOT);
  } catch (_) {
    /* ignore */
  }
  const binDir = isWin()
    ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"), "Kx-Defender", "bin")
    : path.join(os.homedir(), ".local", "bin");
  fs.mkdirSync(binDir, { recursive: true });
  let root = ROOT;
  try {
    const { getAppRoot } = require("./kx-update");
    const app = getAppRoot();
    if (app) root = app;
  } catch (_) {
    /* ignore */
  }
  const entry = path.join(root, "scripts", "npx-entry.js");
  const kxJs = path.join(root, "scripts", "npm-kx.js");
  const shellJs = path.join(root, "scripts", "kx-shell.js");
  const updateJs = path.join(root, "scripts", "kx-update.js");

  if (isWin()) {
    fs.writeFileSync(path.join(binDir, "kx.cmd"), `@node "${kxJs}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-defender.cmd"), `@node "${entry}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-shell.cmd"), `@node "${shellJs}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "login-kx.cmd"), `@node "${entry}" login kx %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-update.cmd"), `@node "${updateJs}" %*\r\n`);
  } else {
    for (const [name, target, prefix] of [
      ["kx", kxJs, ""],
      ["kx-defender", entry, ""],
      ["kx-shell", shellJs, ""],
      ["login-kx", entry, "login kx "],
      ["kx-update", updateJs, ""],
    ]) {
      const dest = path.join(binDir, name);
      fs.writeFileSync(
        dest,
        `#!/bin/sh\nexec node ${JSON.stringify(target)} ${prefix}"$@"\n`,
        { mode: 0o755 }
      );
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

function isLoginCommand(cmd, rest) {
  const joined = [cmd, ...rest]
    .join(" ")
    .toLowerCase()
    .replace(/[\[\]]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (/^login\s*kx$/.test(joined) || joined === "login-kx" || joined === "loginkx") return true;
  if (cmd === "login" || cmd === "login-kx" || cmd === "loginkx" || cmd === "[login") return true;
  if (/^\[?login\s+kx\]?$/.test(String(cmd || "").toLowerCase().replace(/\s+/g, " ").trim())) return true;
  return false;
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
  // After `update`, prefer ~/.kx-defender/app so npx cache is not required
  preferPersistentApp();

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
    // Bare: kx → already handled; here positional was "kx" with rest
    if (rest.length === 0) {
      runProgram(flags);
      return;
    }
    if ((rest[0] || "").toLowerCase() === "update" || (rest[0] || "").toLowerCase() === "upgrade") {
      require("./kx-update").updateKx();
      return;
    }
    if ((rest[0] || "").toLowerCase() === "login") {
      setupSync();
      installUserShims();
      startEdexShell();
      return;
    }
    ensureSetup();
    const res = runKx(rest.length ? rest : ["/h"]);
    process.exit(res.status == null ? 1 : res.status);
  }

  if (cmd === "update" || cmd === "upgrade") {
    require("./kx-update").updateKx();
    return;
  }

  // login / [login kx] / login-kx → start HUD (re-entry)
  if (isLoginCommand(cmd, rest)) {
    setupSync();
    installUserShims();
    startEdexShell();
    return;
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
