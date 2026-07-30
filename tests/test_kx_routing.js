"use strict";

const assert = require("assert");
const {
  isLoginCommand,
  isClientOnlyArgv,
  looksLikeKxCommand,
  stripUnlockPrefix,
} = require("../scripts/kx-routing");

assert.strictEqual(isLoginCommand("login", []), true);
assert.strictEqual(isLoginCommand("login", ["kx"]), true);
assert.strictEqual(isLoginCommand("login_kx", []), true);
assert.strictEqual(isClientOnlyArgv(["login_kx"]), true);
assert.strictEqual(isClientOnlyArgv(["kx", "login_kx"]), true);
assert.strictEqual(isLoginCommand("kx", ["login"]), true);
assert.strictEqual(isLoginCommand("client", []), false);
assert.strictEqual(isLoginCommand("roast", ["tickets", "--realm", "kx.lab"]), false);
assert.strictEqual(isLoginCommand("watch", ["procs", "--at", "host-kx-01"]), false);
assert.strictEqual(isLoginCommand("sentry", []), false);

assert.strictEqual(isClientOnlyArgv([]), true);
assert.strictEqual(isClientOnlyArgv(["kx"]), true);
assert.strictEqual(isClientOnlyArgv(["client"]), true);
assert.strictEqual(isClientOnlyArgv(["hud"]), true);
assert.strictEqual(isClientOnlyArgv(["roast", "tickets"]), false);
assert.strictEqual(isClientOnlyArgv(["/h"]), false);
assert.strictEqual(isClientOnlyArgv(["lang", "ko"]), false);

assert.strictEqual(looksLikeKxCommand("sentry"), true);
assert.strictEqual(looksLikeKxCommand("kx sentry"), true);
assert.strictEqual(looksLikeKxCommand("roast tickets"), true);
assert.strictEqual(looksLikeKxCommand("hello world"), false);
assert.strictEqual(stripUnlockPrefix("kx"), "");
assert.strictEqual(stripUnlockPrefix("kx sentry"), "sentry");
assert.strictEqual(stripUnlockPrefix("sentry"), "sentry");

console.log("test_kx_routing.js OK");
