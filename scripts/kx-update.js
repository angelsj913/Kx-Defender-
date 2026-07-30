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

function run(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, {
    stdio: "inherit",
    shell: isWin(),
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

function hasGit() {
  const res = spawnSync("git", ["--version"], { stdio: "ignore", shell: isWin() });
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
    run("git", ["-C", APP, "reset", "--hard", `origin/${BRANCH}`]);
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

function runSetup() {
  const setupJs = path.join(APP, "scripts", "npm-setup.js");
  if (!fs.existsSync(setupJs)) throw new Error(`setup missing: ${setupJs}`);
  log("Running setup in updated app ...");
  run(process.execPath, [setupJs, "--setup"], { cwd: APP });
}

function writeShims() {
  const binDir = isWin()
    ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"), "Kx-Defender", "bin")
    : path.join(os.homedir(), ".local", "bin");
  fs.mkdirSync(binDir, { recursive: true });
  const entry = path.join(APP, "scripts", "npx-entry.js");
  const kxJs = path.join(APP, "scripts", "npm-kx.js");
  if (isWin()) {
    fs.writeFileSync(path.join(binDir, "kx.cmd"), `@node "${kxJs}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "kx-defender.cmd"), `@node "${entry}" %*\r\n`);
    fs.writeFileSync(path.join(binDir, "login-kx.cmd"), `@node "${entry}" login kx %*\r\n`);
    fs.writeFileSync(
      path.join(binDir, "kx-update.cmd"),
      `@node "${path.join(APP, "scripts", "kx-update.js")}" %*\r\n`
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
    write("kx", kxJs);
    write("kx-defender", entry);
    write("login-kx", entry, "login kx ");
    write("kx-update", path.join(APP, "scripts", "kx-update.js"));
  }
  // marker for launcher to prefer local app
  fs.writeFileSync(
    path.join(HOME, "install.json"),
    JSON.stringify({ app: APP, updatedAt: new Date().toISOString(), branch: BRANCH }, null, 2) + "\n"
  );
  log(`Shims updated in ${binDir}`);
  return binDir;
}

/** Seed ~/.kx-defender/app from the current package once (enables update without reinstall). */
function ensurePersistentInstall(sourceRoot) {
  if (fs.existsSync(path.join(APP, "package.json"))) {
    writeShims();
    return APP;
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

function updateKx() {
  log("Updating Kx-Defender (no full reinstall) ...");
  if (hasGit()) updateFromGit();
  else updateFromNpxPack();
  runSetup();
  const binDir = writeShims();
  log("Update complete.");
  log(`App: ${APP}`);
  log(`Re-enter: login kx   or   [login kx]`);
  if (isWin()) log(`PATH tip: $env:PATH="${binDir};$env:PATH"`);
  return { app: APP, binDir };
}

function getAppRoot() {
  try {
    const meta = JSON.parse(fs.readFileSync(path.join(HOME, "install.json"), "utf8"));
    if (meta.app && fs.existsSync(path.join(meta.app, "package.json"))) return meta.app;
  } catch (_) {
    /* ignore */
  }
  if (fs.existsSync(path.join(APP, "package.json"))) return APP;
  return null;
}

module.exports = { updateKx, getAppRoot, ensurePersistentInstall, writeShims, APP, HOME };

if (require.main === module) {
  try {
    updateKx();
  } catch (err) {
    console.error(`[Kx] ${err.message || err}`);
    process.exit(err.status || 1);
  }
}
