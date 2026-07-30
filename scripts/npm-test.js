"use strict";

const path = require("path");
const { spawnSync } = require("child_process");
const { ensureSetup, ROOT, isWin, readState } = require("./npm-setup");

const runtime = ensureSetup();
const py = runtime.python || readState().python;
const route = spawnSync(process.execPath, [path.join(ROOT, "tests", "test_kx_routing.js")], {
  cwd: ROOT,
  stdio: "inherit",
});
if (route.status) process.exit(route.status == null ? 1 : route.status);
const res = spawnSync(py, ["-m", "pytest", "-q"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: isWin(),
});
process.exit(res.status == null ? 1 : res.status);
