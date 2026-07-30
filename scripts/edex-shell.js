"use strict";

/**
 * eDEX-UI inspired Kx TUI (Tron / sci-fi HUD)
 * Runs inside PowerShell / Windows Terminal / any ANSI terminal.
 * Colors from eDEX tron.json — no Electron dependency.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { ensureSetup, SETUP_VERSION, ROOT, isWin, readState } = require("./npm-setup");
const { readLang, writeLang, splitArgs } = require("./kx-shell");

// eDEX tron theme
const C = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  fg: "\x1b[38;2;170;207;209m", // #aacfd1
  bg: "\x1b[48;2;5;8;13m", // #05080d
  panel: "\x1b[48;2;8;12;18m",
  accent: "\x1b[38;2;0;229;255m",
  warn: "\x1b[38;2;255;140;0m",
  ok: "\x1b[38;2;80;255;180m",
  mute: "\x1b[38;2;70;100;110m",
  black: "\x1b[38;2;0;0;0m",
};

const { KX_LOGO } = require("./banner");

const LOGO = KX_LOGO.split("\n").filter(Boolean);

function decodeChildText(raw) {
  if (raw == null) return "";
  if (Buffer.isBuffer(raw)) {
    const asUtf8 = raw.toString("utf8");
    // If UTF-8 decode produced lots of replacement-looking CP misreads, try cp949 on win
    if (isWin() && /[\u00c0-\u00ff]{2,}/.test(asUtf8) && !/[가-힣]/.test(asUtf8)) {
      try {
        return raw.toString("cp949");
      } catch {
        return asUtf8;
      }
    }
    return asUtf8;
  }
  const s = String(raw);
  // Already a string from encoding:'utf8' — if mojibake of Korean, attempt repair
  if (isWin() && /[\u00c0-\u00ff]{2,}/.test(s) && !/[가-힣]/.test(s)) {
    try {
      return Buffer.from(s, "latin1").toString("utf8");
    } catch {
      return s;
    }
  }
  return s;
}

function containsKx(text) {
  return /kx/i.test(String(text || ""));
}

function cols() {
  return process.stdout.columns || 100;
}
function rows() {
  return process.stdout.rows || 30;
}

function stripAnsi(s) {
  return String(s).replace(/\x1b\[[0-9;]*m/g, "");
}

function pad(s, width, align = "left") {
  const plain = stripAnsi(s);
  const len = [...plain].length;
  if (len >= width) return plain.slice(0, width);
  const padN = width - len;
  if (align === "right") return " ".repeat(padN) + s;
  if (align === "center") {
    const L = Math.floor(padN / 2);
    return " ".repeat(L) + s + " ".repeat(padN - L);
  }
  return s + " ".repeat(padN);
}

function hline(width, ch = "─") {
  return ch.repeat(Math.max(0, width));
}

function boxLine(content, width, { left = "│", right = "│" } = {}) {
  const inner = width - 2;
  return `${C.fg}${left}${C.reset}${C.fg}${pad(content, inner)}${C.reset}${C.fg}${right}${C.reset}`;
}

function memBar(usedPct, width = 16) {
  const filled = Math.round((usedPct / 100) * width);
  return (
    C.accent +
    "█".repeat(Math.max(0, filled)) +
    C.mute +
    "░".repeat(Math.max(0, width - filled)) +
    C.reset
  );
}

function sysPanel(width) {
  const total = os.totalmem();
  const free = os.freemem();
  const usedPct = Math.round(((total - free) / total) * 100);
  const cpus = os.cpus()?.length || 0;
  const load = os.loadavg?.()?.[0];
  const lines = [
    `${C.warn} SYS MONITOR ${C.reset}`,
    `HOST ${C.accent}${pad(os.hostname(), width - 8)}${C.reset}`,
    `CPU  ${C.fg}${cpus} threads${C.reset}`,
    `LOAD ${C.fg}${load != null ? load.toFixed(2) : "n/a"}${C.reset}`,
    `RAM  ${memBar(usedPct, Math.max(8, width - 10))} ${usedPct}%`,
    `PLAT ${C.fg}${os.platform()}/${os.arch()}${C.reset}`,
    `NODE ${C.fg}${process.version}${C.reset}`,
    `KX   ${C.ok}v${SETUP_VERSION}${C.reset}`,
  ];
  return lines;
}

function filesPanel(width) {
  let names = [];
  try {
    names = fs
      .readdirSync(process.cwd())
      .filter((n) => !n.startsWith("."))
      .slice(0, 8);
  } catch {
    names = [];
  }
  const lines = [`${C.warn} FILESYSTEM ${C.reset}`, `${C.mute}${pad(process.cwd(), width - 2)}${C.reset}`];
  for (const n of names) {
    let mark = "·";
    try {
      if (fs.statSync(path.join(process.cwd(), n)).isDirectory()) mark = "▸";
    } catch {
      /* ignore */
    }
    lines.push(`${C.fg}${mark} ${n}${C.reset}`);
  }
  while (lines.length < 10) lines.push("");
  return lines;
}

