"use strict";

/**
 * Kx-Defender runtime setup
 * - Finds system Python, or downloads portable CPython once
 * - Fully synchronous (reliable under npx on Windows)
 */

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const SETUP_VERSION = "0.1.6";
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
    windowsHide: true,
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
  if (/WindowsApps/i.test(String(executable))) return null;
  const out = runCapture(executable, [
    ...baseArgs,
    "-c",
    "import sys; assert sys.version_info[:2] >= (3, 9); print(sys.executable)",
  ]);
  if (!out) return null;
  const resolved = out.split(/\r?\n/).filter(Boolean).pop();
  if (!resolved || /WindowsApps/i.test(resolved)) return null;
  return { cmd: executable, baseArgs, executable: resolved };
}

function windowsPythonCandidates() {
  const homes = [
    process.env.LOCALAPPDATA,
    process.env.PROGRAMFILES,
    process.env["ProgramFiles(x86)"],
    path.join(os.homedir(), "AppData", "Local"),
    path.join(os.homedir(), "AppData", "Local", "Programs"),
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
  return found;
}

function findPython() {
  for (const p of [
    path.join(PY_HOME, "python.exe"),
    path.join(PY_HOME, "bin", "python3"),
    path.join(PY_HOME, "bin", "python"),
  ]) {
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
  const arch = process.arch;
  if (isWin()) return "x86_64-pc-windows-msvc";
  if (process.platform === "darwin") {
    return arch === "arm64" ? "aarch64-apple-darwin" : "x86_64-apple-darwin";
  }
  return arch === "arm64" ? "aarch64-unknown-linux-gnu" : "x86_64-unknown-linux-gnu";
}

function downloadFileSync(url, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });

  if (isWin()) {
    const ps = [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-Command",
      `[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '${url}' -OutFile '${dest.replace(/'/g, "''")}' -UseBasicParsing`,
    ];
    const res = spawnSync("powershell", ps, { stdio: "inherit", windowsHide: true });
    if (res.status === 0 && fs.existsSync(dest) && fs.statSync(dest).size > 1_000_000) {
      return dest;
    }
  }

  for (const [bin, args] of [
    ["curl", ["-fsSL", "-L", url, "-o", dest]],
    ["wget", ["-q", "-O", dest, url]],
  ]) {
    const res = spawnSync(bin, args, { stdio: "ignore", shell: isWin(), windowsHide: true });
    if (res.status === 0 && fs.existsSync(dest) && fs.statSync(dest).size > 1_000_000) {
      return dest;
    }
  }

  const waiter = `
const https=require('https');const http=require('http');const fs=require('fs');
const url=${JSON.stringify(url)}; const dest=${JSON.stringify(dest)};
function get(u,n){return new Promise((resolve,reject)=>{if(n>10)return reject(new Error('redirects'));
const lib=u.startsWith('https')?https:http;
lib.get(u,res=>{if(res.statusCode>=300&&res.statusCode<400&&res.headers.location){res.resume();return resolve(get(res.headers.location,n+1));}
if(res.statusCode!==200){res.resume();return reject(new Error('HTTP '+res.statusCode));}
const f=fs.createWriteStream(dest);res.pipe(f);f.on('finish',()=>f.close(()=>resolve()));f.on('error',reject);}).on('error',reject);});}
get(url,0).then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1);});
`;
  const r2 = spawnSync(process.execPath, ["-e", waiter], {
    stdio: "inherit",
    windowsHide: true,
  });
  if (r2.status !== 0 || !fs.existsSync(dest) || fs.statSync(dest).size < 1_000_000) {
    throw new Error(`Failed to download Python runtime`);
  }
  return dest;
}

function extractTarGz(archive, destDir) {
  fs.mkdirSync(destDir, { recursive: true });
  const res = spawnSync("tar", ["-xzf", archive, "-C", destDir], {
    stdio: "inherit",
    shell: isWin(),
    windowsHide: true,
  });
  if (res.status !== 0) {
    throw new Error(
      "Failed to extract Python archive. On Windows 10+, tar.exe is required."
    );
  }
}

