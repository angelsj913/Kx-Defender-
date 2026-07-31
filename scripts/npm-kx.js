#!/usr/bin/env node
"use strict";

/**
 * `kx` launcher:
 *   kx              → HUD
 *   kx update       → updater (not a KxLang verb)
 *   kx /h | kx <verb> … → one-shot KxLang
 */

const path = require("path");
const { spawnSync } = require("child_process");
const { runKx, ensureSetup } = require("./npm-setup");
const { runDoctor } = require("./kx-doctor");

const args = process.argv.slice(2);

function isUpdate(argv) {
  if (!argv.length) return false;
  const a0 = String(argv[0]).toLowerCase();
  if (a0 === "update" || a0 === "upgrade") return true;
  if (a0 === "kx" && argv[1]) {
    const a1 = String(argv[1]).toLowerCase();
    return a1 === "update" || a1 === "upgrade";
  }
  return false;
}

function doctorArgs(argv) {
  if (String(argv[0] || "").toLowerCase() === "doctor") return argv.slice(1);
  if (
    String(argv[0] || "").toLowerCase() === "kx" &&
    String(argv[1] || "").toLowerCase() === "doctor"
  ) {
    return argv.slice(2);
  }
  return null;
}

function containsKx(text) {
  return /kx/i.test(String(text || ""));
}

function shouldEnterProgram(argv) {
  if (!argv.length) return true;
  if (isUpdate(argv)) return false;
  const a0 = String(argv[0]).toLowerCase();
  if (a0 === "/h" || a0 === "-h" || a0 === "--help" || a0 === "help") return false;
  if (a0 === "kx") {
    const rest = argv.slice(1);
    if (!rest.length) return true;
    const head = String(rest[0]).toLowerCase();
    if (["login", "hud", "shell", "repl", "cli"].includes(head)) return true;
    return false; // kx roast …
  }
  if (containsKx(argv.join(" "))) {
    const first = a0.replace(/[\[\]]/g, "");
    const kxLangVerbs = new Set([
      "sentry", "trace", "audit", "harden", "triage", "comply", "forge",
      "roast", "relay", "loot", "bait", "breach", "crack", "nexus", "graph",
      "probe", "sweep", "watch", "kill", "sig", "lang", "lexicon",
    ]);
    if (kxLangVerbs.has(first)) return false;
    return true;
  }
  return false;
}

const doctorForward = doctorArgs(args);
if (doctorForward) {
  process.exit(runDoctor(doctorForward));
}

if (isUpdate(args)) {
  try {
    const offset = String(args[0]).toLowerCase() === "kx" ? 2 : 1;
    require("./kx-update").updateKx(args.slice(offset));
    process.exit(0);
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
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

ensureSetup();
const forward = args[0] && String(args[0]).toLowerCase() === "kx" ? args.slice(1) : args;
const res = runKx(forward);
process.exit(res.status == null ? 1 : res.status);