function netPanel(width) {
  const ifaces = os.networkInterfaces() || {};
  const lines = [`${C.warn} NETLINK ${C.reset}`];
  let count = 0;
  for (const [name, list] of Object.entries(ifaces)) {
    for (const a of list || []) {
      if (a.internal || a.family !== "IPv4") continue;
      lines.push(`${C.fg}${pad(name, 8)} ${a.address}${C.reset}`);
      count++;
      if (count >= 5) break;
    }
    if (count >= 5) break;
  }
  if (count === 0) lines.push(`${C.mute}no ipv4${C.reset}`);
  lines.push(`${C.ok}● LINK UP${C.reset}`);
  while (lines.length < 8) lines.push("");
  return lines;
}

class EdexShell {
  constructor() {
    this.history = [];
    this.maxHistory = 12;
    this.lang = readLang();
  }

  pushOut(text) {
    const lines = String(text || "")
      .replace(/\r\n/g, "\n")
      .split("\n");
    for (const line of lines) {
      this.history.push(line);
      if (this.history.length > this.maxHistory) this.history.shift();
    }
  }

  /** Single-write frame (terminal-ui: batch output). */
  renderFrame() {
    const W = cols();
    const side = Math.max(22, Math.min(28, Math.floor(W * 0.22)));
    const mid = Math.max(30, W - side * 2 - 2);
    const left = sysPanel(side - 2);
    const right = netPanel(side - 2);
    const files = filesPanel(W - 4);

    const out = [];
    out.push("\x1b[2J\x1b[H"); // clear + home
    out.push(C.bg);

    // Top brand — ASCII KX logo (not plain "Kx" text)
    out.push(`${C.fg}╔${hline(W - 2, "═")}╗${C.reset}\n`);
    for (const line of LOGO) {
      out.push(
        `${C.fg}║${C.reset}${C.accent}${C.bold}${pad(line, W - 2, "center")}${C.reset}${C.fg}║${C.reset}\n`
      );
    }
    out.push(`${C.fg}╠${hline(side, "═")}╦${hline(mid, "═")}╦${hline(side, "═")}╣${C.reset}\n`);

    const bodyRows = Math.max(left.length, right.length, this.maxHistory + 2, 10);
    for (let i = 0; i < bodyRows; i++) {
      const L = left[i] || "";
      const R = right[i] || "";
      let M = "";
      if (i === 0) {
        M = `${C.warn} MAIN ${C.reset}`;
      } else if (i === 1) {
        M = `${C.mute}${hline(mid - 2, "·")}${C.reset}`;
      } else {
        const hi = i - 2;
        M = this.history[hi] != null ? `${C.fg}${this.history[hi]}${C.reset}` : "";
      }
      out.push(
        `${C.fg}║${C.reset}${pad(L, side)}${C.fg}│${C.reset}${pad(M, mid)}${C.fg}│${C.reset}${pad(R, side)}${C.fg}║${C.reset}\n`
      );
    }

    out.push(`${C.fg}╠${hline(W - 2, "═")}╣${C.reset}\n`);
    // filesystem strip
    for (let i = 0; i < Math.min(4, files.length); i++) {
      out.push(`${C.fg}║${C.reset}${pad(files[i], W - 2)}${C.fg}║${C.reset}\n`);
    }
    out.push(`${C.fg}╚${hline(W - 2, "═")}╝${C.reset}\n`);

    process.stdout.write(out.join(""));
  }

