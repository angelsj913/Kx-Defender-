#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const REPORT_VERSION = 1;
const STATUS_ORDER = { pass: 0, warn: 1, fail: 2 };

function defaultHome(env = process.env) {
  return env.KX_HOME || path.join(os.homedir(), ".kx-defender");
}

function parseArgs(argv = []) {
  const parsed = {
    json: false,
    verbose: false,
    repair: false,
    repairTargets: new Set(),
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = String(argv[i]);
    if (arg === "--json") parsed.json = true;
    else if (arg === "--verbose" || arg === "-v") parsed.verbose = true;
    else if (arg === "--repair") {
      parsed.repair = true;
      if (argv[i + 1] && !String(argv[i + 1]).startsWith("-")) {
        for (const target of String(argv[++i]).split(",")) {
          if (target.trim()) parsed.repairTargets.add(target.trim().toLowerCase());
        }
      }
    } else if (arg.startsWith("--repair=")) {
      parsed.repair = true;
      for (const target of arg.slice("--repair=".length).split(",")) {
        if (target.trim()) parsed.repairTargets.add(target.trim().toLowerCase());
      }
    }
  }
  if (parsed.repair && parsed.repairTargets.size === 0) parsed.repairTargets.add("all");
  return parsed;
}

function safeJson(file) {
  try {
    return { value: JSON.parse(fs.readFileSync(file, "utf8")), error: null };
  } catch (error) {
    return { value: null, error };
  }
}

function readPackageVersion(root) {
  const result = safeJson(path.join(root, "package.json"));
  return result.value && typeof result.value.version === "string"
    ? result.value.version
    : null;
}

function redactRemote(value) {
  return String(value || "").replace(
    /^(https?:\/\/)[^/@\s]+@/i,
    "$1<redacted>@"
  );
}

function spawn(context, command, args, options = {}) {
  const runner = context.spawn || spawnSync;
  return runner(command, args, {
    encoding: "utf8",
    windowsHide: true,
    shell: false,
    ...options,
  });
}

function add(checks, id, status, summary, extra = {}) {
  checks.push({
    id,
    status,
    summary,
    ...(extra.details ? { details: extra.details } : {}),
    ...(extra.repair ? { repair: extra.repair } : {}),
  });
}

function resolveApp(home) {
  const installPath = path.join(home, "install.json");
  const install = safeJson(installPath);
  if (install.value && typeof install.value.app === "string") {
    return { app: path.resolve(install.value.app), install, installPath };
  }
  return { app: path.join(home, "app"), install, installPath };
}

function binDirFor(context) {
  if (context.platform === "win32") {
    return path.join(
      context.env.LOCALAPPDATA || path.join(path.dirname(context.home), "AppData", "Local"),
      "Kx-Defender",
      "bin"
    );
  }
  return path.join(path.dirname(context.home), ".local", "bin");
}

function pidIsAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (_) {
    return false;
  }
}

