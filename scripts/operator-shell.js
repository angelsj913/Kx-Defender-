"use strict";

/**
 * Kx DEFCOM — native terminal Operator Client (not a web UI).
 * Runs inside PowerShell / Windows Terminal as a dedicated client surface.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { spawnSync } = require("child_process");
const { ensureSetup, SETUP_VERSION, ROOT, isWin, readState } = require("./npm-setup");
const { readLang, writeLang, splitArgs } = require("./kx-shell");
const { looksLikeKxCommand, stripUnlockPrefix, isUnlockToken } = require("./kx-routing");

const C = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  show: "\x1b[?25h",
  fg: "\x1b[38;2;186;230;236m",
  accent: "\x1b[38;2;0;255;208m",
  warn: "\x1b[38;2;255;176;0m",
  ok: "\x1b[38;2;0;255;136m",
  mute: "\x1b[38;2;70;100;110m",
  bg: "\x1b[48;2;2;4;10m",
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
  return Math.max(64, process.stdout.columns || 100);
}

function stripAnsi(s) {
  return String(s).replace(/\x1b\[[0-9;]*m/g, "");
}

function displayWidth(s) {
  let w = 0;
  for (const ch of stripAnsi(s)) {
    const cp = ch.codePointAt(0);
    if (cp <= 0x1f || (cp >= 0x7f && cp <= 0x9f)) continue;
    if (
      (cp >= 0x1100 && cp <= 0x115f) ||
      (cp >= 0x2e80 && cp <= 0xa4cf) ||
      (cp >= 0xac00 && cp <= 0xd7a3) ||
      (cp >= 0xf900 && cp <= 0xfaff) ||
      (cp >= 0xff00 && cp <= 0xff60) ||
      (cp >= 0xffe0 && cp <= 0xffe6)
    ) {
      w += 2;
    } else w += 1;
  }
  return w;
}

function pad(s, width, align = "left") {
  const plain = stripAnsi(s);
  let w = displayWidth(plain);
  if (w > width) {
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
  const n = width - w;
  if (align === "right") return " ".repeat(n) + s;
  if (align === "center") {
    const L = Math.floor(n / 2);
    return " ".repeat(L) + s + " ".repeat(n - L);
  }
  return s + " ".repeat(n);
}

function hline(width, ch = "-") {
  // ASCII-only separators: reliable on every Windows code page / font
  return ch.repeat(Math.max(0, width));
}

function boxTop(W) {
  return "+" + hline(W - 2, "=") + "+";
}
function boxMid(W) {
  return "+" + hline(W - 2, "-") + "+";
}
function boxBot(W) {
  return "+" + hline(W - 2, "=") + "+";
}
function boxRow(content, W) {
  const inner = W - 2;
  return "|" + pad(content, inner) + "|";
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

function setWindowTitle(title) {
  try {
    process.stdout.write(`\x1b]0;${title}\x07`);
  } catch {
    /* ignore */
  }
}

class KxClient {
  constructor() {
    this.history = [];
    this.maxHistory = 16;
    this.lang = readLang();
    this.locked = false;
  }

  pushOut(text) {
    for (const line of String(text || "").replace(/\r\n/g, "\n").split("\n")) {
      this.history.push(line);
      if (this.history.length > this.maxHistory) this.history.shift();
    }
  }

  renderFrame() {
    const W = cols();
    const out = [];
    out.push("\x1b[2J\x1b[H");
    out.push(C.bg);

    out.push(`${C.fg}${boxTop(W)}${C.reset}\n`);
    for (const line of LOGO) {
      out.push(`${C.fg}|${C.reset}${C.accent}${C.bold}${pad(line, W - 2, "center")}${C.reset}${C.fg}|${C.reset}\n`);
    }
    out.push(
      `${C.fg}|${C.reset}${pad(`${C.mute}KX DEFCOM  ·  OPERATOR CLIENT  ·  v${SETUP_VERSION}${C.reset}`, W - 2, "center")}${C.fg}|${C.reset}\n`
    );
    out.push(`${C.fg}${boxMid(W)}${C.reset}\n`);

    const host = pad(os.hostname(), 18);
    const telemetry = ` SYS ${host}  CPU ${os.cpus()?.length || 0}  RAM ${memPct()}%  LINK ${primaryIpv4()}  ${os.platform()}/${os.arch()}`;
    out.push(`${C.fg}|${C.reset}${pad(`${C.warn}${telemetry}${C.reset}`, W - 2)}${C.fg}|${C.reset}\n`);
    out.push(`${C.fg}${boxMid(W)}${C.reset}\n`);

    out.push(`${C.fg}|${C.reset}${pad(` ${C.warn}> MAIN${C.reset}  ${C.mute}KxLang command feed${C.reset}`, W - 2)}${C.fg}|${C.reset}\n`);
    out.push(`${C.fg}|${C.reset}${pad(` ${C.mute}${hline(Math.min(40, W - 6), ".")}${C.reset}`, W - 2)}${C.fg}|${C.reset}\n`);

    const rows = Math.max(10, Math.min(this.maxHistory, Math.floor((process.stdout.rows || 32) * 0.42)));
    for (let i = 0; i < rows; i++) {
      const line = this.history[i] != null ? String(this.history[i]) : "";
      out.push(`${C.fg}|${C.reset}${pad(" " + line, W - 2)}${C.fg}|${C.reset}\n`);
    }

    out.push(`${C.fg}${boxMid(W)}${C.reset}\n`);
    let cwd = process.cwd();
    if (cwd.length > W - 12) cwd = "..." + cwd.slice(-(W - 14));
    out.push(`${C.fg}|${C.reset}${pad(` FS ${cwd}`, W - 2)}${C.fg}|${C.reset}\n`);
    out.push(`${C.fg}${boxBot(W)}${C.reset}\n`);

    process.stdout.write(out.join(""));
  }