  runCommand(line) {
    const trimmed = (line || "").trim();
    if (!trimmed) return;
    this.pushOut(`${C.accent}kx>${C.reset} ${trimmed}`);

    const lower = trimmed.toLowerCase();
    if (lower === "exit" || lower === "quit" || lower === "q") {
      process.stdout.write(`\n${C.ok}[Kx] link closed${C.reset}\n`);
      process.exit(0);
    }
    if (lower === "clear" || lower === "cls") {
      this.history = [];
      return;
    }

    let args = splitArgs(trimmed);
    if (args[0] && args[0].toLowerCase() === "kx") args = args.slice(1);
    // Bare `kx` or empty → English help
    if (!args.length) args = ["/h"];

    const head = (args[0] || "").toLowerCase();
    if (head === "lang" || head === "language" || head === "locale" || args[0] === "언어") {
      if (args.length < 2) {
        this.pushOut(this.lang === "ko" ? `언어: ${this.lang}` : `language: ${this.lang}`);
      } else {
        const raw = String(args[1]).toLowerCase();
        let next = null;
        if (["ko", "kr", "korean", "kor", "한국어", "한글"].includes(raw) || args[1] === "한국어") next = "ko";
        else if (["en", "english", "eng", "us"].includes(raw)) next = "en";
        if (!next) this.pushOut("use: lang en | lang ko");
        else {
          writeLang(next);
          this.lang = next;
          this.pushOut(next === "ko" ? "언어 → ko" : "language → en");
        }
      }
      return;
    }

    // Capture kx output (UTF-8 forced for Windows consoles)
    ensureSetup();
    const state = readState();
    const env = {
      ...process.env,
      KX_LANG: this.lang,
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8",
    };
    let res;
    const { spawnSync } = require("child_process");
    if (state?.kx && fs.existsSync(state.kx)) {
      res = spawnSync(state.kx, args, {
        cwd: ROOT,
        encoding: "utf8",
        shell: false,
        windowsHide: true,
        env,
      });
    } else {
      const code =
        "import sys; from kx_defender.kx_cli import main; sys.argv=['kx']+sys.argv[1:]; main()";
      res = spawnSync(state?.python || "python", ["-c", code, ...args], {
        cwd: ROOT,
        encoding: "utf8",
        shell: isWin(),
        windowsHide: true,
        env,
      });
    }
    const text = decodeChildText(`${res.stdout || ""}${res.stderr || ""}`).trimEnd();
    if (text) this.pushOut(text);
    else if (res.status) this.pushOut(`${C.warn}exit ${res.status}${C.reset}`);
  }

  start() {
    ensureSetup();
    this.lang = readLang();
    this.locked = false;
    // No decorative boot lines — prompt is enough

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });
    this._rl = rl;

    const isLogin = (line) => containsKx(line);

    let ask = () => {};
    const softLock = () => {
      if (this.locked) {
        process.stdout.write(`\n${C.warn}[Kx] locked — type anything with kx${C.reset}\n`);
        ask();
        return;
      }
      this.locked = true;
      this.history = [];
      this.pushOut("locked (Ctrl+C)");
      this.pushOut("resume: type anything containing kx");
      ask();
    };

    ask = () => {
      this.renderFrame();
      const prompt = this.locked
        ? `${C.warn}${C.bold} [login kx]>${C.reset} `
        : `${C.accent}${C.bold} kx>${C.reset} `;
      rl.question(prompt, (line) => {
        try {
          if (this.locked) {
            if (isLogin(line)) {
              this.locked = false;
              this.history = [];
              this.pushOut(
                this.lang === "ko" ? "로그인 성공 · HUD 재개" : "login ok · HUD resumed"
              );
            } else if ((line || "").trim().toLowerCase() === "exit") {
              process.stdout.write(`\n${C.ok}[Kx] link closed${C.reset}\n`);
              process.exit(0);
            } else {
              this.pushOut(
                this.lang === "ko"
                  ? "잠금 — 입력에 kx 를 포함하세요."
                  : "locked — include kx in your input"
              );
            }
            ask();
            return;
          }

          const trimmed = (line || "").trim();
          const low = trimmed.toLowerCase();
          if (low === "update" || low === "kx update" || low === "upgrade") {
            this.pushOut(this.lang === "ko" ? "업데이트 중..." : "updating...");
            this.renderFrame();
            try {
              const { updateKx } = require("./kx-update");
              updateKx();
              this.pushOut(this.lang === "ko" ? "업데이트 완료" : "update complete");
            } catch (err) {
              this.pushOut(`[update] ${err.message || err}`);
            }
            ask();
            return;
          }

          this.runCommand(line);
        } catch (err) {
          this.pushOut(`[err] ${err.message || err}`);
        }
        ask();
      });
    };

    // readline owns Ctrl+C when terminal:true — soft-lock instead of exit
    rl.on("SIGINT", softLock);

    process.stdout.write("\x1b[?25h");
    ask();
  }
}

function startEdexShell() {
  const ui = new EdexShell();
  ui.start();
}

module.exports = { startEdexShell, EdexShell };

if (require.main === module) {
  try {
    startEdexShell();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(1);
  }
}
