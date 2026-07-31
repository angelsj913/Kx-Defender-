"use strict";

/**
 * Persist / update Kx-Defender under ~/.kx-defender/app (no full reinstall).
 *
 *   npx -y angelsj913/Kx-Defender- update
 *   Kx> update
 */

const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const releaseState = require("./kx-release");

const HOME = path.join(os.homedir(), ".kx-defender");
const APP = path.join(HOME, "app");
const REPO = "https://github.com/angelsj913/Kx-Defender-.git";
const BRANCH = process.env.KX_UPDATE_BRANCH || "main";

function log(msg) {
  console.log(`[Kx] ${msg}`);
}

function isWin() {
  return process.platform === "win32";
}

function spawnOptions(cmd, { platform = process.platform } = {}) {
  const absolute = path.isAbsolute(cmd) || /^[a-zA-Z]:[\\/]/.test(cmd);
  const nativeGit = /^(git|git\.exe)$/i.test(path.basename(cmd));
  return { shell: platform === "win32" && !absolute && !nativeGit };
}

function run(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, {
    stdio: "inherit",
    ...spawnOptions(cmd),
    windowsHide: true,
    ...opts,
  });
  if (res.status !== 0) {
    const err = new Error(`Command failed (${res.status}): ${cmd} ${args.join(" ")}`);
    err.status = res.status || 1;
    throw err;
  }
  return res;
}

function capture(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, {
    encoding: "utf8",
    ...spawnOptions(cmd),
    windowsHide: true,
    ...opts,
  });
  if (res.status !== 0) {
    const err = new Error(String(res.stderr || `Command failed (${res.status}): ${cmd}`).trim());
    err.status = res.status || 1;
    throw err;
  }
  return String(res.stdout || "").trim();
}

function hasGit() {
  const res = spawnSync("git", ["--version"], {
    stdio: "ignore",
    ...spawnOptions("git"),
  });
  return res.status === 0;
}

function updateFromGit() {
  fs.mkdirSync(HOME, { recursive: true });
  if (!fs.existsSync(path.join(APP, ".git"))) {
    if (fs.existsSync(APP)) fs.rmSync(APP, { recursive: true, force: true });
    log(`Cloning ${REPO} (${BRANCH}) → ${APP}`);
    run("git", ["clone", "--depth", "1", "--branch", BRANCH, REPO, APP]);
  } else {
    log(`Pulling latest (${BRANCH}) in ${APP}`);
    run("git", ["-C", APP, "fetch", "origin", BRANCH]);
    run("git", ["-C", APP, "reset", "--hard", "FETCH_HEAD"]);
  }
}

function updateFromNpxPack() {
  // Fallback when git is unavailable: npm pack github shorthand
  fs.mkdirSync(HOME, { recursive: true });
  const staging = path.join(HOME, "pack-staging");
  fs.rmSync(staging, { recursive: true, force: true });
  fs.mkdirSync(staging, { recursive: true });
  log("Fetching package via npm pack (github:angelsj913/Kx-Defender-) ...");
  run("npm", ["pack", "github:angelsj913/Kx-Defender-", "--pack-destination", staging], {
    cwd: staging,
  });
  const tgz = fs.readdirSync(staging).find((f) => f.endsWith(".tgz"));
  if (!tgz) throw new Error("npm pack produced no tarball");
  const extract = path.join(staging, "extract");
  fs.mkdirSync(extract, { recursive: true });
  run("tar", ["-xzf", path.join(staging, tgz), "-C", extract]);
  const pkg = path.join(extract, "package");
  if (!fs.existsSync(pkg)) throw new Error("unexpected pack layout");
  fs.rmSync(APP, { recursive: true, force: true });
  fs.cpSync(pkg, APP, { recursive: true });
  fs.rmSync(staging, { recursive: true, force: true });
}

function runSetup(app = APP) {
  const setupJs = path.join(app, "scripts", "npm-setup.js");
  if (!fs.existsSync(setupJs)) throw new Error(`setup missing: ${setupJs}`);
  log("Running setup in updated app ...");
  run(process.execPath, [setupJs, "--setup"], { cwd: app });
}

function smokeTest(app) {
  const entry = path.join(app, "scripts", "npm-kx.js");
  run(process.execPath, ["--check", entry], { cwd: app });
  const terminalTest = path.join(app, "scripts", "test-terminal-ui.js");
  if (fs.existsSync(terminalTest)) run(process.execPath, [terminalTest], { cwd: app });
}

function gitCommit(app) {
  try {
    return capture("git", ["-C", app, "rev-parse", "HEAD"]);
  } catch (_) {
    return null;
  }
}

