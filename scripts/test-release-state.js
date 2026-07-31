"use strict";

const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const release = require("./kx-release");
const { writeStableLauncher } = require("./kx-update");

const home = fs.mkdtempSync(path.join(os.tmpdir(), "kx-release-test-"));
const releases = path.join(home, "releases");

function makeRelease(commit, valid = true) {
  const app = path.join(releases, commit);
  fs.mkdirSync(path.join(app, "scripts"), { recursive: true });
  fs.writeFileSync(path.join(app, "package.json"), JSON.stringify({ name: "kx-defender", version: "0.5.0" }));
  if (valid) {
    fs.writeFileSync(
      path.join(app, "scripts", "npm-kx.js"),
      `"use strict"; console.log(${JSON.stringify(commit)});\n`
    );
  }
  return app;
}

const first = makeRelease("aaaa1111");
const second = makeRelease("bbbb2222");
const broken = makeRelease("cccc3333", false);

let state = release.activate({ home, app: first, commit: "aaaa1111", branch: "main" });
assert.strictEqual(state.current.commit, "aaaa1111");
assert.strictEqual(state.previous, null);

state = release.activate({ home, app: second, commit: "bbbb2222", branch: "main" });
assert.strictEqual(state.current.commit, "bbbb2222");
assert.strictEqual(state.previous.commit, "aaaa1111");

assert.throws(() => release.activate({ home, app: broken, commit: "cccc3333" }), /entry/);
state = release.readState(home);
assert.strictEqual(state.current.commit, "bbbb2222", "invalid release changed current");
assert.strictEqual(state.previous.commit, "aaaa1111");

state = release.rollback(home);
assert.strictEqual(state.current.commit, "aaaa1111");
assert.strictEqual(state.previous.commit, "bbbb2222");
assert.strictEqual(release.currentApp(home), first);
const launcher = writeStableLauncher(home);
let launched = require("child_process").spawnSync(process.execPath, [launcher, "kx"], {
  encoding: "utf8",
  shell: false,
});
assert.strictEqual(launched.status, 0, launched.stderr);
assert.strictEqual(launched.stdout.trim(), "aaaa1111");

release.rollback(home);
launched = require("child_process").spawnSync(process.execPath, [launcher, "kx"], {
  encoding: "utf8",
  shell: false,
});
assert.strictEqual(launched.stdout.trim(), "bbbb2222");
fs.mkdirSync(path.join(home, "control"), { recursive: true });
fs.writeFileSync(
  path.join(home, "control", "kx-update.js"),
  '"use strict"; console.log("CONTROL");\n'
);
launched = require("child_process").spawnSync(process.execPath, [launcher, "update", "status"], {
  encoding: "utf8",
  shell: false,
});
assert.strictEqual(launched.stdout.trim(), "CONTROL");

assert(
  fs.readdirSync(home).every((name) => !name.includes(".tmp-")),
  "atomic pointer temp file was left behind"
);

fs.rmSync(home, { recursive: true, force: true });
console.log("release state tests passed");
