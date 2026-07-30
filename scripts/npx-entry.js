#!/usr/bin/env node
"use strict";

/**
 * Kx-Defender npx entry — quiet skills-style one-liner
 *
 *   npx --yes kx-defender add --all -g
 *   npx --yes kx-defender --all -g
 *
 * Installs bundled agent skills only (no third-party `skills` CLI,
 * no GitHub Source banner, no Eve/PromptScript noise).
 */

const { spawnSync } = require("child_process");
const path = require("path");
const os = require("os");
const fs = require("fs");
const {
  installAgentSkills,
  listSkillDirs,
} = require("./install-agent-skills");
const { setup, ensureSetup, runKx, log, ROOT, isWin } = require("./npm-setup");

function printHelp() {
  console.log(`Kx-Defender

Install agent skills:
  npx --yes kx-defender add --all -g
  npx --yes kx-defender --all -g

Other:
  npx --yes kx-defender setup          Python runtime + package
  npx --yes kx-defender serve [--bind host:port]
  npx --yes kx-defender kx <KxLang args...>

Flags:
  --all           Install all bundled skills
  -g, --global    Install into user skill dirs (~/.agents/skills, ~/.cursor/skills)
  --runtime       Also set up Python runtime (optional)
  --no-serve      With --runtime, skip Console start

Self-Built Only — ships this package's skills/ only.
`);
}

function parseArgs(argv) {
  const flags = {
    all: false,
    global: false,
    noServe: false,
    runtime: false,
    bind: process.env.KX_BIND || "127.0.0.1:8787",
    help: false,
  };
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--all") flags.all = true;
    else if (a === "-g" || a === "--global") flags.global = true;
    else if (a === "--no-serve") flags.noServe = true;
    else if (a === "--runtime") flags.runtime = true;
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
  const result = installAgentSkills({
    global: Boolean(flags.global || flags.all),
  });
  console.log(`Installed ${result.names.length} skills`);
  for (const name of result.names) console.log(`  ✓ ${name}`);
  for (const t of result.targets) console.log(`  → ${t}`);
  if (flags.global) installGlobalShims();
  console.log("Done.");
}

function main() {
  const { flags, positional } = parseArgs(process.argv.slice(2));
  if (flags.help && positional.length === 0) {
    printHelp();
    return;
  }

  const cmd = (positional[0] || "").toLowerCase();
  const rest = positional.slice(1);

  // Consume format-only package ref after `add` (never fetch remote)
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

  if (cmd === "setup" || flags.runtime) {
    setup();
    if (flags.global) installGlobalShims();
    if (!flags.noServe && cmd !== "setup") {
      startServe(flags.bind);
      return;
    }
    log("Runtime ready. Try: kx /h");
    return;
  }

  if (cmd === "help") {
    printHelp();
    return;
  }

  // Default / add / install / --all / -g → quiet agent-skill install
  const isSkillAdd =
    !cmd ||
    cmd === "add" ||
    cmd === "init" ||
    cmd === "install" ||
    flags.all ||
    flags.global;

  if (isSkillAdd) {
    doSkillInstall(flags);
    if (flags.runtime) {
      setup();
      if (!flags.noServe) startServe(flags.bind);
    }
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