function inspect(options = {}) {
  const context = {
    home: options.home || defaultHome(options.env),
    root: options.root || path.resolve(__dirname, ".."),
    env: options.env || process.env,
    platform: options.platform || process.platform,
    spawn: options.spawn,
  };
  context.home = path.resolve(context.home);
  context.root = path.resolve(context.root);

  const checks = [];
  const nodeMajor = Number.parseInt(process.versions.node.split(".")[0], 10);
  add(
    checks,
    "runtime.node",
    nodeMajor >= 16 ? "pass" : "fail",
    `Node ${process.versions.node}`,
    nodeMajor >= 16 ? {} : { details: "Node 16 or newer is required." }
  );

  if (context.platform === "win32") {
    const ps = spawn(
      context,
      "powershell.exe",
      ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"]
    );
    add(
      checks,
      "runtime.powershell",
      ps.status === 0 ? "pass" : "warn",
      ps.status === 0 ? `PowerShell ${String(ps.stdout).trim()}` : "PowerShell version unavailable",
      ps.status === 0 ? {} : { details: String(ps.stderr || "").trim() }
    );
  } else {
    add(checks, "runtime.powershell", "pass", "PowerShell check not required on this platform");
  }

  if (!fs.existsSync(context.home)) {
    add(checks, "home.access", "warn", `Kx home is not created yet: ${context.home}`);
  } else {
    try {
      fs.accessSync(context.home, fs.constants.R_OK | fs.constants.W_OK);
      add(checks, "home.access", "pass", `Kx home is readable and writable`, {
        details: context.home,
      });
    } catch (error) {
      add(checks, "home.access", "fail", "Kx home is not readable and writable", {
        details: error.message,
      });
    }
  }

  const { app, install, installPath } = resolveApp(context.home);
  const appVersion = readPackageVersion(app);
  if (appVersion) {
    add(checks, "app.install", "pass", `Persistent app ${appVersion}`, { details: app });
  } else {
    add(checks, "app.install", "fail", "Persistent app is missing or invalid", {
      details: app,
      repair: "shims",
    });
  }

  if (fs.existsSync(path.join(app, ".git"))) {
    const remote = spawn(context, "git", ["-C", app, "remote", "get-url", "origin"]);
    const branch = spawn(context, "git", ["-C", app, "rev-parse", "--abbrev-ref", "HEAD"]);
    const commit = spawn(context, "git", ["-C", app, "rev-parse", "--short", "HEAD"]);
    const gitOk = remote.status === 0 && branch.status === 0 && commit.status === 0;
    add(
      checks,
      "app.git",
      gitOk ? "pass" : "warn",
      gitOk
        ? `Git ${String(branch.stdout).trim()} at ${String(commit.stdout).trim()}`
        : "Git application metadata is incomplete",
      {
        details: gitOk
          ? redactRemote(String(remote.stdout).trim())
          : [remote.stderr, branch.stderr, commit.stderr].filter(Boolean).join("\n").trim(),
      }
    );
  } else {
    add(checks, "app.git", "pass", "Persistent app is a packaged installation");
  }

  if (fs.existsSync(installPath) && install.error) {
    add(checks, "install.metadata", "fail", "install.json is invalid", {
      details: install.error.message,
      repair: "shims",
    });
  } else if (install.value) {
    add(checks, "install.metadata", "pass", "Install metadata is valid", {
      details: installPath,
    });
  } else {
    add(checks, "install.metadata", "warn", "Install metadata is not present", {
      repair: "shims",
    });
  }

  const launcherVersion = readPackageVersion(context.root);
  if (launcherVersion && appVersion && launcherVersion !== appVersion) {
    add(checks, "app.version", "fail", "Launcher and persistent app versions differ", {
      details: `launcher=${launcherVersion}, app=${appVersion}`,
      repair: "shims",
    });
  } else if (launcherVersion || appVersion) {
    add(checks, "app.version", "pass", `Version ${launcherVersion || appVersion}`);
  } else {
    add(checks, "app.version", "fail", "No valid Kx-Defender package version found");
  }

  const statePath = fs.existsSync(path.join(app, ".kx-runtime.json"))
    ? path.join(app, ".kx-runtime.json")
    : path.join(context.root, ".kx-runtime.json");
  const state = safeJson(statePath);
  const python = state.value && typeof state.value.python === "string" ? state.value.python : null;
  if (!python || !fs.existsSync(python)) {
    add(checks, "runtime.python", "fail", "Configured Python runtime is missing", {
      details: state.error ? state.error.message : statePath,
      repair: "venv",
    });
  } else {
    const py = spawn(context, python, ["--version"]);
    add(
      checks,
      "runtime.python",
      py.status === 0 ? "pass" : "fail",
      py.status === 0
        ? String(py.stdout || py.stderr || "Python available").trim()
        : "Configured Python cannot start",
      {
        details: python,
        ...(py.status === 0 ? {} : { repair: "venv" }),
      }
    );
    if (py.status === 0) {
      const installed = spawn(
        context,
        python,
        ["-c", "import kx_defender; print(kx_defender.__version__)"]
      );
      const installedVersion = String(installed.stdout || "").trim();
      const packageOk = installed.status === 0 && Boolean(installedVersion);
      const versionOk = packageOk && (!appVersion || installedVersion === appVersion);
      add(
        checks,
        "runtime.package",
        versionOk ? "pass" : "fail",
        versionOk
          ? `Python package ${installedVersion}`
          : packageOk
            ? `Python package ${installedVersion} does not match app ${appVersion}`
            : "kx_defender cannot be imported by the configured Python",
        {
          details: packageOk ? python : String(installed.stderr || "").trim(),
          ...(versionOk ? {} : { repair: "venv" }),
        }
      );
    }
  }

  const configPath = path.join(context.home, "config.json");
  if (!fs.existsSync(configPath)) {
    add(checks, "config", "pass", "No config file; English defaults will be used");
  } else {
    const config = safeJson(configPath);
    if (config.error || !config.value || !["en", "ko"].includes(config.value.lang)) {
      add(checks, "config", "fail", "config.json is invalid", {
        details: config.error ? config.error.message : "lang must be en or ko",
        repair: "config",
      });
    } else {
      add(checks, "config", "pass", `Configuration is valid (language=${config.value.lang})`);
    }
  }

  const usersPath = path.join(context.home, "users.json");
  if (!fs.existsSync(usersPath)) {
    add(checks, "auth.users", "warn", "User database is not initialized yet");
  } else {
    const users = safeJson(usersPath);
    const valid = Boolean(
      !users.error &&
      users.value &&
      Array.isArray(users.value.users) &&
      users.value.users.every((user) => {
        const hash = typeof user.passwordHash === "string" ? user.passwordHash : "";
        return (
          typeof user.username === "string" &&
          ["admin", "user"].includes(user.role) &&
          (/^[a-f0-9]{64}$/i.test(hash) ||
            /^scrypt\$[a-f0-9]{32}\$[a-f0-9]{128}$/i.test(hash))
        );
      })
    );
    add(
      checks,
      "auth.users",
      valid ? "pass" : "fail",
      valid ? `User database is valid (${users.value.users.length} user(s))` : "User database is invalid",
      users.error ? { details: users.error.message } : {}
    );
  }

  const git = spawn(context, "git", ["--version"]);
  add(
    checks,
    "tool.git",
    git.status === 0 ? "pass" : "warn",
    git.status === 0 ? String(git.stdout).trim() : "Git is unavailable; npm update fallback is required"
  );

  const commandProbe = context.platform === "win32"
    ? spawn(context, "where.exe", ["kx"])
    : spawn(context, "which", ["kx"]);
  const commandPaths = commandProbe.status === 0
    ? String(commandProbe.stdout).split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    : [];
  add(
    checks,
    "command.kx",
    commandPaths.length ? "pass" : "warn",
    commandPaths.length ? `kx resolves to ${commandPaths[0]}` : "kx is not on PATH",
    {
      ...(commandPaths.length > 1 ? { details: commandPaths.join("\n") } : {}),
      ...(commandPaths.length ? {} : { repair: "path" }),
    }
  );

  const binDir = binDirFor(context);
  const expectedShims = context.platform === "win32"
    ? ["kx.cmd", "kx-update.cmd"]
    : ["kx", "kx-update"];
  const missingShims = expectedShims.filter((name) => !fs.existsSync(path.join(binDir, name)));
  add(
    checks,
    "command.shims",
    missingShims.length ? "warn" : "pass",
    missingShims.length
      ? `Missing command shim(s): ${missingShims.join(", ")}`
      : `Command shims are present`,
    missingShims.length ? { details: binDir, repair: "shims" } : { details: binDir }
  );

  const normalizePath = (value) => {
    const resolved = path.resolve(value);
    return context.platform === "win32" ? resolved.toLowerCase() : resolved;
  };
  const activePath = String(context.env.PATH || "")
    .split(path.delimiter)
    .filter(Boolean)
    .map(normalizePath);
  const binOnPath = activePath.includes(normalizePath(binDir));
  add(
    checks,
    "command.path",
    binOnPath ? "pass" : "warn",
    binOnPath ? "Kx shim directory is on PATH" : "Kx shim directory is not on this session PATH",
    binOnPath ? { details: binDir } : { details: binDir, repair: "path" }
  );

  const pidPath = path.join(context.home, "daemon.pid");
  if (!fs.existsSync(pidPath)) {
    add(checks, "daemon.pid", "pass", "Daemon is stopped; no PID file");
  } else {
    const pid = Number.parseInt(String(fs.readFileSync(pidPath, "utf8")).trim(), 10);
    const alive = pidIsAlive(pid);
    add(
      checks,
      "daemon.pid",
      alive ? "pass" : "warn",
      alive ? `Daemon process ${pid} is running` : "Stale or invalid daemon PID file",
      alive ? {} : { details: pidPath, repair: "pid" }
    );
  }

  const staging = ["pack-staging", "python-staging"]
    .map((name) => path.join(context.home, name))
    .filter((target) => fs.existsSync(target));
  add(
    checks,
    "staging",
    staging.length ? "warn" : "pass",
    staging.length ? `${staging.length} stale staging path(s) found` : "No stale staging paths",
    staging.length ? { details: staging.join("\n"), repair: "staging" } : {}
  );

  const utf8 = Buffer.from("Kx 진단", "utf8").toString("utf8") === "Kx 진단";
  add(checks, "encoding.utf8", utf8 ? "pass" : "fail", utf8 ? "UTF-8 round trip passed" : "UTF-8 round trip failed");

  checks.sort((a, b) => STATUS_ORDER[b.status] - STATUS_ORDER[a.status] || a.id.localeCompare(b.id));
  const summary = {
    pass: checks.filter((check) => check.status === "pass").length,
    warn: checks.filter((check) => check.status === "warn").length,
    fail: checks.filter((check) => check.status === "fail").length,
  };
  return {
    version: REPORT_VERSION,
    healthy: summary.fail === 0,
    generatedAt: new Date().toISOString(),
    platform: `${context.platform}/${process.arch}`,
    app,
    summary,
    checks,
  };
}

