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
  if (["login", "login-kx", "loginkx"].includes(a0)) return true;
  if (a0 === "kx" && ["login", "login-kx", "loginkx"].includes(a1)) return true;
  if (/^login[-_]?kx$/.test(a0)) return true;
  return false;
}

function isClientOnlyArgv(argv) {
  const args = argv || [];
  if (!args.length) return true;
  const a0 = lowerToken(args[0]);
  if (["login", "login-kx", "loginkx", "hud", "edex", "shell", "repl", "cli", "client"].includes(a0)) {
    return true;
  }
  if (a0 === "kx") {
    if (args.length === 1) return true;
    const a1 = lowerToken(args[1]);
    return ["login", "hud", "edex", "shell", "repl", "cli", "client", "login-kx", "loginkx"].includes(a1);
  }
  return false;
}

module.exports = { isLoginCommand, isClientOnlyArgv, lowerToken };
