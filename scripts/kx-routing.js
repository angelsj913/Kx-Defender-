"use strict";

/**
 * Shared launcher routing helpers (no HUD steal of Strike verbs).
 */

function lowerToken(a) {
  return String(a || "")
    .toLowerCase()
    .replace(/[\[\]]/g, "");
}

/** True only for explicit login / re-entry tokens — never realm/host containing "kx". */
function isLoginCommand(cmd, rest) {
  const a0 = lowerToken(cmd);
  const a1 = lowerToken((rest || [])[0]);
  if (["login", "login-kx", "loginkx", "login_kx"].includes(a0) || /^login[-_]?kx$/.test(a0)) return true;
  if (a0 === "kx" && (["login", "login-kx", "loginkx", "login_kx"].includes(a1) || /^login[-_]?kx$/.test(a1))) {
    return true;
  }
  return false;
}

function isClientOnlyArgv(argv) {
  const args = argv || [];
  if (!args.length) return true;
  const a0 = lowerToken(args[0]);
  if (
    ["login", "login-kx", "loginkx", "login_kx", "hud", "edex", "shell", "repl", "cli", "client"].includes(a0) ||
    /^login[-_]?kx$/.test(a0)
  ) {
    return true;
  }
  if (a0 === "kx") {
    if (args.length === 1) return true;
    const a1 = lowerToken(args[1]);
    return (
      ["login", "hud", "edex", "shell", "repl", "cli", "client", "login-kx", "loginkx", "login_kx"].includes(a1) ||
      /^login[-_]?kx$/.test(a1)
    );
  }
  return false;
}

/** Known KxLang / meta heads — used so soft-lock does not swallow real commands like sentry. */
const KX_COMMAND_HEADS = new Set([
  "sentry",
  "trace",
  "audit",
  "harden",
  "triage",
  "comply",
  "forge",
  "roast",
  "relay",
  "loot",
  "bait",
  "breach",
  "crack",
  "nexus",
  "graph",
  "probe",
  "sweep",
  "watch",
  "kill",
  "sig",
  "lang",
  "language",
  "locale",
  "lexicon",
  "daemon",
  "alert",
  "alerts",
  "report",
  "why",
  "form",
  "suggest",
  "ask",
  "update",
  "upgrade",
  "/h",
  "/help",
  "help",
  "-h",
  "--help",
  "?",
]);

function looksLikeKxCommand(line) {
  const raw = String(line || "").trim();
  if (!raw) return false;
  const parts = raw.split(/\s+/);
  let head = lowerToken(parts[0]);
  if (head === "kx" && parts.length >= 2) head = lowerToken(parts[1]);
  if (head === "kx" && parts.length === 1) return true; // unlock token
  return KX_COMMAND_HEADS.has(head);
}

/** Strip a leading unlock-only token ("kx" / "login kx") leaving the real command. */
function stripUnlockPrefix(line) {
  let s = String(line || "").trim();
  const low = s.toLowerCase().replace(/[\[\]]/g, "");
  if (
    low === "kx" ||
    low === "login kx" ||
    low === "login-kx" ||
    low === "loginkx" ||
    low === "login_kx" ||
    /^login[-_]?kx$/.test(low)
  ) {
    return "";
  }
  if (/^kx\s+/i.test(s)) s = s.replace(/^kx\s+/i, "").trim();
  return s;
}

function isUnlockToken(line) {
  const raw = String(line || "").trim();
  if (!raw) return false;
  const low = raw.toLowerCase().replace(/[\[\]]/g, "");
  if (low === "kx" || low === "login kx" || /^login[-_]?kx$/.test(low)) return true;
  return looksLikeKxCommand(raw);
}

module.exports = {
  isLoginCommand,
  isClientOnlyArgv,
  lowerToken,
  looksLikeKxCommand,
  stripUnlockPrefix,
  isUnlockToken,
  KX_COMMAND_HEADS,
};