function timestamp() {
  return new Date().toISOString().replace(/\D/g, "").slice(0, 17);
}

function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp, JSON.stringify(value, null, 2) + "\n", "utf8");
  fs.renameSync(temp, file);
}

function within(parent, target) {
  const root = path.resolve(parent) + path.sep;
  return path.resolve(target).startsWith(root);
}

function powershellLiteral(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function repairConfig(context) {
  const target = path.join(context.home, "config.json");
  if (fs.existsSync(target)) fs.copyFileSync(target, `${target}.bak-${timestamp()}`);
  atomicJson(target, { lang: "en" });
  return "Rebuilt config.json with English defaults";
}

function repairShims(context) {
  const { app } = resolveApp(context.home);
  if (!readPackageVersion(app)) throw new Error(`persistent app is missing: ${app}`);
  const binDir = binDirFor(context);
  fs.mkdirSync(binDir, { recursive: true });
  const entries = {
    kx: path.join(app, "scripts", "npm-kx.js"),
    "kx-defender": path.join(app, "scripts", "npx-entry.js"),
    "login-kx": path.join(app, "scripts", "npx-entry.js"),
    "kx-update": path.join(app, "scripts", "kx-update.js"),
  };
  for (const [name, target] of Object.entries(entries)) {
    if (!fs.existsSync(target)) throw new Error(`shim target is missing: ${target}`);
    if (context.platform === "win32") {
      const prefix = name === "login-kx" ? " login kx" : "";
      fs.writeFileSync(path.join(binDir, `${name}.cmd`), `@node "${target}"${prefix} %*\r\n`);
    } else {
      const prefix = name === "login-kx" ? " login kx" : "";
      const destination = path.join(binDir, name);
      fs.writeFileSync(destination, `#!/bin/sh\nexec node ${JSON.stringify(target)}${prefix} "$@"\n`);
      fs.chmodSync(destination, 0o755);
    }
  }
  atomicJson(path.join(context.home, "install.json"), {
    app,
    updatedAt: new Date().toISOString(),
    branch: safeJson(path.join(context.home, "install.json")).value?.branch || "main",
  });
  return `Rebuilt command shims in ${binDir}`;
}

function repairPath(context) {
  const binDir = binDirFor(context);
  const parts = String(context.env.PATH || "").split(path.delimiter).filter(Boolean);
  if (parts.some((entry) => path.resolve(entry).toLowerCase() === path.resolve(binDir).toLowerCase())) {
    return `${binDir} is already on PATH`;
  }
  if (context.platform !== "win32") {
    throw new Error(`automatic PATH repair is only supported on Windows; add ${binDir}`);
  }
  const script = [
    `$bin=${powershellLiteral(binDir)}`,
    "$current=[Environment]::GetEnvironmentVariable('Path','User')",
    "$parts=@($current -split ';' | Where-Object { $_ })",
    "$binFull=[IO.Path]::GetFullPath($bin).TrimEnd('\\')",
    "$clean=@($parts | Where-Object { try { [IO.Path]::GetFullPath($_).TrimEnd('\\') -ne $binFull } catch { $true } })",
    "[Environment]::SetEnvironmentVariable('Path', (($bin)+$([IO.Path]::PathSeparator)+($clean -join [IO.Path]::PathSeparator)), 'User')",
  ].join(";");
  const encoded = Buffer.from(script, "utf16le").toString("base64");
  const result = spawn(
    context,
    "powershell.exe",
    ["-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
  );
  if (result.status !== 0) throw new Error(String(result.stderr || "PATH update failed").trim());
  return `Added ${binDir} to the user PATH; reopen the terminal to refresh this session`;
}

function repairVenv(context) {
  const setupPath = path.join(context.root, "scripts", "npm-setup.js");
  if (!fs.existsSync(setupPath)) throw new Error(`setup module is missing: ${setupPath}`);
  delete require.cache[require.resolve(setupPath)];
  require(setupPath).setup();
  return "Rebuilt the local Python runtime";
}

function repairPid(context) {
  const target = path.join(context.home, "daemon.pid");
  if (fs.existsSync(target)) {
    const pid = Number.parseInt(String(fs.readFileSync(target, "utf8")).trim(), 10);
    if (pidIsAlive(pid)) throw new Error(`refusing to remove PID for running process ${pid}`);
    fs.rmSync(target, { force: true });
  }
  return "Removed the stale daemon PID file";
}

function repairStaging(context) {
  let removed = 0;
  for (const name of ["pack-staging", "python-staging"]) {
    const target = path.join(context.home, name);
    if (!within(context.home, target)) throw new Error(`unsafe staging path: ${target}`);
    if (fs.existsSync(target)) {
      fs.rmSync(target, { recursive: true, force: true });
      removed++;
    }
  }
  return `Removed ${removed} stale staging path(s)`;
}

const REPAIRS = {
  config: repairConfig,
  shims: repairShims,
  path: repairPath,
  venv: repairVenv,
  pid: repairPid,
  staging: repairStaging,
};

function performRepairs(parsed, options, initialReport) {
  const requested = parsed.repairTargets.has("all")
    ? [...new Set(
      initialReport.checks
        .filter((check) => check.status !== "pass" && check.repair)
        .map((check) => check.repair)
    )]
    : [...parsed.repairTargets];
  const outcomes = [];
  for (const target of requested) {
    const action = REPAIRS[target];
    if (!action) {
      outcomes.push({ target, status: "fail", summary: `Unknown repair target: ${target}` });
      continue;
    }
    try {
      outcomes.push({ target, status: "pass", summary: action(options) });
    } catch (error) {
      outcomes.push({ target, status: "fail", summary: error.message || String(error) });
    }
  }
  return outcomes;
}

function formatHuman(report, { verbose = false, repairs = [] } = {}) {
  const lines = [
    `Kx Doctor v${report.version}`,
    `Platform: ${report.platform}`,
    `App: ${report.app}`,
    "",
  ];
  for (const check of report.checks) {
    const label = check.status.toUpperCase().padEnd(4);
    lines.push(`[${label}] ${check.id} - ${check.summary}`);
    if (verbose && check.details) {
      for (const detail of String(check.details).split(/\r?\n/)) lines.push(`       ${detail}`);
    }
    if (check.repair) lines.push(`       repair: kx doctor --repair ${check.repair}`);
  }
  if (repairs.length) {
    lines.push("", "Repairs:");
    for (const result of repairs) {
      lines.push(`[${result.status.toUpperCase()}] ${result.target} - ${result.summary}`);
    }
  }
  lines.push(
    "",
    `Summary: ${report.summary.pass} passed, ${report.summary.warn} warning(s), ${report.summary.fail} failed`
  );
  return lines.join("\n");
}

function execute(argv = [], options = {}) {
  const parsed = parseArgs(argv);
  const context = {
    home: path.resolve(options.home || defaultHome(options.env)),
    root: path.resolve(options.root || path.resolve(__dirname, "..")),
    env: options.env || process.env,
    platform: options.platform || process.platform,
    spawn: options.spawn,
  };
  const initialReport = inspect(context);
  let repairs = [];
  if (parsed.repair) repairs = performRepairs(parsed, context, initialReport);
  const report = repairs.length ? inspect(context) : initialReport;
  if (repairs.length) report.repairs = repairs;
  const output = parsed.json
    ? JSON.stringify(report, null, 2)
    : formatHuman(report, { verbose: parsed.verbose, repairs });
  const repairFailed = repairs.some((result) => result.status === "fail");
  const exitCode = repairFailed ? 3 : report.summary.fail > 0 ? 2 : 0;
  if (options.write !== false) process.stdout.write(output + "\n");
  return { report, repairs, output, exitCode };
}

function runDoctor(argv = [], options = {}) {
  return execute(argv, options).exitCode;
}

function main(argv = process.argv.slice(2)) {
  process.exitCode = runDoctor(argv);
}

module.exports = {
  REPORT_VERSION,
  parseArgs,
  inspect,
  execute,
  formatHuman,
  powershellLiteral,
  redactRemote,
  runDoctor,
  main,
};

if (require.main === module) main();
