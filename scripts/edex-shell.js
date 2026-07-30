"use strict";

/**
 * Kx DEFCOM — Operator Client (Claude Code CLI style, single-window scrolling)
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { spawnSync } = require("child_process");
const { ensureSetup, SETUP_VERSION, ROOT, isWin, readState } = require("./npm-setup");
const { readLang, writeLang, splitArgs } = require("./kx-shell");

const C = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  fg: "\x1b[38;2;186;230;236m",
  accent: "\x1b[38;2;0;255;208m",
  warn: "\x1b[38;2;255;176;0m",
  ok: "\x1b[38;2;0;255;136m",
  mute: "\x1b[38;2;70;100;110m",
};

const LOGO = [
  "██╗  ██╗██╗  ██╗",
  "██║ ██╔╝╚██╗██╔╝",
  "█████╔╝  ╚███╔╝ ",
  "██╔═██╗  ██╔██╗ ",
  "██║  ██╗██╔╝ ██╗",
  "╚═╝  ╚═╝╚═╝  ╚═╝",
];

function primaryIpv4() {
  const ifaces = os.networkInterfaces() || {};
  for (const list of Object.values(ifaces)) {
    for (const a of list || []) {
      if (!a.internal && a.family === "IPv4") return a.address;
    }
  }
  return "0.0.0.0";
}

function memPct() {
  const t = os.totalmem();
  const f = os.freemem();
  return Math.round(((t - f) / t) * 100);
}

function printBanner() {
  const line = "─".repeat(50);
  process.stdout.write("\n");
  for (const l of LOGO) {
    process.stdout.write(`  ${C.accent}${C.bold}${l}${C.reset}\n`);
  }
  process.stdout.write(`\n  ${C.mute}KX DEFCOM  ·  OPERATOR CLIENT  ·  v${SETUP_VERSION}${C.reset}\n`);
  process.stdout.write(`${C.fg}${line}${C.reset}\n`);
  process.stdout.write(
    `  ${C.warn}SYS ${os.hostname()}  CPU ${os.cpus()?.length || 0}  RAM ${memPct()}%  LINK ${primaryIpv4()}  ${os.platform()}/${os.arch()}${C.reset}\n`
  );
  process.stdout.write(`${C.fg}${line}${C.reset}\n\n`);
}

function runCmd(args, lang) {
  const state = readState();
  const env = {
    ...process.env,
    KX_LANG: lang,
    PYTHONUTF8: "1",
    PYTHONIOENCODING: "utf-8",
  };

  // Always call Python directly to avoid kx.exe creating new console windows on Windows
  const code =
    "import sys; from kx_defender.kx_cli import main; sys.argv=['kx']+sys.argv[1:]; main()";
  const pyExe = state?.python || (isWin() ? "python" : "python3");

  return spawnSync(pyExe, ["-c", code, ...args], {
    cwd: ROOT,
    stdio: "inherit",
    shell: false,
    windowsHide: true,
    env,
  });
}

class KxClient {
  constructor() {
    this.lang = "en";
  }

  start() {
    ensureSetup();
    this.lang = readLang();
    printBanner();

    const lang = this.lang;
    if (lang === "ko") {
      console.log(`${C.ok}operator client online${C.reset}`);
      console.log(`${C.mute}/h 도움말  ·  update 업데이트  ·  exit 종료${C.reset}\n`);
    } else {
      console.log(`${C.ok}operator client online${C.reset}`);
      console.log(`${C.mute}/h help  ·  update  ·  exit${C.reset}\n`);
    }

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });

    const ask = () => {
      if (rl.closed) return;
      rl.question(`${C.accent}${C.bold} kx>${C.reset} `, (line) => {
        try {
          this.handle(line, rl);
        } catch (err) {
          console.error(`[Kx] ${err.message || err}`);
        }
        if (!rl.closed) ask();
      });
    };

    rl.on("close", () => {
      console.log(`\n${C.ok}[Kx] client closed${C.reset}`);
      process.exit(0);
    });

    ask();
  }

  handle(line, rl) {
    const trimmed = (line || "").trim();
    if (!trimmed) return;

    const lower = trimmed.toLowerCase();
    if (lower === "exit" || lower === "quit" || lower === "q") {
      if (rl) rl.close();
      return;
    }
    if (lower === "clear" || lower === "cls") {
      process.stdout.write("\x1b[2J\x1b[H");
      return;
    }

    let args = splitArgs(trimmed);
    if (args[0] && args[0].toLowerCase() === "kx") args = args.slice(1);
    if (!args.length) args = ["/h"];

    const head = (args[0] || "").toLowerCase();

    if (head === "lang" || head === "language" || head === "locale" || args[0] === "언어") {
      if (args.length < 2) {
        console.log(this.lang === "ko" ? `언어: ${this.lang} (한국어)` : `language: ${this.lang} (English)`);
      } else {
        const raw = String(args[1]).toLowerCase();
        let next = null;
        if (["ko", "kr", "korean", "kor", "한국어", "한글"].includes(raw)) next = "ko";
        else if (["en", "english", "eng", "us"].includes(raw)) next = "en";
        if (!next) console.error("[Kx] use: lang en | lang ko");
        else {
          writeLang(next);
          this.lang = next;
          console.log(next === "ko" ? "언어가 ko (한국어)(으)로 설정되었습니다." : "language set to en (English)");
        }
      }
      return;
    }

    if (lower === "update" || lower === "kx update" || lower === "upgrade") {
      try {
        require("./kx-update").updateKx();
      } catch (err) {
        console.error(`[update] ${err.message || err}`);
      }
      return;
    }

    console.log("");
    runCmd(args, this.lang);
    console.log("");
  }
}

function startEdexShell() {
  const ui = new KxClient();
  ui.start();
}

function startKxClient() {
  startEdexShell();
}

module.exports = { startEdexShell, startKxClient, KxClient, EdexShell: KxClient };

if (require.main === module) {
  try {
    startKxClient();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(1);
  }
}
