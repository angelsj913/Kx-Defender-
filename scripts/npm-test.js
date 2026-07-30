"use strict";

const { spawnSync } = require("child_process");
const { ensureSetup, ROOT, isWin, readState } = require("./npm-setup");

const runtime = ensureSetup();
const py = runtime.python || readState().python;
const res = spawnSync(py, ["-m", "pytest", "-q"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: isWin(),
});
process.exit(res.status == null ? 1 : res.status);
