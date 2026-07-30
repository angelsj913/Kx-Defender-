"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const VENV = path.join(ROOT, ".venv");
const STATE = path.join(ROOT, ".kx-runtime.json");

function log(msg) {
  console.log(`[Kx] ${msg}`);
}

function isWin() {
  return process.platform === "win32";
}

function venvPython() {
  return isWin()
    ? path.join(VENV, "Scripts", "python.exe")
    : path.join(VENV, "bin", "python");
}

function venvKx() {
  return isWin()
    ? path.join(VENV, "Scripts", "kx.exe")
    : path.join(VENV, "bin", "kx");
}

function readState() {
  try {
    return JSON.parse(fs.readFileSync(STATE, "utf8"));
  } catch {
    return null;
  }
}

function writeState(state) {
  fs.writeFileSync(STATE, JSON.stringify(state, null, 2));
}

function run(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, {
    cwd: ROOT,
    stdio: "inherit",
    shell: isWin(),
    ...opts,
  });
  if (res.error) throw res.error;
  if (res.status !== 0) {
    const err = new Error(`Command failed (${res.status}): ${cmd} ${args.join(" ")}`);
    err.status = res.status;
    throw err;
  }
  return res;
}

function runCapture(cmd, args) {
  const res = spawnSync(cmd, args, {
    cwd: ROOT,
    encoding: "utf8",
    shell: isWin(),
  });
  if (res.status !== 0) return null;
  return (res.stdout || "").trim();
}

function findPython() {
  const candidates = isWin()
    ? [
        ["py", ["-3.12"]],
        ["py", ["-3.11"]],
        ["py", ["-3.10"]],
        ["py", ["-3.9"]],
        ["py", ["-3"]],
        ["python", []],
        ["python3", []],
      ]
    : [
        ["python3", []],
        ["python", []],
      ];

  for (const [cmd, baseArgs] of candidates) {
    const out = runCapture(cmd, [
      ...baseArgs,
      "-c",
      "import sys; assert sys.version_info[:2] >= (3, 9); print(sys.executable)",
    ]);
    if (out) {
      return {
        cmd,
        baseArgs,
        executable: out.split(/\r?\n/).filter(Boolean).pop(),
      };
    }
  }
  return null;
}

function resolveRuntime() {
  const state = readState();
  if (state && state.python && fs.existsSync(state.python)) {
    return state;
  }
  if (fs.existsSync(venvPython()) && fs.existsSync(venvKx())) {
    const runtime = { mode: "venv", python: venvPython(), kx: venvKx() };
    writeState(runtime);
    return runtime;
  }
  return null;
}

function verifyKx(pythonPath) {
  const out = runCapture(pythonPath, [
    "-c",
    "from kx_defender.kx_cli import main; print('ok')",
  ]);
  return Boolean(out && out.includes("ok"));
}

function setup() {
  log("Kx-Defender npm setup (Self-Built Only)");
  if (!fs.existsSync(path.join(ROOT, "pyproject.toml"))) {
    throw new Error("pyproject.toml not found. Run npm install from the repo root.");
  }

  const found = findPython();
  if (!found) {
    throw new Error(
      "Python 3.9+ not found. Install Python and ensure `py`/`python`/`python3` is on PATH."
    );
  }
  log(`Python: ${found.executable}`);

  let runtime = null;

  // Prefer venv
  try {
    if (!fs.existsSync(venvPython())) {
      log("Creating .venv ...");
      run(found.executable, ["-m", "venv", VENV]);
    }
    const py = venvPython();
    log("Installing into .venv ...");
    run(py, ["-m", "pip", "install", "--upgrade", "pip"]);
    run(py, ["-m", "pip", "install", "-e", ".[dev]"]);
    if (!fs.existsSync(venvKx()) && !verifyKx(py)) {
      throw new Error("kx not importable in venv");
    }
    runtime = {
      mode: "venv",
      python: py,
      kx: fs.existsSync(venvKx()) ? venvKx() : null,
    };
  } catch (err) {
    log(`venv install failed (${err.message || err}); falling back to user/site install ...`);
    // Cleanup broken venv dir if empty/broken
    try {
      if (fs.existsSync(VENV)) {
        fs.rmSync(VENV, { recursive: true, force: true });
      }
    } catch (_) {
      /* ignore */
    }
    run(found.executable, ["-m", "pip", "install", "--upgrade", "pip"]);
    run(found.executable, ["-m", "pip", "install", "--user", "-e", ".[dev]"]);
    if (!verifyKx(found.executable)) {
      throw new Error("kx_defender import failed after fallback install");
    }
    runtime = {
      mode: "user",
      python: found.executable,
      kx: null,
    };
  }

  writeState(runtime);
  log("Setup complete.");
  log("Next: npm start");
  return runtime;
}

function ensureSetup() {
  let runtime = resolveRuntime();
  if (runtime && (runtime.kx || verifyKx(runtime.python))) return runtime;
  return setup();
}

function runKx(args, opts = {}) {
  const runtime = ensureSetup();
  if (runtime.kx && fs.existsSync(runtime.kx)) {
    return spawnSync(runtime.kx, args, {
      cwd: ROOT,
      stdio: "inherit",
      shell: isWin(),
      ...opts,
    });
  }
  // python -c launcher
  const code =
    "import sys; from kx_defender.kx_cli import main; sys.argv=['kx']+sys.argv[1:]; main()";
  return spawnSync(runtime.python, ["-c", code, ...args], {
    cwd: ROOT,
    stdio: "inherit",
    shell: isWin(),
    ...opts,
  });
}

module.exports = {
  ROOT,
  VENV,
  ensureSetup,
  setup,
  runKx,
  isWin,
  log,
  readState,
};

if (require.main === module) {
  try {
    setup();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
}
