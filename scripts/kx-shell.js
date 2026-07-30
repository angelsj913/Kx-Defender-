"use strict";

/**
 * Interactive KxLang shell for PowerShell / terminals (no web Console).
 *
 *   Kx> /h
 *   Kx> roast tickets --scope lab --sim
 *   Kx> exit
 */

const readline = require("readline");
const { ensureSetup, runKx, log, SETUP_VERSION } = require("./npm-setup");
const { printKxBanner } = require("./banner");

function splitArgs(line) {
  const out = [];
  let cur = "";
  let quote = null;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quote) {
      if (ch === quote) quote = null;
      else cur += ch;
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      continue;
    }
    if (/\s/.test(ch)) {
      if (cur) out.push(cur);
      cur = "";
      continue;
    }
    cur += ch;
  }
  if (cur) out.push(cur);
  return out;
}

function startKxShell() {
  ensureSetup();
  printKxBanner();
  console.log(`Kx shell v${SETUP_VERSION} — type /h for help, exit to quit`);
  console.log("Examples:");
  console.log("  roast tickets --scope lab --realm lab.local --sim");
  console.log("  watch procs --scope lab --live");
  console.log("  sig scan --scope lab --sim");
  console.log("  serve --bind 127.0.0.1:8787   (optional Console UI)");
  console.log("");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: "Kx> ",
    terminal: true,
  });

  rl.prompt();
  rl.on("line", (line) => {
    const trimmed = (line || "").trim();
    if (!trimmed) {
      rl.prompt();
      return;
    }
    const lower = trimmed.toLowerCase();
    if (lower === "exit" || lower === "quit" || lower === "q") {
      rl.close();
      return;
    }
    if (lower === "help" || lower === "?") {
      runKx(["/h"]);
      rl.prompt();
      return;
    }
    // Allow "kx ..." or bare KxLang
    let args = splitArgs(trimmed);
    if (args[0] && args[0].toLowerCase() === "kx") args = args.slice(1);
    try {
      runKx(args);
    } catch (err) {
      console.error(`[Kx] ${err.message || err}`);
    }
    rl.prompt();
  });

  rl.on("close", () => {
    log("Shell closed.");
    process.exit(0);
  });
}

module.exports = { startKxShell, splitArgs };

if (require.main === module) {
  try {
    startKxShell();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
}
