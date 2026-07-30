#!/usr/bin/env node
"use strict";

/**
 * npx entry — skills-CLI style one-liner UX
 *
 * Shape (same as common skill CLIs; names are format only):
 *   npx --yes <pkg> add <name> --all -g
 *
 * Kx-Defender:
 *   npx --yes github:angelsj913/Kx-Defender- --all -g
 *   npx --yes github:angelsj913/Kx-Defender- add . --all -g
 *
 * Never downloads third-party skill repos (e.g. NomaDamas/k-skill).
 */

const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");
const { setup, ensureSetup, runKx, log, ROOT, isWin } = require("./npm-setup");

function printHelp() {
  console.log(`Kx-Defender (npx)

One-liner (skills-CLI style):
  npx --yes github:angelsj913/Kx-Defender- --all -g
  npx --yes github:angelsj913/Kx-Defender- add . --all -g

Other:
  npx --yes github:angelsj913/Kx-Defender- setup [--all] [-g|--global]
  npx --yes github:angelsj913/Kx-Defender- serve [--bind host:port]
  npx --yes github:angelsj913/Kx-Defender- kx <KxLang args...>

Flags:
  --all           Full setup (Python env + package + verify)
  -g, --global    Install CLI shims globally (kx, kx-defender)
  --no-serve      Setup only (do not start Console)
  --bind host:port   Console bind (default 127.0.0.1:8787)

Self-Built Only: installs this repo only — never fetches external skill packs.
`);
}

function parseArgs(argv) {
  const flags = {
    all: false,
    global: false,
    noServe: false,
    bind: process.env.KX_BIND || "127.0.0.1:8787",
    help: false,
  };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") flags.all = true;
    else if (a === "-g" || a === "--global") flags.global = true;
    else if (a === "--no-serve") flags.noServe = true;
    else if (a === "-h" || a === "--help" || a === "/h") flags.help = true;
    else if (a === "--bind") {
      flags.bind = argv[++i];
    } else if (a.startsWith("--bind=")) {
      flags.bind = a.slice("--bind=".length);
    } else {
      positional.push(a);
    }
  }
  return { flags, positional };
}

function installGlobal() {
  log("Installing global CLI shims (-g) ...");
  const userPrefix = path.join(os.homedir(), ".local");
  const attempts = [
    ["install", "-g", ROOT],
    ["install", "-g", "--prefix", userPrefix, ROOT],
  ];
  for (const args of attempts) {
    const res = spawnSync("npm", args, {
      cwd: ROOT,
      stdio: "inherit",
      shell: isWin(),
    });
    if (res.status === 0) {
      log("Global shims ready: kx-defender, kx");
      if (args.includes("--prefix")) {
        log("Ensure ~/.local/bin is on PATH");
      }
      return true;
    }
  }
  // Last resort: user-local shim scripts (no root)
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
      if (isWin()) {
        fs.writeFileSync(dest, `@node "${target}" %*\r\n`);
      } else {
        fs.writeFileSync(
          dest,
          `#!/bin/sh\nexec node ${JSON.stringify(target)} "$@"\n`,
          { mode: 0o755 }
        );
        fs.chmodSync(dest, 0o755);
      }
    }
    log(`User shims written to ${binDir} (add to PATH if needed)`);
    return true;
  } catch (err) {
    log(`Global install failed (${err.message}) — use npx locally.`);
    return false;
  }
}

function startServe(bind) {
  process.env.KX_BIND = bind;
  process.env.KX_OPEN = process.env.KX_OPEN || "1";
  require("./npm-start.js");
}

function main() {
  const { flags, positional } = parseArgs(process.argv.slice(2));
  if (flags.help && positional.length === 0) {
    printHelp();
    return;
  }

  const cmd = (positional[0] || "").toLowerCase();
  const rest = positional.slice(1);

  // Default / add / setup → full bootstrap (skills-CLI style)
  const isBootstrap =
    !cmd ||
    cmd === "add" ||
    cmd === "setup" ||
    cmd === "init" ||
    cmd === "install" ||
    flags.all ||
    flags.global;

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

  if (cmd === "help" || (flags.help && cmd)) {
    printHelp();
    ensureSetup();
    const res = runKx(["/h"]);
    process.exit(res.status == null ? 0 : res.status);
  }

  if (isBootstrap) {
    // `add <ref>` — ref is format-only (".", package name, owner/repo). Never git-clone it.
    if (cmd === "add" && rest[0] && !rest[0].startsWith("-")) {
      const ref = rest.shift();
      if (ref !== "." && !/^kx-defender$/i.test(ref)) {
        log(
          `Ignoring package ref '${ref}' (format only). Installing local Kx-Defender — no remote skill download.`
        );
      } else {
        log(`Bootstrap target: ${ref}`);
      }
    } else {
      log("Bootstrap target: . (this package)");
    }
    if (flags.all || !cmd || ["add", "setup", "init", "install"].includes(cmd)) {
      setup();
    } else {
      ensureSetup();
    }
    if (flags.global) {
      installGlobal();
    }
    if (flags.noServe) {
      log("Setup done. Try: kx /h");
      return;
    }
    startServe(flags.bind);
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