function seedLegacyRelease() {
  const existing = releaseState.readState(HOME);
  if (existing.current) return existing;
  if (!fs.existsSync(path.join(APP, "package.json"))) return existing;
  const commit = gitCommit(APP) || `legacy-${Date.now()}`;
  const destination = path.join(releaseState.releaseRoot(HOME), commit);
  if (!fs.existsSync(destination)) {
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.cpSync(APP, destination, { recursive: true });
    fs.writeFileSync(
      path.join(destination, ".kx-release-ready.json"),
      JSON.stringify({ commit, branch: "legacy", testedAt: new Date().toISOString() }, null, 2) + "\n"
    );
  }
  return releaseState.activate({ home: HOME, app: destination, commit, branch: "legacy" });
}

function prepareGitRelease() {
  const releases = releaseState.releaseRoot(HOME);
  fs.mkdirSync(releases, { recursive: true });
  const staging = path.join(releases, `.staging-${process.pid}-${Date.now()}`);
  let candidate = null;
  let created = false;
  try {
    run("git", ["clone", "--depth", "1", "--branch", BRANCH, REPO, staging]);
    const commit = capture("git", ["-C", staging, "rev-parse", "HEAD"]);
    const destination = path.join(releases, commit);
    if (fs.existsSync(destination)) {
      releaseState.validate({ home: HOME, app: destination, commit });
      if (!fs.existsSync(path.join(destination, ".kx-release-ready.json"))) {
        throw new Error(`release exists without a successful smoke-test marker: ${destination}`);
      }
      return { app: destination, commit, reused: true };
    }
    fs.renameSync(staging, destination);
    candidate = destination;
    created = true;
    runSetup(destination);
    smokeTest(destination);
    fs.writeFileSync(
      path.join(destination, ".kx-release-ready.json"),
      JSON.stringify({ commit, branch: BRANCH, testedAt: new Date().toISOString() }, null, 2) + "\n"
    );
    return { app: destination, commit, reused: false };
  } catch (error) {
    if (created && candidate && fs.existsSync(candidate)) {
      fs.rmSync(candidate, { recursive: true, force: true });
    }
    throw error;
  } finally {
    if (fs.existsSync(staging)) fs.rmSync(staging, { recursive: true, force: true });
  }
}

function printUpdateStatus() {
  const state = releaseState.readState(HOME);
  const payload = {
    current: state.current,
    previous: state.previous,
    legacyApp: fs.existsSync(path.join(APP, "package.json")) ? APP : null,
  };
  console.log(JSON.stringify(payload, null, 2));
  return payload;
}

function writeStableControlPlane(home = HOME, sourceDir = __dirname) {
  const control = path.join(home, "control");
  fs.mkdirSync(control, { recursive: true });
  for (const name of ["kx-update.js", "kx-release.js"]) {
    const source = path.join(sourceDir, name);
    if (!fs.existsSync(source)) throw new Error(`control-plane source is missing: ${source}`);
    fs.copyFileSync(source, path.join(control, name));
  }
  return path.join(control, "kx-update.js");
}

function writeStableLauncher(home = HOME) {
  fs.mkdirSync(home, { recursive: true });
  const launcher = path.join(home, "launcher.js");
  const source = `"use strict";
const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const home = ${JSON.stringify(home)};
function json(file) { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch (_) { return null; } }
const state = json(path.join(home, "current.json"));
const install = json(path.join(home, "install.json"));
const app = state && state.current && state.current.app || install && install.app || path.join(home, "app");
const mode = process.argv[2] || "kx";
let rest = process.argv.slice(3);
let target = path.join(app, "scripts", "npm-kx.js");
let prefix = [];
if (mode === "entry") target = path.join(app, "scripts", "npx-entry.js");
if (mode === "login") { target = path.join(app, "scripts", "npx-entry.js"); prefix = ["login", "kx"]; }
if (mode === "client") target = path.join(app, "scripts", "kx-client.js");
if (mode === "shell") target = path.join(app, "scripts", "kx-shell.js");
if (mode === "update") {
  const stableUpdater = path.join(home, "control", "kx-update.js");
  target = fs.existsSync(stableUpdater) ? stableUpdater : path.join(app, "scripts", "kx-update.js");
}
if (mode === "kx" && ["update", "upgrade"].includes(String(rest[0] || "").toLowerCase())) {
  const stableUpdater = path.join(home, "control", "kx-update.js");
  target = fs.existsSync(stableUpdater) ? stableUpdater : path.join(app, "scripts", "kx-update.js");
  rest = rest.slice(1);
}
if (!fs.existsSync(target)) { console.error("[Kx] active release entry is missing: " + target); process.exit(2); }
const result = spawnSync(process.execPath, [target, ...prefix, ...rest], { stdio: "inherit", shell: false, windowsHide: true });
process.exit(result.status == null ? 1 : result.status);
`;
  const temp = `${launcher}.tmp-${process.pid}`;
  fs.writeFileSync(temp, source, "utf8");
  fs.renameSync(temp, launcher);
  return launcher;
}

