#!/usr/bin/env node
"use strict";

/**
 * `kx` launcher:
 *   kx / anything containing only entry intent → HUD
 *   kx /h | kx <verb> … → one-shot KxLang
 */

const path = require("path");
const { spawnSync } = require("child_process");
const { runKx, ensureSetup } = require("./npm-setup");

const args = process.argv.slice(2);

function containsKx(text) {
  return /kx/i.test(String(text || ""));
}

function shouldEnterProgram(argv) {
  if (!argv.length) return true;
  const joined = argv.join(" ").toLowerCase();
  // update stays a system command
  if (argv[0] === "update" || argv[0] === "upgrade") return false;
  if (argv[0] === "/h" || argv[0] === "-h" || argv[0] === "--help" || argv[0] === "help") return false;
  // kx <verb> … one-shot (verb is not login/hud/…)
  if (argv[0].toLowerCase() === "kx") {
    const rest = argv.slice(1);
    if (!rest.length) return true;
    const head = rest[0].toLowerCase();
    if (["login", "hud", "edex", "shell", "repl", "cli"].includes(head)) return true;
    if (head === "update" || head === "upgrade") return false;
    return false; // kx roast … etc.
  }
  // login kx / [login kx] / loginkx / any token with kx and no KxLang verb path
  if (containsKx(joined)) {
    const first = argv[0].toLowerCase().replace(/[\[\]]/g, "");
    const kxLangVerbs = new Set([
      "sentry", "trace", "audit", "harden", "triage", "comply", "forge",
      "roast", "relay", "loot", "bait", "breach", "crack", "nexus", "graph",
      "probe", "sweep", "watch", "kill", "sig", "lang", "lexicon", "serve",
    ]);
    if (kxLangVerbs.has(first)) return false;
    return true;
  }
  return false;
}

if (shouldEnterProgram(args)) {
  const entry = path.join(__dirname, "npx-entry.js");
  const res = spawnSync(process.execPath, [entry], {
    stdio: "inherit",
    env: process.env,
    windowsHide: true,
  });
  process.exit(res.status == null ? 0 : res.status);
}

if (args[0] && args[0].toLowerCase() === "update") {
  require("./kx-update").updateKx();
  process.exit(0);
}

ensureSetup();
const forward = args[0] && args[0].toLowerCase() === "kx" ? args.slice(1) : args;
const res = runKx(forward);
process.exit(res.status == null ? 1 : res.status);
