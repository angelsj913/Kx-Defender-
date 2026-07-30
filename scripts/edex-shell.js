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

const LOGO = [
  "██╗  ██╗██╗  ██╗",
  "██║ ██╔╝╚██╗██╔╝",
  "█████╔╝  ╚███╔╝ ",
  "██╔═██╗  ██╔██╗ ",
  "██║  ██╗██╔╝ ██╗",
  "╚═╝  ╚═╝╚═╝  ╚═╝",
];

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

    // Top title bar
    out.push(
      `${C.fg}╔${hline(W - 2, "═")}╗${C.reset}\n` +
        `${C.fg}║${C.reset}${C.accent}${C.bold}${pad(" Kx-DEFENDER  ·  eDEX HUD  ·  TRON LINK ", W - 2, "center")}${C.reset}${C.fg}║${C.reset}\n` +
        `${C.fg}╠${hline(side, "═")}╦${hline(mid, "═")}╦${hline(side, "═")}╣${C.reset}\n`
    );

    const bodyRows = Math.max(left.length, right.length, this.maxHistory + 2, 10);
    for (let i = 0; i < bodyRows; i++) {
      const L = left[i] || "";
      const R = right[i] || "";
      let M = "";
      if (i === 0) {
        M = `${C.warn} MAIN TERMINAL ${C.mute}// DEFCOM${C.reset}`;
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

    // logo whisper
    for (const line of LOGO) {
      out.push(`${C.dim}${C.accent}${pad(line, W, "center")}${C.reset}\n`);
    }

    const tip =
      this.lang === "ko"
        ? "명령 입력 · lang ko|en · /h · exit"
        : "enter command · lang ko|en · /h · exit";
    out.push(`${C.mute}${pad(tip, W, "center")}${C.reset}\n`);

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
          this.pushOut(next === "ko" ? "언어 → ko (한국어)" : "language → en (English)");
        }
      }
      return;
    }

    // Capture kx output
    ensureSetup();
    const state = readState();
    let res;
    const { spawnSync } = require("child_process");
    if (state?.kx && fs.existsSync(state.kx)) {
      res = spawnSync(state.kx, args, {
        cwd: ROOT,
        encoding: "utf8",
        shell: false,
        windowsHide: true,
        env: { ...process.env, KX_LANG: this.lang },
      });
    } else {
      const code =
        "import sys; from kx_defender.kx_cli import main; sys.argv=['kx']+sys.argv[1:]; main()";
      res = spawnSync(state?.python || "python", ["-c", code, ...args], {
        cwd: ROOT,
        encoding: "utf8",
        shell: isWin(),
        windowsHide: true,
        env: { ...process.env, KX_LANG: this.lang },
      });
    }
    const text = `${res.stdout || ""}${res.stderr || ""}`.trimEnd();
    if (text) this.pushOut(text);
    else if (res.status) this.pushOut(`${C.warn}exit ${res.status}${C.reset}`);
  }

  start() {
    ensureSetup();
    this.lang = readLang();
    this.pushOut(this.lang === "ko" ? "트론 링크 수립 · Kx HUD 온라인" : "tron link established · Kx HUD online");
    this.pushOut(this.lang === "ko" ? "예: roast tickets --scope lab --sim" : "try: roast tickets --scope lab --sim");

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });

    const loop = () => {
      this.renderFrame();
      rl.question(`${C.accent}${C.bold} kx>${C.reset} `, (line) => {
        try {
          this.runCommand(line);
        } catch (err) {
          this.pushOut(`[err] ${err.message || err}`);
        }
        loop();
      });
    };

    process.stdout.write("\x1b[?25h"); // show cursor
    loop();
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
