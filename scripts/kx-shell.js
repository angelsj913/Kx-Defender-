"use strict";

/**
 * Interactive KxLang shell for PowerShell / terminals (no web Console).
 *
 *   Kx> lang ko
 *   Kx> lang en
 *   Kx> /h
 *   Kx> roast tickets --scope lab --sim
 *   Kx> exit
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { ensureSetup, runKx, log, SETUP_VERSION } = require("./npm-setup");
const { printKxBanner } = require("./banner");

function configPath() {
  return process.env.KX_CONFIG || path.join(os.homedir(), ".kx-defender", "config.json");
}

function readLang() {
  if (process.env.KX_LANG) {
    const v = String(process.env.KX_LANG).toLowerCase();
    if (v === "ko" || v === "kr" || v === "korean") return "ko";
    if (v === "en" || v === "english") return "en";
  }
  try {
    const cfg = JSON.parse(fs.readFileSync(configPath(), "utf8"));
    if (cfg.lang === "ko") return "ko";
  } catch (_) {
    /* ignore */
  }
  return "en";
}

function writeLang(lang) {
  const p = configPath();
  fs.mkdirSync(path.dirname(p), { recursive: true });
  let cfg = {};
  try {
    cfg = JSON.parse(fs.readFileSync(p, "utf8"));
  } catch (_) {
    /* ignore */
  }
  cfg.lang = lang;
  fs.writeFileSync(p, JSON.stringify(cfg, null, 2) + "\n");
  process.env.KX_LANG = lang;
}

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
  const lang = readLang();
  if (lang === "ko") {
    console.log(`Kx 셸 v${SETUP_VERSION} — /h 도움말, lang ko|en 언어, exit 종료`);
    console.log("예제:");
    console.log("  lang ko");
    console.log("  roast tickets --scope lab --realm lab.local --sim");
    console.log("  watch procs --scope lab --live");
  } else {
    console.log(`Kx shell v${SETUP_VERSION} — /h help, lang ko|en language, exit quit`);
    console.log("Examples:");
    console.log("  lang en");
    console.log("  roast tickets --scope lab --realm lab.local --sim");
    console.log("  watch procs --scope lab --live");
  }
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

    let args = splitArgs(trimmed);
    if (args[0] && args[0].toLowerCase() === "kx") args = args.slice(1);

    // Fast path for lang in shell (also handled by Python CLI)
    const head = (args[0] || "").toLowerCase();
    if (head === "lang" || head === "language" || head === "locale" || args[0] === "언어") {
      if (args.length < 2) {
        const cur = readLang();
        console.log(cur === "ko" ? `언어: ${cur} (한국어)` : `language: ${cur} (English)`);
      } else {
        const raw = String(args[1]).toLowerCase();
        let next = null;
        if (["ko", "kr", "korean", "kor", "한국어", "한글"].includes(raw) || args[1] === "한국어") {
          next = "ko";
        } else if (["en", "english", "eng", "us"].includes(raw)) {
          next = "en";
        }
        if (!next) {
          console.error("[Kx] use: lang en | lang ko");
        } else {
          writeLang(next);
          console.log(
            next === "ko"
              ? "언어가 ko (한국어)(으)로 설정되었습니다."
              : "language set to en (English)"
          );
        }
      }
      rl.prompt();
      return;
    }

    try {
      runKx(args);
    } catch (err) {
      console.error(`[Kx] ${err.message || err}`);
    }
    rl.prompt();
  });

  rl.on("close", () => {
    log(readLang() === "ko" ? "셸을 종료합니다." : "Shell closed.");
    process.exit(0);
  });
}

module.exports = { startKxShell, splitArgs, readLang, writeLang };

if (require.main === module) {
  try {
    startKxShell();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
}
