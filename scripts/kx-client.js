#!/usr/bin/env node
"use strict";

/**
 * Native Kx Operator Client entry (terminal — not web).
 * Prefer: node scripts/kx-client.js   or   kx
 */

const { isWin } = require("./npm-setup");
const { spawnSync } = require("child_process");

if (isWin()) {
  try {
    spawnSync("chcp", ["65001"], { stdio: "ignore", shell: true, windowsHide: true });
  } catch (_) {
    /* ignore */
  }
  process.env.PYTHONUTF8 = "1";
  process.env.PYTHONIOENCODING = "utf-8";
}

require("./operator-shell").startKxClient();
