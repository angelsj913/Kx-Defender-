"use strict";

const assert = require("assert");
const {
  isLoginCommand,
  isClientOnlyArgv,
  looksLikeKxCommand,
  stripUnlockPrefix,
  isUnlockToken,
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
assert.strictEqual(stripUnlockPrefix("login_kx"), "");
assert.strictEqual(stripUnlockPrefix("login-kx"), "");
assert.strictEqual(stripUnlockPrefix("loginkx"), "");
assert.strictEqual(stripUnlockPrefix("host-kx-01"), "host-kx-01");
assert.strictEqual(looksLikeKxCommand("host-kx-01"), false);
assert.strictEqual(looksLikeKxCommand("login_kx"), false);
assert.strictEqual(isUnlockToken("kx"), true);
assert.strictEqual(isUnlockToken("login_kx"), true);
assert.strictEqual(isUnlockToken("sentry"), true);
assert.strictEqual(isUnlockToken("host-kx-01"), false);
assert.strictEqual(isUnlockToken("asdf"), false);

console.log("test_kx_routing.js OK");
