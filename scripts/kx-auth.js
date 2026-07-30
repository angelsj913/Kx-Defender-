"use strict";

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");

const KX_DIR = path.join(os.homedir(), ".kx-defender");
const USERS_FILE = path.join(KX_DIR, "users.json");

function hash(pw) {
  return crypto.createHash("sha256").update(String(pw)).digest("hex");
}

function load() {
  try {
    return JSON.parse(fs.readFileSync(USERS_FILE, "utf8"));
  } catch (_) {
    return { users: [{ username: "admin", passwordHash: hash("admin"), role: "admin" }] };
  }
}

function save(store) {
  fs.mkdirSync(KX_DIR, { recursive: true });
  fs.writeFileSync(USERS_FILE, JSON.stringify(store, null, 2));
}

function init() {
  if (!fs.existsSync(USERS_FILE)) {
    save({ users: [{ username: "admin", passwordHash: hash("admin"), role: "admin" }] });
  }
}

function readLine(prompt) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: true });
    rl.question(prompt, (ans) => { rl.close(); resolve(ans.trim()); });
  });
}

function readSecret(prompt) {
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
        process.exit(0);
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

async function login() {
  init();
  const WARN = "\x1b[38;2;255;176;0m";
  const RESET = "\x1b[0m";

  for (let i = 0; i < 3; i++) {
    const username = await readLine("  username: ");
    const password = await readSecret("  password: ");
    const store = load();
    const user = store.users.find((u) => u.username === username);
    if (user && user.passwordHash === hash(password)) return user;
    const left = 2 - i;
    if (left > 0) process.stdout.write(`${WARN}  incorrect. ${left} attempt(s) left${RESET}\n\n`);
  }
  process.stdout.write("  access denied.\n");
  process.exit(1);
}

function handleAuthCmd(args, store) {
  const cmd = (args[0] || "").toLowerCase();

  if (cmd === "users") {
    for (const u of store.users) console.log(`  ${u.role === "admin" ? "*" : " "} ${u.username}`);
    return true;
  }
  if (cmd === "useradd") {
    const [, uname, pw = "password"] = args;
    if (!uname) { console.error("  useradd <username> [password]"); return true; }
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

module.exports = { login, handleAuthCmd, load, init, hash };
