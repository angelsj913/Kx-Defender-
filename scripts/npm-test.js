"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");
const { ensureSetup, ROOT, readState, spawnOpts } = require("./npm-setup");

const terminal = spawnSync(process.execPath, ["scripts/test-terminal-ui.js"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: false,
});
if (terminal.status !== 0) process.exit(terminal.status == null ? 1 : terminal.status);

const doctor = spawnSync(process.execPath, ["scripts/test-doctor.js"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: false,
});
if (doctor.status !== 0) process.exit(doctor.status == null ? 1 : doctor.status);

const releaseState = spawnSync(process.execPath, ["scripts/test-release-state.js"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: false,
});
if (releaseState.status !== 0) process.exit(releaseState.status == null ? 1 : releaseState.status);

const security = spawnSync(process.execPath, ["scripts/test-security.js"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: false,
});
if (security.status !== 0) process.exit(security.status == null ? 1 : security.status);

const commandStore = spawnSync(process.execPath, ["scripts/test-command-store.js"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: false,
});
if (commandStore.status !== 0) process.exit(commandStore.status == null ? 1 : commandStore.status);

const packageTest = spawnSync(process.execPath, ["scripts/test-package.js"], {
  cwd: ROOT,
  stdio: "inherit",
  shell: false,
});
if (packageTest.status !== 0) process.exit(packageTest.status == null ? 1 : packageTest.status);

const runtime = ensureSetup();
const py = runtime.python || readState().python;
const pythonTestHome = fs.mkdtempSync(path.join(os.tmpdir(), "kx-python-tests-"));
const pythonTestEnv = {
  ...process.env,
  KX_HOME: pythonTestHome,
};
delete pythonTestEnv.KX_OPERATOR_DB;
delete pythonTestEnv.KX_RUN_DB;
const pytest = spawnSync(py, ["-c", "import pytest"], {
  ...spawnOpts(py, { cwd: ROOT, stdio: "ignore" }),
  env: pythonTestEnv,
});
if (pytest.status !== 0) {
  const install = spawnSync(py, ["-m", "pip", "install", "-e", ".[dev]"], {
    ...spawnOpts(py, { cwd: ROOT, stdio: "inherit" }),
    env: pythonTestEnv,
  });
  if (install.status !== 0) {
    fs.rmSync(pythonTestHome, { recursive: true, force: true });
    process.exit(install.status == null ? 1 : install.status);
  }
}
const res = spawnSync(py, ["-m", "pytest", "-q"], {
  ...spawnOpts(py, { cwd: ROOT, stdio: "inherit" }),
  env: pythonTestEnv,
});
fs.rmSync(pythonTestHome, { recursive: true, force: true });
process.exit(res.status == null ? 1 : res.status);
