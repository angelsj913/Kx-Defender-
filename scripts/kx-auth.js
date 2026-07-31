"use strict";

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

const KX_DIR = process.env.KX_HOME || path.join(os.homedir(), ".kx-defender");
const USERS_FILE = path.join(KX_DIR, "users.json");
const CONFIG_FILE = path.join(KX_DIR, "config.json");
let nonTtyLines = null;

function hash(pw) {
  const salt = crypto.randomBytes(16).toString("hex");
  const digest = crypto.scryptSync(String(pw), salt, 64).toString("hex");
  return `scrypt$${salt}$${digest}`;
}

function verify(password, stored) {
  if (typeof stored !== "string") return false;
  if (stored.startsWith("scrypt$")) {
    const [, salt, expected] = stored.split("$");
    if (!salt || !/^[a-f0-9]{128}$/i.test(expected || "")) return false;
    const actual = crypto.scryptSync(String(password), salt, 64).toString("hex");
    return crypto.timingSafeEqual(Buffer.from(actual, "hex"), Buffer.from(expected, "hex"));
  }
  if (!/^[a-f0-9]{64}$/i.test(stored)) return false;
  const legacy = crypto.createHash("sha256").update(String(password)).digest("hex");
  return crypto.timingSafeEqual(Buffer.from(legacy, "hex"), Buffer.from(stored, "hex"));
}

function load() {
  try {
    return JSON.parse(fs.readFileSync(USERS_FILE, "utf8"));
  } catch (_) {
    return { users: [] };
  }
}

function save(store) {
  fs.mkdirSync(KX_DIR, { recursive: true });
  fs.writeFileSync(USERS_FILE, JSON.stringify(store, null, 2));
}

function init() {
  fs.mkdirSync(KX_DIR, { recursive: true });
  if (!fs.existsSync(CONFIG_FILE)) {
    fs.writeFileSync(CONFIG_FILE, `${JSON.stringify({ lang: "en" }, null, 2)}\n`, {
      encoding: "utf8",
      mode: 0o600,
    });
  }
  if (fs.existsSync(USERS_FILE)) return null;
  const password = process.env.KX_INITIAL_ADMIN_PASSWORD || "admin";
  save({ users: [{ username: "admin", passwordHash: hash(password), role: "admin" }] });
  return process.env.KX_INITIAL_ADMIN_PASSWORD ? null : password;
}

function readLine(prompt) {
  if (!process.stdin.isTTY) {
    process.stdout.write(prompt);
    if (nonTtyLines === null) {
      nonTtyLines = fs.readFileSync(0, "utf8").split(/\r?\n/);
    }
    return Promise.resolve(String(nonTtyLines.shift() || "").trim());
  }
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: true });
    rl.question(prompt, (ans) => { rl.close(); resolve(ans.trim()); });
  });
}

function readSecret(prompt) {
  if (!process.stdin.isTTY) return readLine(prompt);
  return new Promise((resolve) => {
    process.stdout.write(prompt);
    let buf = "";

    const onData = (data) => {
      const ch = String(data);
      const code = ch.length === 1 ? ch.charCodeAt(0) : -1;
      if (ch === "\r" || ch === "\n" || code === 4) {
        // enter or ctrl+d
        if (process.stdin.isTTY) process.stdin.setRawMode(false);
        process.stdin.removeListener("data", onData);
        process.stdin.pause();
        process.stdout.write("\n");
        resolve(buf);
      } else if (code === 3) {
        // ctrl+c
        if (process.stdin.isTTY) process.stdin.setRawMode(false);
        process.stdout.write("\n");
        process.exit(130);
      } else if (code === 127 || code === 8) {
        // backspace / del
        buf = buf.slice(0, -1);
      } else if (code > 31) {
        buf += ch;
      }
    };

    if (process.stdin.isTTY) process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.on("data", onData);
  });
}

function takeBufferedInput() {
  if (nonTtyLines === null) return null;
  const remaining = nonTtyLines.join("\n");
  nonTtyLines = [];
  return remaining;
}

async function login() {
  const initialPassword = init();
  const useColor = process.stdout.isTTY && !process.env.NO_COLOR &&
    !process.env.KX_NO_COLOR && process.env.TERM !== "dumb";
  const WARN = useColor ? "\x1b[33m" : "";
  const RESET = useColor ? "\x1b[0m" : "";

  if (initialPassword) {
    process.stdout.write(`${WARN}  First-run login: admin / ${initialPassword} (change it after login)${RESET}\n`);
  }

  for (let i = 0; i < 3; i++) {
    const username = await readLine("  username: ");
    const password = await readSecret("  password: ");
    const store = load();
    const user = store.users.find((u) => u.username === username);
    if (user && verify(password, user.passwordHash)) {
      if (!user.passwordHash.startsWith("scrypt$")) {
        user.passwordHash = hash(password);
        save(store);
      }
      return user;
    }
    const left = 2 - i;
    if (left > 0) process.stdout.write(`${WARN}  incorrect. ${left} attempt(s) left${RESET}\n\n`);
  }
  process.stdout.write("  access denied.\n");
  process.exit(1);
}

function handleAuthCmd(args, store, actor) {
  const cmd = (args[0] || "").toLowerCase();

  if (!actor || actor.role !== "admin") {
    console.error("  admin role required");
    return true;
  }

  if (cmd === "users") {
    for (const u of store.users) console.log(`  ${u.role === "admin" ? "*" : " "} ${u.username}`);
    return true;
  }
  if (cmd === "useradd") {
    const [, uname, pw] = args;
    if (!uname || !pw) { console.error("  useradd <username> <password>"); return true; }
    if (store.users.find((u) => u.username === uname)) { console.error(`  '${uname}' exists`); return true; }
    store.users.push({ username: uname, passwordHash: hash(pw), role: "user" });
    save(store);
    console.log(`  '${uname}' added`);
    return true;
  }
  if (cmd === "userdel") {
    const uname = args[1];
    if (!uname) { console.error("  userdel <username>"); return true; }
    if (uname === "admin") { console.error("  cannot delete admin"); return true; }
    const idx = store.users.findIndex((u) => u.username === uname);
    if (idx === -1) { console.error(`  '${uname}' not found`); return true; }
    store.users.splice(idx, 1);
    save(store);
    console.log(`  '${uname}' removed`);
    return true;
  }
  if (cmd === "passwd") {
    const [, uname, newPw] = args;
    if (!uname || !newPw) { console.error("  passwd <username> <newpassword>"); return true; }
    const user = store.users.find((u) => u.username === uname);
    if (!user) { console.error(`  '${uname}' not found`); return true; }
    user.passwordHash = hash(newPw);
    save(store);
    console.log(`  password updated for '${uname}'`);
    return true;
  }
  return false;
}

module.exports = {
  login,
  handleAuthCmd,
  load,
  init,
  hash,
  verify,
  readLine,
  readSecret,
  takeBufferedInput,
};
