"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const {
  clearScreen,
  renderDashboard,
  renderLoading,
  renderPromptTop,
  stringWidth,
  stripAnsi,
} = require("./terminal-ui");
const { spawnOptions } = require("./kx-update");

function lines(text) {
  return stripAnsi(text).split(/\r?\n/);
}

for (const width of [60, 72, 80, 100, 140]) {
  const dashboard = renderDashboard({
    width,
    height: 30,
    lang: "en",
    username: "admin",
    result: "Purpose: Validate the terminal layout.\nResult: OK",
    color: false,
  });
  assert(
    lines(dashboard).every((line) => stringWidth(line) <= width),
    `dashboard overflow at ${width} columns`
  );

  const loading = renderLoading({
    width,
    percent: 45,
    label: "Preparing security engines",
    frame: 2,
    color: false,
  });
  assert.match(loading, /45%/);
  assert(lines(loading).every((line) => stringWidth(line) <= width));
}

const percents = [0, 20, 45, 70, 90, 100];
assert.deepStrictEqual([...percents].sort((a, b) => a - b), percents);

assert.match(clearScreen(), /\x1b\[3J/, "launch must clear scrollback");
assert.match(renderPromptTop(72, false).trimStart(), /^┌─/);
assert.strictEqual(stringWidth("한글"), 4);
assert.strictEqual(stringWidth("\x1b[36mKX\x1b[0m"), 2);

const absoluteNode = path.join("C:\\", "Program Files", "nodejs", "node.exe");
assert.strictEqual(
  spawnOptions(absoluteNode, { platform: "win32" }).shell,
  false,
  "absolute executable paths must not be parsed by cmd.exe"
);
assert.strictEqual(spawnOptions("git", { platform: "win32" }).shell, true);

const configDir = fs.mkdtempSync(path.join(os.tmpdir(), "kx-terminal-test-"));
const oldConfig = process.env.KX_CONFIG;
const oldLang = process.env.KX_LANG;
process.env.KX_CONFIG = path.join(configDir, "config.json");
delete process.env.KX_LANG;
delete require.cache[require.resolve("./kx-shell")];
const { readLang, writeLang } = require("./kx-shell");
assert.strictEqual(readLang(), "en", "fresh installs must default to English");
writeLang("ko");
assert.strictEqual(readLang(), "ko", "Korean selection must persist");
writeLang("en");
assert.strictEqual(readLang(), "en", "English selection must persist");
if (oldConfig === undefined) delete process.env.KX_CONFIG;
else process.env.KX_CONFIG = oldConfig;
if (oldLang === undefined) delete process.env.KX_LANG;
else process.env.KX_LANG = oldLang;
fs.rmSync(configDir, { recursive: true, force: true });

const packageVersion = require("../package.json").version;
const setupVersion = require("./npm-setup").SETUP_VERSION;
assert.strictEqual(setupVersion, packageVersion, "setup version must follow package.json");

console.log("terminal UI tests passed");
