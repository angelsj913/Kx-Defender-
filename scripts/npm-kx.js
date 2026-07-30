#!/usr/bin/env node
"use strict";

/**
 * `kx` launcher:
 *   kx              → start Kx-Defender HUD (the program)
 *   kx /h           → English help
 *   kx roast ...    → one-shot KxLang
 */

const path = require("path");
const { spawnSync } = require("child_process");
const { runKx, ensureSetup } = require("./npm-setup");

const args = process.argv.slice(2);

if (args.length === 0) {
  // Bare `kx` launches the interactive program (eDEX HUD)
  const entry = path.join(__dirname, "npx-entry.js");
  const res = spawnSync(process.execPath, [entry], {
    stdio: "inherit",
    env: process.env,
    windowsHide: true,
  });
  process.exit(res.status == null ? 0 : res.status);
}

ensureSetup();
const res = runKx(args);
process.exit(res.status == null ? 1 : res.status);