function writeShims() {
  const binDir = isWin()
    ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"), "Kx-Defender", "bin")
    : path.join(os.homedir(), ".local", "bin");
  fs.mkdirSync(binDir, { recursive: true });
  const activeApp = getAppRoot() || APP;
  writeStableControlPlane();
  const launcher = writeStableLauncher();
  if (isWin()) {
    fs.writeFileSync(path.join(binDir, "kx.cmd"), `@node "${launcher}" kx %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-defender.cmd"), `@node "${launcher}" entry %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-client.cmd"), `@node "${launcher}" client %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-shell.cmd"), `@node "${launcher}" shell %*\r\n`);
    fs.writeFileSync(path.join(binDir, "login-kx.cmd"), `@node "${launcher}" login %*\r\n`);
    fs.writeFileSync(
      path.join(binDir, "kx-update.cmd"),
      `@node "${launcher}" update %*\r\n`
    );
  } else {
    const write = (name, target, extraArgs = "") => {
      const dest = path.join(binDir, name);
      fs.writeFileSync(
        dest,
        `#!/bin/sh\nexec node ${JSON.stringify(target)} ${extraArgs}"$@"\n`,
        { mode: 0o755 }
      );
      try {
        fs.chmodSync(dest, 0o755);
      } catch (_) {
        /* ignore */
      }
    };
    write("kx", launcher, "kx ");
    write("kx-defender", launcher, "entry ");
    write("kx-client", launcher, "client ");
    write("kx-shell", launcher, "shell ");
    write("login-kx", launcher, "login ");
    write("kx-update", launcher, "update ");
  }
  // marker for launcher to prefer local app
  fs.writeFileSync(
    path.join(HOME, "install.json"),
    JSON.stringify({ app: activeApp, updatedAt: new Date().toISOString(), branch: BRANCH }, null, 2) + "\n"
  );
  log(`Shims updated in ${binDir}`);
  return binDir;
}

/** Seed ~/.kx-defender/app from the current package once (enables update without reinstall). */
function ensurePersistentInstall(sourceRoot) {
  const active = getAppRoot();
  if (active) {
    writeShims();
    return active;
  }
  if (!sourceRoot || !fs.existsSync(path.join(sourceRoot, "package.json"))) return null;
  if (path.resolve(sourceRoot) === path.resolve(APP)) {
    writeShims();
    return APP;
  }
  log(`Seeding local app at ${APP} ...`);
  fs.mkdirSync(HOME, { recursive: true });
  fs.rmSync(APP, { recursive: true, force: true });
  fs.cpSync(sourceRoot, APP, {
    recursive: true,
    filter: (p) => {
      const base = path.basename(p);
      return base !== "node_modules" && base !== ".git";
    },
  });
  writeShims();
  return APP;
}

function updateKx(args = []) {
  const command = String(args[0] || "apply").toLowerCase();
  if (command === "status") return printUpdateStatus();
  if (command === "rollback") {
    const state = releaseState.rollback(HOME);
    const binDir = writeShims();
    log(`Rollback complete: ${state.current.commit}`);
    return { app: state.current.app, binDir, state };
  }
  if (command === "check") {
    if (!hasGit()) throw new Error("git is required for update check");
    const remote = capture("git", ["ls-remote", REPO, `refs/heads/${BRANCH}`]).split(/\s+/)[0];
    const state = releaseState.readState(HOME);
    const payload = { branch: BRANCH, remote, current: state.current?.commit || null, updateAvailable: remote !== state.current?.commit };
    console.log(JSON.stringify(payload, null, 2));
    return payload;
  }
  if (!["apply", "update", "upgrade"].includes(command)) {
    throw new Error("usage: kx update [check|apply|status|rollback]");
  }
  if (!hasGit()) throw new Error("atomic updates currently require git");
  log("Preparing atomic Kx-Defender update ...");
  seedLegacyRelease();
  const binDir = writeShims();
  const candidate = prepareGitRelease();
  const state = releaseState.activate({
    home: HOME,
    app: candidate.app,
    commit: candidate.commit,
    branch: BRANCH,
  });
  writeShims();
  log("Atomic update complete.");
  log(`App: ${state.current.app}`);
  log(`Re-enter: login kx   or   [login kx]`);
  if (isWin()) log(`PATH tip: $env:PATH="${binDir};$env:PATH"`);
  return { app: state.current.app, binDir, state };
}

function getAppRoot() {
  const current = releaseState.currentApp(HOME);
  if (current) return current;
  try {
    const meta = JSON.parse(fs.readFileSync(path.join(HOME, "install.json"), "utf8"));
    if (meta.app && fs.existsSync(path.join(meta.app, "package.json"))) return meta.app;
  } catch (_) {
    /* ignore */
  }
  if (fs.existsSync(path.join(APP, "package.json"))) return APP;
  return null;
}

module.exports = {
  updateKx,
  getAppRoot,
  ensurePersistentInstall,
  writeShims,
  writeStableLauncher,
  writeStableControlPlane,
  spawnOptions,
  hasGit,
  APP,
  HOME,
};

if (require.main === module) {
  try {
    updateKx(process.argv.slice(2));
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
}
