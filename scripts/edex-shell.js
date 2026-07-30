"use strict";

/**
 * Kx DEFCOM Operator — terminal HUD
 * Futuristic hacking-console layout (single-width-safe ASCII geometry).
 * Fixes broken 3-column bleed on Windows Terminal / PowerShell.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { ensureSetup, SETUP_VERSION, ROOT, isWin, readState } = require("./npm-setup");
const { readLang, writeLang, splitArgs } = require("./kx-shell");

/** DEFCOM palette — void + phosphor cyan + amber alert */
const C = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  hide: "\x1b[?25l",
  show: "\x1b[?25h",
  fg: "\x1b[38;2;180;220;230m",
  accent: "\x1b[38;2;0;255;208m", // phosphor
  warn: "\x1b[38;2;255;176;0m", // amber
  ok: "\x1b[38;2;0;255;136m",
  mute: "\x1b[38;2;60;90;100m",
  danger: "\x1b[38;2;255;64;96m",
  bg: "\x1b[48;2;2;4;10m",
};

/** Single-cell-safe brand mark (no fullwidth blocks — they break Windows column math) */
const LOGO = [
  "  _  __          ",
  " | |/ /__  __    ",
  " | ' </\\ \\/ /    ",
  " |_|\\_\\\\_/\\_\\    ",
];

function cols() {
  return Math.max(60, process.stdout.columns || 100);
}

