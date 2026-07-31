"use strict";

const assert = require("assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const { ROOT } = require("./npm-setup");

const npmCli = process.env.npm_execpath ||
  path.join(path.dirname(process.execPath), "node_modules", "npm", "bin", "npm-cli.js");
assert(fs.existsSync(npmCli), `npm CLI was not found: ${npmCli}`);
const result = spawnSync(process.execPath, [npmCli, "pack", "--dry-run", "--json"], {
  cwd: ROOT,
  encoding: "utf8",
  shell: false,
  windowsHide: true,
});
assert.strictEqual(result.status, 0, result.stderr);
const manifest = JSON.parse(result.stdout)[0];
const paths = manifest.files.map((entry) => entry.path.replace(/\\/g, "/"));

assert(paths.includes("scripts/terminal-ui.js"));
assert(paths.includes("scripts/kx-doctor.js"));
assert(paths.includes("scripts/kx-release.js"));
assert(paths.includes("services/orchestrator/kx_defender/kx_cli.py"));
assert(paths.includes("modules/defense/process_monitor.py"));
assert(
  paths.every((file) => !file.includes("__pycache__") && !/\.py[co]$/.test(file)),
  "npm package must not contain generated Python bytecode"
);
assert.strictEqual(manifest.version, require(path.join(ROOT, "package.json")).version);

console.log(`package tests passed (${manifest.entryCount} files)`);
