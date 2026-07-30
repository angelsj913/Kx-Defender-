"use strict";

const { spawnSync } = require("child_process");
const { ensureSetup, ROOT, isWin, readState } = require("./npm-setup");

const runtime = ensureSetup();
const py = runtime.python || readState().python;
const pytest = spawnSync(py, ["-c", "import pytest"], {
  cwd: ROOT,
  stdio: "ignore",
  shell: isWin(),
});
if (pytest.status !== 0) {
  const install = spawnSync(py, ["-m", "pip", "install", "-e", ".[dev]"], {
    cwd: ROOT,
    stdio: "inherit",
    shell: isWin(),
  });
  if (install.status !== 0) process.exit(install.status == null ? 1 : install.status);
}
const res = spawnSync(py, ["-m", "pytest", "-q"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: isWin(),
});
process.exit(res.status == null ? 1 : res.status);
