#!/usr/bin/env node
"use strict";

/**
 * Single kx launcher (simplified — PRD §4):
 *   kx                 → native client
 *   kx update          → updater
 *   kx login | hud …   → client
 *   kx <verb> …        → Python kx_cli (one path)
 */

const path = require("path");
const { spawnSync } = require("child_process");
const { runKx, ensureSetup } = require("./npm-setup");

const args = process.argv.slice(2);

function lower(a) {
  return String(a || "").toLowerCase();
}

function isUpdate(argv) {
  if (!argv.length) return false;
  if (["update", "upgrade"].includes(lower(argv[0]))) return true;
  if (lower(argv[0]) === "kx" && ["update", "upgrade"].includes(lower(argv[1]))) return true;
  return false;
}

function isClientOnly(argv) {
  if (!argv.length) return true;
  const a0 = lower(argv[0]).replace(/[\[\]]/g, "");
  if (["login", "login-kx", "loginkx", "hud", "edex", "shell", "repl", "cli", "client"].includes(a0)) {
    return true;
  }
  if (a0 === "kx") {
    if (argv.length === 1) return true;
    const a1 = lower(argv[1]).replace(/[\[\]]/g, "");
    return ["login", "hud", "edex", "shell", "repl", "cli", "client"].includes(a1);
  }
  return false;
}

if (isUpdate(args)) {
  try {
    require("./kx-update").updateKx();
    process.exit(0);
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
}

if (isClientOnly(args)) {
  const entry = path.join(__dirname, "kx-client.js");
  const res = spawnSync(process.execPath, [entry], {
    stdio: "inherit",
    env: process.env,
    windowsHide: true,
  });
  process.exit(res.status == null ? 0 : res.status);
}

ensureSetup();
const forward = lower(args[0]) === "kx" ? args.slice(1) : args;
const res = runKx(forward);
process.exit(res.status == null ? 1 : res.status);
