"use strict";

const { KX_LOGO } = require("./banner");

const ANSI_RE = /\x1b\[[0-?]*[ -/]*[@-~]/g;
const C = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  cyan: "\x1b[36m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  dim: "\x1b[2m",
};

function colorEnabled(explicit) {
  if (explicit === false) return false;
  if (process.env.NO_COLOR || process.env.KX_NO_COLOR || process.env.TERM === "dumb") return false;
  return explicit === true || process.stdout.isTTY === true;
}

function stripAnsi(value) {
  return String(value || "").replace(ANSI_RE, "");
}

function codePointWidth(cp) {
  if (cp === 0 || cp < 32 || (cp >= 0x7f && cp < 0xa0)) return 0;
  if (
    (cp >= 0x0300 && cp <= 0x036f) ||
    (cp >= 0x1ab0 && cp <= 0x1aff) ||
    (cp >= 0x1dc0 && cp <= 0x1dff) ||
    (cp >= 0xfe20 && cp <= 0xfe2f)
  ) return 0;
  if (
    cp >= 0x1100 &&
    (cp <= 0x115f || cp === 0x2329 || cp === 0x232a ||
      (cp >= 0x2e80 && cp <= 0xa4cf && cp !== 0x303f) ||
      (cp >= 0xac00 && cp <= 0xd7a3) ||
      (cp >= 0xf900 && cp <= 0xfaff) ||
      (cp >= 0xfe10 && cp <= 0xfe19) ||
      (cp >= 0xfe30 && cp <= 0xfe6f) ||
      (cp >= 0xff00 && cp <= 0xff60) ||
      (cp >= 0xffe0 && cp <= 0xffe6) ||
      (cp >= 0x1f300 && cp <= 0x1faff))
  ) return 2;
  return 1;
}

function stringWidth(value) {
  let width = 0;
  for (const ch of stripAnsi(value)) width += codePointWidth(ch.codePointAt(0));
  return width;
}

function clip(value, maxWidth) {
  if (maxWidth <= 0) return "";
  const input = String(value || "");
  let out = "";
  let width = 0;
  for (let index = 0; index < input.length;) {
    if (input[index] === "\x1b") {
      const match = input.slice(index).match(/^\x1b\[[0-?]*[ -/]*[@-~]/);
      if (match) {
        out += match[0];
        index += match[0].length;
        continue;
      }
    }
    const cp = input.codePointAt(index);
    const ch = String.fromCodePoint(cp);
    const next = codePointWidth(ch.codePointAt(0));
    if (width + next > maxWidth) break;
    out += ch;
    width += next;
    index += ch.length;
  }
  return out;
}

function pad(value, width, align = "left") {
  const text = clip(value, width);
  const gap = Math.max(0, width - stringWidth(text));
  if (align === "center") {
    const left = Math.floor(gap / 2);
    return " ".repeat(left) + text + " ".repeat(gap - left);
  }
  return text + " ".repeat(gap);
}

function paint(value, style, enabled) {
  return enabled ? `${style}${value}${C.reset}` : value;
}

function center(value, width) {
  return pad(value, width, "center");
}

function clearScreen() {
  return "\x1b[2J\x1b[3J\x1b[H";
}

function contentWidth(width) {
  return Math.min(Math.max(40, width - 4), 118);
}

function logoLines(width, enabled, frame = 0) {
  const palette = [C.cyan, C.green, C.cyan, C.yellow];
  return KX_LOGO.split("\n").map((line, index) => {
    const centered = center(line, width);
    return paint(centered, `${C.bold}${palette[(frame + index) % palette.length]}`, enabled);
  });
}

function bordered(lines, width, title = "") {
  const inner = Math.max(1, width - 2);
  const label = title ? ` ${clip(title, Math.max(0, inner - 3))} ` : "";
  const top = `┌${label}${"─".repeat(Math.max(0, inner - stringWidth(label)))}┐`;
  const body = lines.map((line) => `│${pad(line, inner)}│`);
  return [top, ...body, `└${"─".repeat(inner)}┘`];
}

function progressBar(percent, width) {
  const inner = Math.max(10, width - 9);
  const complete = Math.round((Math.max(0, Math.min(100, percent)) / 100) * inner);
  return `[${"━".repeat(complete)}${"─".repeat(inner - complete)}] ${String(percent).padStart(3)}%`;
}

function renderLoading({ width = 80, percent = 0, label = "Loading", frame = 0, color } = {}) {
  const enabled = colorEnabled(color);
  const boxWidth = contentWidth(width);
  const rows = [
    "",
    ...logoLines(boxWidth - 2, enabled, frame),
    "",
    center(label, boxWidth - 2),
    center(progressBar(percent, Math.min(boxWidth - 6, 64)), boxWidth - 2),
    "",
  ];
  return bordered(rows, boxWidth, "KX DEFENDER").map((line) => center(line, width)).join("\n");
}

function wrapText(text, width) {
  const out = [];
  for (const source of String(text || "").split(/\r?\n/)) {
    if (!source) {
      out.push("");
      continue;
    }
    let rest = source;
    while (stringWidth(rest) > width) {
      const part = clip(rest, width);
      out.push(part);
      rest = [...rest].slice([...part].length).join("");
    }
    out.push(rest);
  }
  return out;
}

function renderDashboard({
  width = 80,
  height = 30,
  lang = "en",
  username = "operator",
  result = "",
  version = "",
  color,
} = {}) {
  const enabled = colorEnabled(color);
  const boxWidth = contentWidth(width);
  const inner = boxWidth - 2;
  const compact = width < 72 || height < 24;
  const title = version ? `KX DEFENDER · ${version}` : "KX DEFENDER";
  const status = lang === "ko"
    ? `상태: 온라인  |  사용자: ${username}  |  언어: 한국어`
    : `Status: online  |  User: ${username}  |  Language: English`;
  const help = lang === "ko"
    ? "명령어를 입력하세요 · /h 도움말 · lang en · exit 종료"
    : "Enter a command · /h help · lang ko · exit";
  const rows = [];
  if (!compact) rows.push("", ...logoLines(inner, enabled), "");
  rows.push(paint(center(title, inner), C.bold, enabled));
  rows.push(paint(center(status, inner), C.green, enabled));
  rows.push("");
  const resultTitle = lang === "ko" ? "최근 결과" : "LATEST RESULT";
  const resultLines = result
    ? wrapText(result, inner - 2).slice(0, Math.max(4, height - (compact ? 12 : 20)))
    : [lang === "ko" ? "아직 실행한 명령이 없습니다." : "No command has been run yet."];
  rows.push(...bordered(resultLines, inner, resultTitle));
  rows.push("");
  rows.push(paint(center(help, inner), C.dim, enabled));
  return bordered(rows, boxWidth).map((line) => center(line, width)).join("\n");
}

function renderPromptTop(width = 80, color) {
  const enabled = colorEnabled(color);
  const boxWidth = contentWidth(width);
  const left = Math.max(0, Math.floor((width - boxWidth) / 2));
  return `${" ".repeat(left)}${paint(`┌─ COMMAND ${"─".repeat(Math.max(0, boxWidth - 12))}┐`, C.cyan, enabled)}`;
}

function renderPromptBottom(width = 80, color) {
  const enabled = colorEnabled(color);
  const boxWidth = contentWidth(width);
  const left = Math.max(0, Math.floor((width - boxWidth) / 2));
  return `${" ".repeat(left)}${paint(`└${"─".repeat(boxWidth - 2)}┘`, C.cyan, enabled)}`;
}

function promptPrefix(width = 80, color) {
  const enabled = colorEnabled(color);
  const boxWidth = contentWidth(width);
  const left = Math.max(0, Math.floor((width - boxWidth) / 2));
  return `${" ".repeat(left)}${paint("│", C.cyan, enabled)} ${paint("kx ›", C.bold, enabled)} `;
}

module.exports = {
  clearScreen,
  colorEnabled,
  renderDashboard,
  renderLoading,
  renderPromptBottom,
  renderPromptTop,
  promptPrefix,
  stringWidth,
  stripAnsi,
};