  runCommand(line) {
    const trimmed = (line || "").trim();
    if (!trimmed) return;
    this.pushOut(`${C.accent}kx>${C.reset} ${trimmed}`);

    const lower = trimmed.toLowerCase();
    if (lower === "exit" || lower === "quit" || lower === "q") {
      process.stdout.write(`\n${C.ok}[Kx] client closed${C.reset}\n`);
      process.exit(0);
    }
    if (lower === "clear" || lower === "cls") {
      this.history = [];
      return;
    }

    // Always re-read lang so Python `lang ko` and client stay in sync
    this.lang = readLang();

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
    // Interactive client: readable text by default (JSON via --json)
    const headCmd = (args[0] || "").toLowerCase();
    const metaNoPretty = new Set([
      "lang",
      "language",
      "locale",
      "lexicon",
      "/h",
      "/help",
      "help",
      "-h",
      "--help",
      "?",
      "update",
      "upgrade",
      "daemon",
      "alert",
      "alerts",
      "report",
      "why",
      "form",
      "suggest",
      "ask",
    ]);
    if (!metaNoPretty.has(headCmd) && !args.includes("--pretty")) {
      args = [...args, "--pretty"];
    }
    const env = {
      ...process.env,
      KX_LANG: this.lang,
      PYTHONUTF8: "1",
      PYTHONIOENCODING: "utf-8",
    };
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
    if (text) for (const ln of text.split("\n")) this.pushOut(ln);
    else if (res.status) this.pushOut(`${C.warn}exit ${res.status}${C.reset}`);
  }

  start() {
    ensureSetup();
    setWindowTitle(`Kx DEFCOM Client v${SETUP_VERSION}`);
    this.lang = readLang();
    this.locked = false;
    this.pushOut(`${C.ok}operator client online${C.reset}`);
    this.pushOut(`${C.mute}/h · update · Ctrl+C lock (kx or verb to resume) · exit${C.reset}`);

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: true,
    });

    let ask = () => {};
    const softLock = () => {
      if (this.locked) {
        const msg =
          this.lang === "ko"
            ? "\n[Kx] 잠금 — kx 또는 명령(예: sentry)으로 해제\n"
            : "\n[Kx] locked — type kx or a command (e.g. sentry)\n";
        process.stdout.write(`\n${C.warn}${msg.trim()}${C.reset}\n`);
        ask();
        return;
      }
      this.locked = true;
      this.history = [];
      this.pushOut(`${C.warn}client locked${C.reset}`);
      this.pushOut(
        this.lang === "ko"
          ? "해제: kx 또는 명령 입력 (예: sentry)"
          : "resume: kx or a command (e.g. sentry)"
      );
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
            const trimmed = (line || "").trim();
            if (!trimmed) {
              ask();
              return;
            }
            if (trimmed.toLowerCase() === "exit") {
              process.stdout.write(`\n${C.ok}[Kx] client closed${C.reset}\n`);
              process.exit(0);
            }
            // Unlock only on explicit unlock tokens or real KxLang/meta heads.
            // Do NOT unlock on arbitrary text that merely contains "kx".
            if (isUnlockToken(trimmed)) {
              this.locked = false;
              this.history = [];
              this.pushOut(`${C.ok}client resumed${C.reset}`);
              const cmd = stripUnlockPrefix(trimmed);
              if (cmd && looksLikeKxCommand(cmd)) {
                const low = cmd.toLowerCase();
                if (low === "update" || low === "upgrade" || /^kx\s+(update|upgrade)$/i.test(low)) {
                  this.pushOut("updating…");
                  try {
                    require("./kx-update").updateKx();
                    this.pushOut(`${C.ok}update complete${C.reset}`);
                  } catch (err) {
                    this.pushOut(`[update] ${err.message || err}`);
                  }
                } else {
                  this.runCommand(cmd);
                }
              }
            } else {
              this.pushOut(
                this.lang === "ko"
                  ? `${C.mute}잠금 — kx 또는 명령 입력 (예: sentry)${C.reset}`
                  : `${C.mute}locked — type kx or a command (e.g. sentry)${C.reset}`
              );
            }
            ask();
            return;
          }

          const low = (line || "").trim().toLowerCase();
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

function startOperatorShell() {
  // Keep export name for npx-entry / shims — this IS the native client
  const ui = new KxClient();
  ui.start();
}

function startKxClient() {
  startOperatorShell();
}

module.exports = { startOperatorShell, startKxClient, KxClient };

if (require.main === module) {
  try {
    startKxClient();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(1);
  }
}
