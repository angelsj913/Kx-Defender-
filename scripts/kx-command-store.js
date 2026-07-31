"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const HOME = path.resolve(process.env.KX_HOME || path.join(os.homedir(), ".kx-defender"));
const HISTORY_FILE = path.join(HOME, "history.jsonl");
const FAVORITES_FILE = path.join(HOME, "favorites.json");
const MAX_HISTORY = 500;
const SKIP_HEADS = new Set(["passwd", "useradd"]);
const META_COMMANDS = [
  "alert", "case", "daemon", "doctor", "evidence", "favorite", "history",
  "lang", "report", "security", "setup", "update", "baseline", "playbook", "schedule",
  "dashboard", "overview", "alerts", "runs", "cases", "rules", "health",
];
const COMMON_FLAGS = [
  "--at", "--json", "--live", "--path", "--pretty", "--realm", "--scope",
  "--sim", "--url", "--with",
];
const SENSITIVE_FLAG = /^(--?(?:password|passwd|token|secret|cookie|authorization|api[-_]?key))$/i;
const SENSITIVE_ASSIGNMENT = /\b(password|passwd|token|secret|cookie|authorization|api[-_]?key)\s*[:=]\s*\S+/gi;
const AUTHORIZATION_VALUE = /\bauthorization\s*:\s*\S+(?:\s+\S+)?/gi;

function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, {
    encoding: "utf8",
    mode: 0o600,
  });
  fs.renameSync(temp, file);
  try { fs.chmodSync(file, 0o600); } catch (_) { /* Windows ACL */ }
}

function sanitizeCommand(command) {
  const original = String(command || "").trim();
  if (!original) return { command: "", skipped: true, redacted: false };
  const tokens = original.split(/\s+/);
  const offset = String(tokens[0] || "").toLowerCase() === "kx" ? 1 : 0;
  const head = String(tokens[offset] || "").toLowerCase();
  const sub = String(tokens[offset + 1] || "").toLowerCase();
  if (
    SKIP_HEADS.has(head) ||
    (head === "security" && sub === "password") ||
    (head === "setup" && sub === "wizard") ||
    (head === "history" && sub === "clear")
  ) {
    return { command: "", skipped: true, redacted: true };
  }
  let redacted = false;
  for (let i = 0; i < tokens.length; i++) {
    if (SENSITIVE_FLAG.test(tokens[i])) {
      if (i + 1 < tokens.length) tokens[i + 1] = "<redacted>";
      redacted = true;
    }
  }
  let sanitized = tokens.join(" ");
  sanitized = sanitized.replace(SENSITIVE_ASSIGNMENT, (match, name) => {
    redacted = true;
    const separator = match.includes("=") ? "=" : ":";
    return `${name}${separator}<redacted>`;
  });
  sanitized = sanitized.replace(AUTHORIZATION_VALUE, () => {
    redacted = true;
    return "authorization:<redacted>";
  });
  return { command: sanitized, skipped: false, redacted };
}

function readHistory() {
  if (!fs.existsSync(HISTORY_FILE)) return [];
  try {
    return fs.readFileSync(HISTORY_FILE, "utf8")
      .split(/\r?\n/)
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .filter((item) => item && typeof item.command === "string");
  } catch (_) {
    return [];
  }
}

function rewriteHistory(items) {
  fs.mkdirSync(HOME, { recursive: true });
  const temp = `${HISTORY_FILE}.${process.pid}.tmp`;
  const content = items.map((item) => JSON.stringify(item)).join("\n");
  fs.writeFileSync(temp, content ? `${content}\n` : "", { encoding: "utf8", mode: 0o600 });
  fs.renameSync(temp, HISTORY_FILE);
}

function recordHistory(command) {
  if (process.env.KX_DISABLE_HISTORY === "1") return false;
  const safe = sanitizeCommand(command);
  if (safe.skipped) return false;
  fs.mkdirSync(HOME, { recursive: true });
  fs.appendFileSync(
    HISTORY_FILE,
    `${JSON.stringify({ ts: new Date().toISOString(), command: safe.command })}\n`,
    { encoding: "utf8", mode: 0o600 }
  );
  try { fs.chmodSync(HISTORY_FILE, 0o600); } catch (_) { /* Windows ACL */ }
  const items = readHistory();
  if (items.length > MAX_HISTORY) rewriteHistory(items.slice(-MAX_HISTORY));
  return true;
}

function listHistory({ limit = 50 } = {}) {
  return readHistory().slice(-Math.max(1, Math.min(Number(limit) || 50, MAX_HISTORY))).reverse();
}

function searchHistory(query, options) {
  const needle = String(query || "").toLowerCase();
  return listHistory(options).filter((item) => item.command.toLowerCase().includes(needle));
}

function clearHistory() {
  const count = readHistory().length;
  try { fs.rmSync(HISTORY_FILE, { force: true }); } catch (_) { /* no history */ }
  return count;
}

function loadFavorites() {
  try {
    const parsed = JSON.parse(fs.readFileSync(FAVORITES_FILE, "utf8"));
    return parsed && parsed.version === 1 && parsed.favorites ? parsed : { version: 1, favorites: {} };
  } catch (_) {
    return { version: 1, favorites: {} };
  }
}

