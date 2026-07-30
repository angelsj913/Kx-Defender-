"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");
const https = require("https");
const http = require("http");

const ROOT = path.resolve(__dirname, "..");
const VENV = path.join(ROOT, ".venv");
const STATE = path.join(ROOT, ".kx-runtime.json");
const PY_HOME = path.join(os.homedir(), ".kx-defender", "python");
const PY_TAG = "20260728";
const PY_VERSION = "3.12.13";

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
    windowsHide: true,
  });
  if (res.status !== 0) return null;
  return (res.stdout || "").trim();
}

function probePython(executable, baseArgs = []) {
  if (!executable) return null;
  // Skip Microsoft Store stub
  if (/\\WindowsApps\\/i.test(executable)) return null;
  if (!fs.existsSync(executable) && !["py", "python", "python3"].includes(executable)) {
    // bare command names ok
  }
  const out = runCapture(executable, [
    ...baseArgs,
    "-c",
    "import sys; assert sys.version_info[:2] >= (3, 9); print(sys.executable)",
  ]);
  if (!out) return null;
  const resolved = out.split(/\r?\n/).filter(Boolean).pop();
  if (!resolved || /\\WindowsApps\\/i.test(resolved)) return null;
  return {
    cmd: executable,
    baseArgs,
    executable: resolved,
  };
}

function windowsPythonCandidates() {
  const homes = [
    process.env.LOCALAPPDATA,
    process.env.PROGRAMFILES,
    process.env["ProgramFiles(x86)"],
    path.join(os.homedir(), "AppData", "Local"),
  ].filter(Boolean);

  const found = [];
  for (const home of homes) {
    const roots = [
      path.join(home, "Programs", "Python"),
      path.join(home, "Python"),
      home,
    ];
    for (const root of roots) {
      if (!fs.existsSync(root)) continue;
      let entries = [];
      try {
        entries = fs.readdirSync(root);
      } catch {
        continue;
      }
      for (const name of entries) {
        if (!/^Python3\d+/i.test(name) && !/^python-?3/i.test(name)) continue;
        const exe = path.join(root, name, "python.exe");
        if (fs.existsSync(exe)) found.push(exe);
      }
      const direct = path.join(root, "python.exe");
      if (fs.existsSync(direct)) found.push(direct);
    }
  }
  // Portable bootstrap location
  const portable = path.join(PY_HOME, "python.exe");
  if (fs.existsSync(portable)) found.unshift(portable);
  const portableUnix = path.join(PY_HOME, "bin", "python3");
  if (fs.existsSync(portableUnix)) found.unshift(portableUnix);
  return found;
}

function findPython() {
  // Already-bootstrapped portable runtime
  const portableWin = path.join(PY_HOME, "python.exe");
  const portableUnix = path.join(PY_HOME, "bin", "python3");
  for (const p of [portableWin, portableUnix, path.join(PY_HOME, "bin", "python")]) {
    const hit = probePython(p);
    if (hit) return hit;
  }

  const commandCandidates = isWin()
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

  for (const [cmd, baseArgs] of commandCandidates) {
    const hit = probePython(cmd, baseArgs);
    if (hit) return hit;
  }

  if (isWin()) {
    for (const exe of windowsPythonCandidates()) {
      const hit = probePython(exe);
      if (hit) return hit;
    }
  }

  return null;
}

function platformTriple() {
  const arch = process.arch; // x64, arm64
  if (isWin()) {
    if (arch !== "x64" && arch !== "arm64") {
      throw new Error(`Unsupported Windows arch: ${arch}`);
    }
    // windows arm64 build naming may differ; prefer x64 for now
    return "x86_64-pc-windows-msvc";
  }
  if (process.platform === "darwin") {
    return arch === "arm64" ? "aarch64-apple-darwin" : "x86_64-apple-darwin";
  }
  // linux
  return arch === "arm64" ? "aarch64-unknown-linux-gnu" : "x86_64-unknown-linux-gnu";
}

function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    const get = (u, redirects = 0) => {
      if (redirects > 10) return reject(new Error("Too many redirects"));
      const lib = u.startsWith("https") ? https : http;
      lib
        .get(u, (res) => {
          if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            res.resume();
            return get(res.headers.location, redirects + 1);
          }
          if (res.statusCode !== 200) {
            res.resume();
            return reject(new Error(`Download failed HTTP ${res.statusCode}`));
          }
          res.pipe(file);
          file.on("finish", () => file.close(() => resolve(dest)));
        })
        .on("error", reject);
    };
    get(url);
  });
}