function bootstrapPortablePython() {
  log(`Python not on PATH — downloading portable CPython once (${SETUP_VERSION}) ...`);
  const triple = platformTriple();
  const asset = `cpython-${PY_VERSION}+${PY_TAG}-${triple}-install_only.tar.gz`;
  const url = `https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/${asset}`;
  const cacheDir = path.join(os.homedir(), ".kx-defender", "cache");
  fs.mkdirSync(cacheDir, { recursive: true });
  const archive = path.join(cacheDir, asset);

  try {
    if (!fs.existsSync(archive) || fs.statSync(archive).size < 1_000_000) {
      log(`Fetching ${asset} ...`);
      downloadFileSync(url, archive);
    }
  } catch (err) {
    throw new Error(
      `Could not download Python (${err.message}). Check network access to github.com, then retry.`
    );
  }

  const staging = path.join(os.homedir(), ".kx-defender", "python-staging");
  fs.rmSync(staging, { recursive: true, force: true });
  fs.mkdirSync(staging, { recursive: true });
  extractTarGz(archive, staging);

  const extracted = path.join(staging, "python");
  if (!fs.existsSync(extracted)) {
    throw new Error("Portable Python archive layout unexpected");
  }
  fs.rmSync(PY_HOME, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(PY_HOME), { recursive: true });
  // Windows rename across volumes can fail — copy fallback
  try {
    fs.renameSync(extracted, PY_HOME);
  } catch {
    fs.cpSync(extracted, PY_HOME, { recursive: true });
  }
  fs.rmSync(staging, { recursive: true, force: true });

  const exe = isWin()
    ? path.join(PY_HOME, "python.exe")
    : path.join(PY_HOME, "bin", "python3");
  const hit = probePython(exe);
  if (!hit) {
    throw new Error(`Portable Python installed but not runnable: ${exe}`);
  }
  log(`Portable Python ready: ${hit.executable}`);
  return hit;
}

function ensurePython() {
  if (process.env.KX_FORCE_PORTABLE === "1") {
    return bootstrapPortablePython();
  }
  const found = findPython();
  if (found) return found;
  return bootstrapPortablePython();
}

function resolveRuntime() {
  const state = readState();
  if (state && state.python && fs.existsSync(state.python)) {
    if (state.kx || verifyKx(state.python)) return state;
  }
  if (fs.existsSync(venvPython())) {
    const runtime = {
      mode: "venv",
      python: venvPython(),
      kx: fs.existsSync(venvKx()) ? venvKx() : null,
    };
    if (runtime.kx || verifyKx(runtime.python)) {
      writeState(runtime);
      return runtime;
    }
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
  log(`Kx-Defender setup v${SETUP_VERSION} (Self-Built Only)`);
  if (!fs.existsSync(path.join(ROOT, "pyproject.toml"))) {
    throw new Error("pyproject.toml not found. Re-run: npx -y --prefer-online angelsj913/Kx-Defender-");
  }

  const found = ensurePython();
  log(`Python: ${found.executable}`);

  let runtime = null;

  try {
    if (!fs.existsSync(venvPython())) {
      log("Creating .venv ...");
      run(found.executable, ["-m", "venv", VENV]);
    }
    const py = venvPython();
    log("Installing into .venv ...");
    run(py, ["-m", "pip", "install", "--upgrade", "pip"]);
    run(py, ["-m", "pip", "install", "-e", "."]);
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
      if (fs.existsSync(VENV)) fs.rmSync(VENV, { recursive: true, force: true });
    } catch (_) {
      /* ignore */
    }
    try {
      run(found.executable, ["-m", "ensurepip", "--upgrade"]);
    } catch (_) {
      /* ignore */
    }
    run(found.executable, ["-m", "pip", "install", "--upgrade", "pip"]);
    run(found.executable, ["-m", "pip", "install", "--user", "-e", "."]);
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
  return setup();
}

function setupSync() {
  return setup();
}

function runKx(args, opts = {}) {
  const runtime = ensureSetup();
  if (runtime.kx && fs.existsSync(runtime.kx)) {
    return spawnSync(runtime.kx, args, {
      cwd: ROOT,
      stdio: "inherit",
      shell: isWin(),
      windowsHide: true,
      ...opts,
    });
  }
  const code =
    "import sys; from kx_defender.kx_cli import main; sys.argv=['kx']+sys.argv[1:]; main()";
  return spawnSync(runtime.python, ["-c", code, ...args], {
    cwd: ROOT,
    stdio: "inherit",
    shell: isWin(),
    windowsHide: true,
    ...opts,
  });
}

module.exports = {
  ROOT,
  VENV,
  SETUP_VERSION,
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
  try {
    setup();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
}
