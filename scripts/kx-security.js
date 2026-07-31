#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { hash, verify, readLine, readSecret } = require("./kx-auth");

function resolveHome(home) {
  return path.resolve(home || process.env.KX_HOME || path.join(os.homedir(), ".kx-defender"));
}

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (_) {
    return fallback;
  }
}

function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, {
    encoding: "utf8",
    mode: 0o600,
  });
  fs.renameSync(temp, file);
  try {
    fs.chmodSync(file, 0o600);
  } catch (_) {
    // Windows ACLs are managed by the user's profile directory.
  }
}

function canAccess(file, mode) {
  try {
    fs.accessSync(file, mode);
    return true;
  } catch (_) {
    return false;
  }
}

function getStatus({ home } = {}) {
  const root = resolveHome(home);
  const configFile = path.join(root, "config.json");
  const usersFile = path.join(root, "users.json");
  const config = readJson(configFile, null);
  const store = readJson(usersFile, null);
  const users = store && Array.isArray(store.users) ? store.users : [];
  const admin = users.find((user) => user && user.username === "admin");
  const language = config && ["en", "ko"].includes(config.lang) ? config.lang : "invalid";
  const files = {
    config: {
      exists: fs.existsSync(configFile),
      readable: canAccess(configFile, fs.constants.R_OK),
      writable: canAccess(configFile, fs.constants.W_OK),
    },
    users: {
      exists: fs.existsSync(usersFile),
      readable: canAccess(usersFile, fs.constants.R_OK),
      writable: canAccess(usersFile, fs.constants.W_OK),
    },
  };
  const healthy =
    language !== "invalid" &&
    Boolean(admin && typeof admin.passwordHash === "string") &&
    Object.values(files).every((item) => item.exists && item.readable && item.writable);

  return {
    healthy,
    language,
    userCount: users.length,
    adminAccount: Boolean(admin),
    defaultPassword: Boolean(admin && verify("admin", admin.passwordHash)),
    files,
  };
}

function applyWizard({ home, lang, password } = {}) {
  const root = resolveHome(home);
  if (!["en", "ko"].includes(lang)) {
    throw new Error("language must be en or ko");
  }
  if (password !== undefined && String(password).length < 8) {
    throw new Error("new password must contain at least 8 characters");
  }

  const configFile = path.join(root, "config.json");
  const usersFile = path.join(root, "users.json");
  const config = readJson(configFile, {});
  const store = readJson(usersFile, { users: [] });
  if (!Array.isArray(store.users)) store.users = [];
  let admin = store.users.find((user) => user && user.username === "admin");
  if (!admin) {
    admin = { username: "admin", passwordHash: hash("admin"), role: "admin" };
    store.users.unshift(admin);
  }
  if (password !== undefined) admin.passwordHash = hash(String(password));
  config.lang = lang;
  atomicJson(configFile, config);
  atomicJson(usersFile, store);
  return getStatus({ home: root });
}

function formatStatus(status, permissionsOnly = false) {
  const lines = [];
  if (!permissionsOnly) {
    lines.push(`Security: ${status.healthy ? "ready" : "attention required"}`);
    lines.push(`Language: ${status.language}`);
    lines.push(`Admin account: ${status.adminAccount ? "present" : "missing"}`);
    lines.push(`Default password: ${status.defaultPassword ? "in use - change recommended" : "changed"}`);
  }
  for (const [name, access] of Object.entries(status.files)) {
    const state = access.exists && access.readable && access.writable ? "ok" : "attention required";
    lines.push(`${name} file permissions: ${state}`);
  }
  return lines.join("\n");
}

function printStatus(status, permissionsOnly = false) {
  console.log(formatStatus(status, permissionsOnly));
}

async function runWizard() {
  const current = getStatus();
  const requested = (await readLine(`Language [${current.language === "ko" ? "ko" : "en"}] (en/ko): `))
    .toLowerCase();
  const lang = requested || (current.language === "ko" ? "ko" : "en");
  if (!["en", "ko"].includes(lang)) throw new Error("language must be en or ko");

  let password;
  const change = (await readLine("Change the admin password now? [y/N]: ")).toLowerCase();
  if (change === "y" || change === "yes") {
    password = await readSecret("New password (8+ characters): ");
    const confirm = await readSecret("Confirm new password: ");
    if (password !== confirm) throw new Error("password confirmation does not match");
  }
  const status = applyWizard({ lang, password });
  printStatus(status);
}

async function changePassword() {
  const root = resolveHome();
  const store = readJson(path.join(root, "users.json"), { users: [] });
  const admin = Array.isArray(store.users)
    ? store.users.find((user) => user && user.username === "admin")
    : null;
  if (!admin || typeof admin.passwordHash !== "string") throw new Error("admin account is missing");
  const current = await readSecret("Current admin password: ");
  if (!verify(current, admin.passwordHash)) throw new Error("current password is incorrect");
  const password = await readSecret("New password (8+ characters): ");
  const confirm = await readSecret("Confirm new password: ");
  if (password !== confirm) throw new Error("password confirmation does not match");
  applyWizard({
    home: root,
    lang: getStatus({ home: root }).language,
    password,
  });
  console.log("Admin password changed.");
}

async function main(argv = process.argv.slice(2)) {
  const command = String(argv[0] || "status").toLowerCase();
  if (command === "status") {
    const status = getStatus();
    if (argv.includes("--json")) console.log(JSON.stringify(status, null, 2));
    else printStatus(status);
    return status.healthy ? 0 : 2;
  }
  if (command === "permissions") {
    const status = getStatus();
    if (argv.includes("--json")) console.log(JSON.stringify(status.files, null, 2));
    else printStatus(status, true);
    return status.healthy ? 0 : 2;
  }
  if (command === "wizard") {
    await runWizard();
    return 0;
  }
  if (command === "password") {
    await changePassword();
    return 0;
  }
  throw new Error("use: kx security status|permissions|password or kx setup wizard");
}

if (require.main === module) {
  main()
    .then((code) => {
      process.exitCode = code;
    })
    .catch((error) => {
      console.error(`[Kx] ${error.message || error}`);
      process.exitCode = 1;
    });
}

module.exports = { applyWizard, formatStatus, getStatus, main };
