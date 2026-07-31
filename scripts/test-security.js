"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const temp = fs.mkdtempSync(path.join(os.tmpdir(), "kx-security-test-"));
const home = path.join(temp, ".kx-defender");
fs.mkdirSync(home, { recursive: true });
const auth = require("./kx-auth");

const freshHome = path.join(temp, "fresh");
let result = spawnSync(
  process.execPath,
  ["-e", "require(process.argv[1]).init()", path.join(__dirname, "kx-auth.js")],
  { env: { ...process.env, KX_HOME: freshHome }, encoding: "utf8", shell: false }
);
assert.strictEqual(result.status, 0, result.stderr);
assert.strictEqual(JSON.parse(fs.readFileSync(path.join(freshHome, "config.json"))).lang, "en");
result = spawnSync(
  process.execPath,
  [path.join(__dirname, "kx-security.js"), "status", "--json"],
  { env: { ...process.env, KX_HOME: freshHome }, encoding: "utf8", shell: false }
);
assert.strictEqual(result.status, 0, result.stderr);
assert.strictEqual(JSON.parse(result.stdout).defaultPassword, true);

const secretHash = auth.hash("admin");
fs.writeFileSync(
  path.join(home, "users.json"),
  JSON.stringify({ users: [{ username: "admin", passwordHash: secretHash, role: "admin" }] })
);
fs.writeFileSync(path.join(home, "config.json"), JSON.stringify({ lang: "en" }));

const env = { ...process.env, KX_HOME: home, NO_COLOR: "1" };
result = spawnSync(process.execPath, [path.join(__dirname, "kx-security.js"), "status", "--json"], {
  env,
  encoding: "utf8",
  shell: false,
});
assert.strictEqual(result.status, 0, result.stderr);
let status = JSON.parse(result.stdout);
assert.strictEqual(status.defaultPassword, true);
assert.strictEqual(status.language, "en");
assert(!result.stdout.includes(secretHash));
assert(!/passwordHash|scrypt\$/.test(result.stdout));

const security = require("./kx-security");
security.applyWizard({ home, lang: "ko", password: "changed-password" });
status = security.getStatus({ home });
assert.strictEqual(status.defaultPassword, false);
assert.strictEqual(status.language, "ko");
assert.strictEqual(auth.verify("changed-password", JSON.parse(fs.readFileSync(path.join(home, "users.json"))).users[0].passwordHash), true);

result = spawnSync(
  process.execPath,
  [path.join(__dirname, "npm-kx.js"), "security", "status", "--json"],
  { env, encoding: "utf8", shell: false }
);
assert.strictEqual(result.status, 0, result.stderr);
assert.strictEqual(JSON.parse(result.stdout).defaultPassword, false);
assert(!/passwordHash|scrypt\$|changed-password/.test(result.stdout));

assert.throws(
  () => security.applyWizard({ home, lang: "en", password: "short" }),
  /at least 8 characters/
);
result = spawnSync(
  process.execPath,
  [path.join(__dirname, "npm-kx.js"), "setup", "wizard"],
  { env, input: "en\nn\n", encoding: "utf8", shell: false }
);
assert.strictEqual(result.status, 0, result.stderr);
assert.match(result.stdout, /Security: ready/);
assert.strictEqual(security.getStatus({ home }).defaultPassword, false);

fs.rmSync(temp, { recursive: true, force: true });
console.log("security tests passed");
