#!/usr/bin/env node
"use strict";

/**
 * Native Operator Client launcher (no web UI).
 *
 *   npx -y --prefer-online angelsj913/Kx-Defender-
 *   kx
 *   kx /h
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
  console.log(`Kx DEFCOM — native Operator Client (PowerShell / terminal)

  kx                              start client
  npx -y --prefer-online angelsj913/Kx-Defender-

Client:
  Ctrl+C     lock · type kx to resume
  update     refresh without reinstall
  /h         help · exit

One-shot:
  kx /h
  kx roast tickets --scope lab --sim
  kx update

Optional:
  --classic  plain shell
`);
}

function parseArgs(argv) {
  const flags = {
    all: false,
    global: false,
    project: false,
    classic: false,
    help: false,
  };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") flags.all = true;
    else if (a === "-g" || a === "--global") flags.global = true;
    else if (a === "--project") flags.project = true;
    else if (a === "--classic" || a === "--simple") flags.classic = true;
    else if (a === "--serve" || a === "--console" || a === "--no-serve") {
      console.error("[Kx] web console removed — use: kx");
    } else if (a === "--edex" || a === "--hud" || a === "--client") {
      /* default client */
    } else if (a === "-h" || a === "--help" || a === "/h") flags.help = true;
    else if (a === "--bind" || a.startsWith("--bind=")) {
      console.error("[Kx] web console removed — --bind ignored");
      if (a === "--bind") i++;
    } else positional.push(a);
  }
  return { flags, positional };
}

function readPkgVersion(root) {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
    return String(pkg.version || "0.0.0");
  } catch (_) {
    return "0.0.0";
  }
}

function cmpSemver(a, b) {
  const pa = String(a).split(".").map((x) => parseInt(x, 10) || 0);
  const pb = String(b).split(".").map((x) => parseInt(x, 10) || 0);
  const n = Math.max(pa.length, pb.length);
  for (let i = 0; i < n; i++) {
    const d = (pa[i] || 0) - (pb[i] || 0);
    if (d) return d > 0 ? 1 : -1;
  }
  return 0;
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
    const hasUpdater = fs.existsSync(path.join(app, "scripts", "kx-update.js"));
    // Stale persistent app without updater — stay on this (npx) package
    if (!hasUpdater) return false;
    if (!fs.existsSync(entry)) return false;
    // Never redirect to an older persistent app (fixes "same reply" from stale trees)
    const here = readPkgVersion(ROOT);
    const there = readPkgVersion(app);
    if (cmpSemver(there, here) < 0) return false;
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
  const edexJs = path.join(root, "scripts", "kx-client.js");
  const updateJs = path.join(root, "scripts", "kx-update.js");

  if (isWin()) {
    fs.writeFileSync(path.join(binDir, "kx.cmd"), `@node "${kxJs}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-defender.cmd"), `@node "${entry}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-client.cmd"), `@node "${edexJs}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-shell.cmd"), `@node "${shellJs}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "login-kx.cmd"), `@node "${entry}" login kx %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-update.cmd"), `@node "${updateJs}" %*\r\n`);
  } else {
    for (const [name, target, prefix] of [
      ["kx", kxJs, ""],
      ["kx-defender", entry, ""],
      ["kx-client", edexJs, ""],
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

function containsKx(text) {
  return /kx/i.test(String(text || ""));
}

function isLoginCommand(cmd, rest) {
  const joined = [cmd, ...rest].join(" ");
  // Any argv that mentions kx (login kx, [login kx], loginkx, …) enters the program
  // unless it is clearly a one-shot KxLang call handled elsewhere (cmd === "kx" + verb).
  if (!containsKx(joined) && !containsKx(cmd)) return false;
  const norm = joined
    .toLowerCase()
    .replace(/[\[\]]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  // One-shot: kx <verb> … → not a login
  if (/^kx\s+\S+/.test(norm) && !/^kx\s+(login|hud|shell|edex|repl|cli)\b/.test(norm)) {
    return false;
  }
  return true;
}

function startServe(_bind) {
  console.error("[Kx] web console removed. Start the native client: kx");
  process.exit(2);
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
  console.log(`[Kx] Starting DEFCOM Operator Client v${SETUP_VERSION}...`);
  setupSync();
  installUserShims();
  if (flags.classic) {
    startKxShell();
    return;
  }
  startEdexShell();
}

function isUpdateArgv(argv) {
  const a = (argv || []).map((x) => String(x).toLowerCase());
  if (!a.length) return false;
  if (a[0] === "update" || a[0] === "upgrade") return true;
  if (a[0] === "kx" && (a[1] === "update" || a[1] === "upgrade")) return true;
  return false;
}

function main() {
  const rawArgv = process.argv.slice(2);

  // CRITICAL: handle update from THIS package before redirecting to
  // ~/.kx-defender/app (which may be an older install without updater).
  if (isUpdateArgv(rawArgv)) {
    try {
      require("./kx-update").updateKx();
    } catch (err) {
      console.error(`[Kx] ${err.message || err}`);
      process.exit(err.status || 1);
    }
    return;
  }

  // After `update`, prefer ~/.kx-defender/app so npx cache is not required
  preferPersistentApp();

  const { flags, positional } = parseArgs(rawArgv);
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

  if (cmd === "serve" || cmd === "console") {
    startServe();
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

  // Bare / --all / -g → native client
  if (!cmd || flags.all || flags.global) {
    runProgram(flags, { withSkills: Boolean(flags.all || flags.global) });
    return;
  }

  // One-shot KxLang only — never steal into the client (PRD RC2)
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
