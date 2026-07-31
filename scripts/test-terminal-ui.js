"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const {
  clearScreen,
  renderDashboard,
  renderLoading,
  renderPromptTop,
  stringWidth,
  stripAnsi,
} = require("./terminal-ui");
const { spawnOptions } = require("./kx-update");
const { buildCliArgs } = require("./kx-tui");

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

assert.match(
  renderLoading({ width: 80, percent: 20, label: "Loading", frame: 1, color: true }),
  /\x1b\[/,
  "TTY loading frames must retain the animated color gradient"
);

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
const updaterSource = fs.readFileSync(path.join(__dirname, "kx-update.js"), "utf8");
assert.match(
  updaterSource,
  /reset", "--hard", "FETCH_HEAD"/,
  "updater must work when the fetched branch has no local tracking ref"
);
assert.deepStrictEqual(buildCliArgs(["sentry"]), ["--pretty", "sentry"]);
assert.deepStrictEqual(
  buildCliArgs(["report", "--json"]),
  ["report", "--json"],
  "command-level JSON flags must reach the Python CLI"
);

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

const authDir = fs.mkdtempSync(path.join(os.tmpdir(), "kx-auth-pipe-test-"));
const authScript = [
  "const auth = require(process.argv[1]);",
  "auth.login().then((user) => {",
  "  if (user.username !== 'admin') process.exit(2);",
  "  console.log('LOGIN_OK');",
  "});",
].join("\n");
const authResult = spawnSync(process.execPath, ["-e", authScript, path.join(__dirname, "kx-auth.js")], {
  input: "admin\nadmin\n",
  encoding: "utf8",
  shell: false,
  env: {
    ...process.env,
    HOME: authDir,
    USERPROFILE: authDir,
    NO_COLOR: "1",
  },
});
assert.strictEqual(authResult.status, 0, authResult.stderr);
assert.match(authResult.stdout, /LOGIN_OK/);
assert.doesNotMatch(authResult.stdout, /\x1b\[/, "NO_COLOR login must not emit ANSI");
fs.rmSync(authDir, { recursive: true, force: true });

const packageVersion = require("../package.json").version;
const setupVersion = require("./npm-setup").SETUP_VERSION;
assert.strictEqual(setupVersion, packageVersion, "setup version must follow package.json");

console.log("terminal UI tests passed");