function stripAnsi(s) {
  return String(s).replace(/\x1b\[[0-9;]*m/g, "");
}

/** Terminal display width (treat most BMP as 1; CJK / fullwidth as 2). */
function displayWidth(s) {
  let w = 0;
  for (const ch of stripAnsi(s)) {
    const cp = ch.codePointAt(0);
    if (cp <= 0x1f || (cp >= 0x7f && cp <= 0x9f)) continue;
    if (
      (cp >= 0x1100 && cp <= 0x115f) ||
      cp === 0x2329 ||
      cp === 0x232a ||
      (cp >= 0x2e80 && cp <= 0xa4cf) ||
      (cp >= 0xac00 && cp <= 0xd7a3) ||
      (cp >= 0xf900 && cp <= 0xfaff) ||
      (cp >= 0xfe10 && cp <= 0xfe19) ||
      (cp >= 0xfe30 && cp <= 0xfe6f) ||
      (cp >= 0xff00 && cp <= 0xff60) ||
      (cp >= 0xffe0 && cp <= 0xffe6) ||
      (cp >= 0x1f300 && cp <= 0x1f64f) ||
      (cp >= 0x1f900 && cp <= 0x1f9ff)
    ) {
      w += 2;
    } else {
      w += 1;
    }
  }
  return w;
}

function pad(s, width, align = "left") {
  const plain = stripAnsi(s);
  let w = displayWidth(plain);
  if (w > width) {
    // truncate by display width
    let out = "";
    let used = 0;
    for (const ch of plain) {
      const cw = displayWidth(ch);
      if (used + cw > width - 1) break;
      out += ch;
      used += cw;
    }
    return out + "…";
  }
  const padN = width - w;
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

function decodeChildText(raw) {
  if (raw == null) return "";
  if (Buffer.isBuffer(raw)) {
    const asUtf8 = raw.toString("utf8");
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

function primaryIpv4() {
  const ifaces = os.networkInterfaces() || {};
  for (const list of Object.values(ifaces)) {
    for (const a of list || []) {
      if (!a.internal && a.family === "IPv4") return a.address;
    }
  }
  return "0.0.0.0";
}

function shortIfaces(limit = 2) {
  const ifaces = os.networkInterfaces() || {};
  const out = [];
  for (const [name, list] of Object.entries(ifaces)) {
    for (const a of list || []) {
      if (a.internal || a.family !== "IPv4") continue;
      const short = name.length > 8 ? name.slice(0, 7) + "…" : name;
      out.push(`${short} ${a.address}`);
      if (out.length >= limit) return out;
    }
  }
  return out.length ? out : ["no-link"];
}

function memBar(usedPct, width = 18) {
  const filled = Math.round((usedPct / 100) * width);
  return (
    C.accent +
    "▓".repeat(Math.max(0, filled)) +
    C.mute +
    "░".repeat(Math.max(0, width - filled)) +
    C.reset
  );
}

function statusStrip(W) {
  const total = os.totalmem();
  const free = os.freemem();
  const usedPct = Math.round(((total - free) / total) * 100);
  const cpus = os.cpus()?.length || 0;
  const ip = primaryIpv4();
  const inner = W - 2;
  const compact = ` ${C.warn}SYS${C.reset} ${pad(os.hostname(), 14)} ${C.mute}·${C.reset} CPU ${cpus} ${C.mute}·${C.reset} RAM ${usedPct}% ${memBar(usedPct, 10)} ${C.mute}·${C.reset} ${C.ok}LINK${C.reset} ${pad(ip, 15)} ${C.mute}·${C.reset} ${C.accent}KX ${SETUP_VERSION}${C.reset}`;
  return `${C.fg}║${C.reset}${pad(compact, inner)}${C.fg}║${C.reset}`;
}

class DefcomShell {
  constructor() {
    this.history = [];
    this.maxHistory = 14;
    this.lang = readLang();
    this.locked = false;
    this.tick = 0;
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

  renderFrame() {
    const W = cols();
    const inner = W - 2;
    const out = [];
    out.push("\x1b[2J\x1b[H");
    out.push(C.bg);

    // ── Header brand ──
    out.push(`${C.fg}╔${hline(inner, "═")}╗${C.reset}\n`);
    for (const line of LOGO) {
      out.push(
        `${C.fg}║${C.reset}${C.accent}${C.bold}${pad(line, inner, "center")}${C.reset}${C.fg}║${C.reset}\n`
      );
    }
    const tag = `${C.mute}DEFCOM OPERATOR${C.reset}`;
    out.push(`${C.fg}║${C.reset}${pad(tag, inner, "center")}${C.fg}║${C.reset}\n`);
    out.push(`${C.fg}╠${hline(inner, "═")}╣${C.reset}\n`);

    // ── Telemetry strip (one row — no column bleed) ──
    out.push(statusStrip(W) + "\n");
    const nets = shortIfaces(2).join(` ${C.mute}|${C.reset} `);
    out.push(
      `${C.fg}║${C.reset}${pad(` ${C.mute}NET${C.reset} ${nets}`, inner)}${C.fg}║${C.reset}\n`
    );
    out.push(`${C.fg}╠${hline(inner, "═")}╣${C.reset}\n`);

    // ── MAIN feed ──
    out.push(
      `${C.fg}║${C.reset}${pad(` ${C.warn}▸ MAIN FEED${C.reset} ${C.mute}// KxLang${C.reset}`, inner)}${C.fg}║${C.reset}\n`
    );
    out.push(`${C.fg}║${C.reset}${pad(` ${C.mute}${hline(Math.min(inner - 2, 48), "·")}${C.reset}`, inner)}${C.fg}║${C.reset}\n`);

    const feedRows = Math.max(8, Math.min(this.maxHistory, Math.floor((process.stdout.rows || 30) * 0.35)));
    for (let i = 0; i < feedRows; i++) {
      const line = this.history[i] != null ? String(this.history[i]) : "";
      out.push(`${C.fg}║${C.reset}${pad(" " + line, inner)}${C.fg}║${C.reset}\n`);
    }

    out.push(`${C.fg}╠${hline(inner, "═")}╣${C.reset}\n`);

    // ── Filesystem strip ──
    let cwd = process.cwd();
    try {
      cwd = cwd.length > inner - 10 ? "…" + cwd.slice(-(inner - 12)) : cwd;
    } catch {
      cwd = ".";
    }
    out.push(
      `${C.fg}║${C.reset}${pad(` ${C.warn}FS${C.reset} ${C.mute}${cwd}${C.reset}`, inner)}${C.fg}║${C.reset}\n`
    );
    let names = [];
    try {
      names = fs
        .readdirSync(process.cwd())
        .filter((n) => !n.startsWith("."))
        .slice(0, 4);
    } catch {
      names = [];
    }
    const fileLine = names.length
      ? names.map((n) => (n.length > 18 ? n.slice(0, 16) + "…" : n)).join("  ·  ")
      : "—";
    out.push(`${C.fg}║${C.reset}${pad(` ${C.mute}${fileLine}${C.reset}`, inner)}${C.fg}║${C.reset}\n`);
    out.push(`${C.fg}╚${hline(inner, "═")}╝${C.reset}\n`);

    process.stdout.write(out.join(""));
  }

  runCommand(line) {
    const trimmed = (line || "").trim();
    if (!trimmed) return;
    this.pushOut(`${C.accent}kx>${C.reset} ${trimmed}`);

    const lower = trimmed.toLowerCase();
    if (lower === "exit" || lower === "quit" || lower === "q") {
      process.stdout.write(`\n${C.ok}[Kx] channel closed${C.reset}\n`);
      process.exit(0);
    }
    if (lower === "clear" || lower === "cls") {
      this.history = [];
      return;
    }

    let args = splitArgs(trimmed);
    if (args[0] && args[0].toLowerCase() === "kx") args = args.slice(1);
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

    ensureSetup();
    const state = readState();
    const env = {
      ...process.env,
      KX_LANG: this.lang,
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8",
    };
    const { spawnSync } = require("child_process");
    let res;
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
    if (text) {
      for (const ln of text.split("\n")) this.pushOut(ln);
    } else if (res.status) {
      this.pushOut(`${C.warn}exit ${res.status}${C.reset}`);
    }
  }

  start() {
    ensureSetup();
    this.lang = readLang();
    this.locked = false;
    this.pushOut(`${C.ok}DEFCOM link online${C.reset} · Kx ${SETUP_VERSION}`);
    this.pushOut(`${C.mute}type /h · update · Ctrl+C locks (resume with kx)${C.reset}`);

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });
    this._rl = rl;

    let ask = () => {};
    const softLock = () => {
      if (this.locked) {
        process.stdout.write(`\n${C.warn}[Kx] locked — include kx to resume${C.reset}\n`);
        ask();
        return;
      }
      this.locked = true;
      this.history = [];
      this.pushOut(`${C.warn}channel locked${C.reset}`);
      this.pushOut("resume: type anything containing kx");
      ask();
    };

    ask = () => {
      this.renderFrame();
      const prompt = this.locked
        ? `${C.warn}${C.bold} lock>${C.reset} `
        : `${C.accent}${C.bold} kx>${C.reset} `;
      rl.question(prompt, (line) => {
        try {
          if (this.locked) {
            if (containsKx(line)) {
              this.locked = false;
              this.history = [];
              this.pushOut(`${C.ok}channel restored${C.reset}`);
            } else if ((line || "").trim().toLowerCase() === "exit") {
              process.stdout.write(`\n${C.ok}[Kx] channel closed${C.reset}\n`);
              process.exit(0);
            } else {
              this.pushOut(`${C.mute}locked — include kx${C.reset}`);
            }
            ask();
            return;
          }

          const trimmed = (line || "").trim();
          const low = trimmed.toLowerCase();
          if (low === "update" || low === "kx update" || low === "upgrade") {
            this.pushOut("updating…");
            this.renderFrame();
            try {
              require("./kx-update").updateKx();
              this.pushOut(`${C.ok}update complete${C.reset}`);
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

    rl.on("SIGINT", softLock);
    process.stdout.write(C.show);
    ask();
  }
}

function startEdexShell() {
  const ui = new DefcomShell();
  ui.start();
}

module.exports = { startEdexShell, EdexShell: DefcomShell, DefcomShell };

if (require.main === module) {
  try {
    startEdexShell();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(1);
  }
}
