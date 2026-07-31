"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const temp = fs.mkdtempSync(path.join(os.tmpdir(), "kx-command-store-"));
process.env.KX_HOME = temp;
delete require.cache[require.resolve("./kx-command-store")];
const store = require("./kx-command-store");

assert.strictEqual(store.recordHistory("sentry --scope lab --sim"), true);
assert.strictEqual(store.recordHistory("passwd admin visible-secret"), false);
assert.strictEqual(store.recordHistory("sentry --token visible-token --scope lab"), true);
let history = store.listHistory();
assert.strictEqual(history.length, 2);
assert.match(history[0].command, /<redacted>/);
assert(!JSON.stringify(history).includes("visible-token"));
assert(!JSON.stringify(history).includes("visible-secret"));
assert.strictEqual(store.searchHistory("scope").length, 2);

store.addFavorite("daily", "sentry --scope lab --sim");
assert.strictEqual(store.getFavorite("daily").command, "sentry --scope lab --sim");
assert.throws(
  () => store.addFavorite("unsafe", "sentry --token visible-token"),
  /sensitive/
);
store.addFavorite("live-check", "watch procs --scope lab --live");
assert.throws(() => store.prepareFavoriteRun("live-check"), /confirm-live/);
assert.strictEqual(
  store.prepareFavoriteRun("live-check", { confirmLive: true }),
  "watch procs --scope lab --live"
);

let cli = spawnSync(
  process.execPath,
  [path.join(__dirname, "npm-kx.js"), "favorite", "list", "--json"],
  { env: { ...process.env, KX_HOME: temp }, encoding: "utf8", shell: false }
);
assert.strictEqual(cli.status, 0, cli.stderr);
assert.strictEqual(JSON.parse(cli.stdout).favorites.length, 2);
cli = spawnSync(
  process.execPath,
  [path.join(__dirname, "npm-kx.js"), "history", "search", "sentry", "--json"],
  { env: { ...process.env, KX_HOME: temp }, encoding: "utf8", shell: false }
);
assert.strictEqual(cli.status, 0, cli.stderr);
assert.strictEqual(JSON.parse(cli.stdout).history.length, 2);

let completion = store.complete("sen");
assert(completion[0].includes("sentry"));
completion = store.complete("sentry auth");
assert(completion[0].includes("auth-anomalies"));
completion = store.complete("sentry auth-anomalies --s");
assert(completion[0].includes("--scope"));

store.clearHistory();
assert.deepStrictEqual(store.listHistory(), []);
fs.rmSync(temp, { recursive: true, force: true });
console.log("command store tests passed");