function extractTarGz(archive, destDir) {
  fs.mkdirSync(destDir, { recursive: true });
  // Windows 10+ ships tar.exe
  const res = spawnSync("tar", ["-xzf", archive, "-C", destDir], {
    stdio: "inherit",
    shell: isWin(),
  });
  if (res.status !== 0) {
    throw new Error("Failed to extract Python archive (tar)");
  }
}

async function bootstrapPortablePython() {
  log("Python not on PATH — downloading portable CPython (one-time) ...");
  const triple = platformTriple();
  const asset = `cpython-${PY_VERSION}+${PY_TAG}-${triple}-install_only.tar.gz`;
  const url = `https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/${asset}`;
  const cacheDir = path.join(os.homedir(), ".kx-defender", "cache");
  fs.mkdirSync(cacheDir, { recursive: true });
  const archive = path.join(cacheDir, asset);
  if (!fs.existsSync(archive) || fs.statSync(archive).size < 1_000_000) {
    log(`Fetching ${asset} ...`);
    await downloadFile(url, archive);
  }

  const staging = path.join(os.homedir(), ".kx-defender", "python-staging");
  fs.rmSync(staging, { recursive: true, force: true });
  fs.mkdirSync(staging, { recursive: true });
  extractTarGz(archive, staging);

  // install_only layout: staging/python/...
  const extracted = path.join(staging, "python");
  if (!fs.existsSync(extracted)) {
    throw new Error("Portable Python archive layout unexpected");
  }
  fs.rmSync(PY_HOME, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(PY_HOME), { recursive: true });
  fs.renameSync(extracted, PY_HOME);
  fs.rmSync(staging, { recursive: true, force: true });

  const exe = isWin()
    ? path.join(PY_HOME, "python.exe")
    : path.join(PY_HOME, "bin", "python3");
  const hit = probePython(exe);
  if (!hit) {
    throw new Error("Portable Python installed but not runnable");
  }
  log(`Portable Python ready: ${hit.executable}`);
  return hit;
}

async function ensurePython() {
  if (process.env.KX_FORCE_PORTABLE === "1") {
    return bootstrapPortablePython();
  }
  let found = findPython();
  if (found) return found;
  found = await bootstrapPortablePython();
  return found;
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

async function setup() {
  log("Kx-Defender npm setup (Self-Built Only)");
  if (!fs.existsSync(path.join(ROOT, "pyproject.toml"))) {
    throw new Error("pyproject.toml not found. Run npm install from the repo root.");
  }

  const found = await ensurePython();
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
    try {
      if (fs.existsSync(VENV)) {
        fs.rmSync(VENV, { recursive: true, force: true });
      }
    } catch (_) {
      /* ignore */
    }
    // Ensure pip exists on portable builds
    run(found.executable, ["-m", "ensurepip", "--upgrade"]);
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
  return runtime;
}

function ensureSetup() {
  let runtime = resolveRuntime();
  if (runtime && (runtime.kx || verifyKx(runtime.python))) return runtime;
  // setup is async — bridge for sync callers
  const { spawnSync: ss } = require("child_process");
  // Run setup in-process via deasync-free approach: call async setup with Atomics wait? 
  // Simpler: expose syncSetup that blocks using child process self-invoke.
  return setupSync();
}

function setupSync() {
  // Run this file as CLI asynchronously via nested require of async setup using busy wait on promise — use child:
  const res = spawnSync(process.execPath, [path.join(__dirname, "npm-setup.js"), "--setup"], {
    cwd: ROOT,
    stdio: "inherit",
    env: process.env,
    shell: false,
  });
  if (res.status !== 0) {
    const err = new Error("Setup failed");
    err.status = res.status || 1;
    throw err;
  }
  const runtime = resolveRuntime();
  if (!runtime) {
    throw new Error("Setup finished but runtime state missing");
  }
  return runtime;
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
  setupSync,
  runKx,
  isWin,
  log,
  readState,
  findPython,
  ensurePython,
};

if (require.main === module) {
  const args = process.argv.slice(2);
  (async () => {
    try {
      if (args.includes("--setup") || args.length === 0) {
        await setup();
      }
    } catch (err) {
      console.error(`[Kx] ${err.message || err}`);
      process.exit(err.status || 1);
    }
  })();
}
