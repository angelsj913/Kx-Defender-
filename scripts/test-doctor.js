"use strict";

const assert = require("assert");
const { spawnSync } = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

const doctor = require("./kx-doctor");

const temp = fs.mkdtempSync(path.join(os.tmpdir(), "kx-doctor-test-"));
const home = path.join(temp, ".kx-defender");
const app = path.join(home, "app");
fs.mkdirSync(app, { recursive: true });
fs.mkdirSync(path.join(app, "scripts"), { recursive: true });

const version = require("../package.json").version;
fs.writeFileSync(path.join(app, "package.json"), JSON.stringify({ name: "kx-defender", version }));
for (const name of ["npm-kx.js", "npx-entry.js", "kx-update.js"]) {
  fs.writeFileSync(path.join(app, "scripts", name), '"use strict";\n');
}
fs.writeFileSync(
  path.join(app, ".kx-runtime.json"),
  JSON.stringify({ mode: "venv", python: process.execPath, kx: null })
);
fs.writeFileSync(path.join(home, "install.json"), JSON.stringify({ app, branch: "test" }));
fs.writeFileSync(path.join(home, "config.json"), JSON.stringify({ lang: "en" }));
const secretHash = `scrypt$${"a".repeat(32)}$${"b".repeat(128)}`;
fs.writeFileSync(
  path.join(home, "users.json"),
  JSON.stringify({ users: [{ username: "admin", passwordHash: secretHash, role: "admin" }] })
);

const localAppData = path.join(temp, "local");
const binDir = process.platform === "win32"
  ? path.join(localAppData, "Kx-Defender", "bin")
  : path.join(temp, ".local", "bin");
fs.mkdirSync(binDir, { recursive: true });
for (const name of process.platform === "win32" ? ["kx.cmd", "kx-update.cmd"] : ["kx", "kx-update"]) {
  fs.writeFileSync(path.join(binDir, name), "test");
}

const context = {
  home,
  root: path.resolve(__dirname, ".."),
  env: {
    ...process.env,
    KX_HOME: home,
    LOCALAPPDATA: localAppData,
    PATH: `${binDir}${path.delimiter}${process.env.PATH || ""}`,
  },
  platform: process.platform,
  spawn(command, args, options) {
    if (command === "where.exe" || command === "which") {
      return { status: 0, stdout: path.join(home, "bin", "kx"), stderr: "" };
    }
    if (command === process.execPath && args[0] === "-c") {
      return { status: 0, stdout: `${version}\n`, stderr: "" };
    }
    return spawnSync(command, args, options);
  },
};

const before = new Map(
  fs.readdirSync(home).map((name) => {
    const target = path.join(home, name);
    if (!fs.statSync(target).isFile()) return [name, null];
    return [name, crypto.createHash("sha256").update(fs.readFileSync(target)).digest("hex")];
  })
);
const report = doctor.inspect(context);
assert.strictEqual(report.summary.fail, 0, JSON.stringify(report, null, 2));
assert.strictEqual(report.version, 1);
assert(report.checks.some((check) => check.id === "runtime.python" && check.status === "pass"));
assert(report.checks.some((check) => check.id === "runtime.package" && check.status === "pass"));
assert(!JSON.stringify(report).includes(secretHash), "doctor must never expose password hashes");

const after = new Map(
  fs.readdirSync(home).map((name) => {
    const target = path.join(home, name);
    if (!fs.statSync(target).isFile()) return [name, null];
    return [name, crypto.createHash("sha256").update(fs.readFileSync(target)).digest("hex")];
  })
);
assert.deepStrictEqual(after, before, "read-only doctor changed files");

fs.writeFileSync(path.join(home, "config.json"), "{broken");
const broken = doctor.inspect(context);
assert(broken.checks.some((check) => check.id === "config" && check.status === "fail"));

const repaired = doctor.execute(["--repair", "config"], { ...context, write: false });
assert.strictEqual(repaired.exitCode, 0, repaired.output);
assert.strictEqual(JSON.parse(fs.readFileSync(path.join(home, "config.json"), "utf8")).lang, "en");
assert(
  fs.readdirSync(home).some((name) => /^config\.json\.bak-/.test(name)),
  "repair must preserve a timestamped config backup"
);

const jsonResult = doctor.execute(["--json"], { ...context, write: false });
assert.strictEqual(jsonResult.exitCode, 0);
const parsed = JSON.parse(jsonResult.output);
assert.strictEqual(parsed.summary.fail, 0);
assert(!jsonResult.output.includes(secretHash));

fs.writeFileSync(path.join(home, "config.json"), JSON.stringify({ lang: "ko" }));
const repairHealthy = doctor.execute(["--repair"], { ...context, write: false });
assert.deepStrictEqual(repairHealthy.repairs, [], "automatic repair must skip healthy checks");
assert.strictEqual(
  JSON.parse(fs.readFileSync(path.join(home, "config.json"), "utf8")).lang,
  "ko",
  "automatic repair changed a healthy configuration"
);

const pidPath = path.join(home, "daemon.pid");
fs.writeFileSync(pidPath, `${process.pid}\n`);
const livePidRepair = doctor.execute(["--repair", "pid"], { ...context, write: false });
assert.strictEqual(livePidRepair.exitCode, 3);
assert(fs.existsSync(pidPath), "repair removed a live PID file");
fs.rmSync(pidPath);

const parsedArgs = doctor.parseArgs(["--verbose", "--repair=path,shims"]);
assert.strictEqual(parsedArgs.verbose, true);
assert.deepStrictEqual([...parsedArgs.repairTargets], ["path", "shims"]);
assert.strictEqual(
  doctor.powershellLiteral("C:\\Users\\O'Brien\\bin"),
  "'C:\\Users\\O''Brien\\bin'"
);
assert.strictEqual(
  doctor.redactRemote("https://user:token@example.test/repo.git"),
  "https://<redacted>@example.test/repo.git"
);

for (const launcher of ["npm-kx.js", "npx-entry.js"]) {
  const source = fs.readFileSync(path.join(__dirname, launcher), "utf8");
  assert(
    source.indexOf("runDoctor") !== -1 && source.indexOf("runDoctor") < source.indexOf("ensureSetup()"),
    `${launcher} must run doctor before setup`
  );
}

fs.rmSync(temp, { recursive: true, force: true });
console.log("doctor tests passed");