function addFavorite(name, command) {
  const key = String(name || "").trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(key)) {
    throw new Error("favorite name must use letters, numbers, dot, dash, or underscore");
  }
  const safe = sanitizeCommand(command);
  if (safe.skipped || safe.redacted) {
    throw new Error("sensitive commands cannot be saved as favorites");
  }
  if (!safe.command || /^kx\s+favorite\b|^favorite\b/i.test(safe.command)) {
    throw new Error("favorite command is invalid");
  }
  const store = loadFavorites();
  store.favorites[key] = {
    command: safe.command,
    updatedAt: new Date().toISOString(),
  };
  atomicJson(FAVORITES_FILE, store);
  return { name: key, ...store.favorites[key] };
}

function removeFavorite(name) {
  const store = loadFavorites();
  if (!store.favorites[name]) throw new Error(`favorite not found: ${name}`);
  delete store.favorites[name];
  atomicJson(FAVORITES_FILE, store);
}

function getFavorite(name) {
  const item = loadFavorites().favorites[name];
  if (!item) throw new Error(`favorite not found: ${name}`);
  return { name, ...item };
}

function listFavorites() {
  const store = loadFavorites();
  return Object.entries(store.favorites)
    .map(([name, item]) => ({ name, ...item }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function prepareFavoriteRun(name, { confirmLive = false } = {}) {
  const item = getFavorite(name);
  if (/(^|\s)--live(\s|$)/.test(item.command) && !confirmLive) {
    throw new Error("live favorite requires --confirm-live");
  }
  return item.command;
}

function loadLexicon() {
  try {
    return JSON.parse(
      fs.readFileSync(path.join(__dirname, "..", "fixtures", "catalog", "kxlang_lexicon.json"), "utf8")
    );
  } catch (_) {
    return { verbs: {} };
  }
}

function complete(line) {
  const text = String(line || "");
  const trailing = /\s$/.test(text);
  const tokens = text.trim() ? text.trim().split(/\s+/) : [];
  if (trailing) tokens.push("");
  const current = tokens[tokens.length - 1] || "";
  const lexicon = loadLexicon();
  let candidates;
  if (tokens.length <= 1) {
    candidates = [...Object.keys(lexicon.verbs || {}), ...META_COMMANDS];
  } else if (tokens.length === 2 && lexicon.verbs?.[tokens[0]]) {
    candidates = Object.keys(lexicon.verbs[tokens[0]].objects || {});
  } else if (current.startsWith("-")) {
    candidates = COMMON_FLAGS;
  } else {
    candidates = [];
  }
  const matches = [...new Set(candidates)]
    .filter((item) => item.startsWith(current))
    .sort();
  return [matches.length ? matches : (current ? [] : candidates.sort()), current];
}

function executeMeta(args) {
  const clean = args.map(String);
  const head = String(clean[0] || "").toLowerCase();
  const sub = String(clean[1] || "list").toLowerCase();
  const asJson = clean.includes("--json");
  const value = (result, human) => ({
    exitCode: 0,
    output: asJson ? JSON.stringify(result, null, 2) : human,
  });
  if (head === "history") {
    if (sub === "list") {
      const items = listHistory();
      return value({ history: items }, items.map((item) => `${item.ts}  ${item.command}`).join("\n") || "(no history)");
    }
    if (sub === "search") {
      const query = clean.slice(2).filter((item) => item !== "--json").join(" ");
      const items = searchHistory(query);
      return value({ history: items }, items.map((item) => `${item.ts}  ${item.command}`).join("\n") || "(no matches)");
    }
    if (sub === "clear") {
      if (!clean.includes("--yes")) throw new Error("history clear requires --yes");
      const count = clearHistory();
      return value({ cleared: count }, `cleared ${count} history item(s)`);
    }
    throw new Error("use: kx history list|search|clear");
  }
  if (head === "favorite") {
    if (sub === "list") {
      const items = listFavorites();
      return value({ favorites: items }, items.map((item) => `${item.name}  ${item.command}`).join("\n") || "(no favorites)");
    }
    if (sub === "add") {
      if (!clean[2] || !clean[3]) throw new Error('use: kx favorite add <name> "<command>"');
      const item = addFavorite(clean[2], clean.slice(3).filter((arg) => arg !== "--json").join(" "));
      return value(item, `saved ${item.name}: ${item.command}`);
    }
    if (sub === "remove") {
      removeFavorite(clean[2]);
      return value({ removed: clean[2] }, `removed ${clean[2]}`);
    }
    if (sub === "run") {
      const command = prepareFavoriteRun(clean[2], { confirmLive: clean.includes("--confirm-live") });
      return { exitCode: 0, output: `running ${clean[2]}: ${command}`, commandToRun: command };
    }
    throw new Error("use: kx favorite add|run|list|remove");
  }
  throw new Error("expected history or favorite command");
}

module.exports = {
  addFavorite,
  clearHistory,
  complete,
  executeMeta,
  getFavorite,
  listFavorites,
  listHistory,
  prepareFavoriteRun,
  recordHistory,
  removeFavorite,
  sanitizeCommand,
  searchHistory,
};
