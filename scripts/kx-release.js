"use strict";

const fs = require("fs");
const path = require("path");

const STATE_VERSION = 1;

function statePath(home) {
  return path.join(path.resolve(home), "current.json");
}

function atomicWriteJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${process.pid}-${Date.now()}`;
  fs.writeFileSync(temp, JSON.stringify(value, null, 2) + "\n", "utf8");
  try {
    fs.renameSync(temp, file);
  } finally {
    if (fs.existsSync(temp)) fs.rmSync(temp, { force: true });
  }
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (_) {
    return null;
  }
}

function normalizeEntry(entry) {
  if (!entry || typeof entry.app !== "string" || typeof entry.commit !== "string") return null;
  return {
    app: path.resolve(entry.app),
    commit: entry.commit,
    branch: String(entry.branch || "main"),
    activatedAt: String(entry.activatedAt || ""),
  };
}

function readState(home) {
  const value = readJson(statePath(home));
  return {
    version: STATE_VERSION,
    current: normalizeEntry(value && value.current),
    previous: normalizeEntry(value && value.previous),
  };
}

function releaseRoot(home) {
  return path.join(path.resolve(home), "releases");
}

function isWithin(parent, target) {
  const root = path.resolve(parent) + path.sep;
  return path.resolve(target).startsWith(root);
}

function validate({ home, app, commit }) {
  if (!/^[A-Za-z0-9._-]{4,128}$/.test(String(commit || ""))) {
    throw new Error("invalid release commit");
  }
  const resolved = path.resolve(app);
  if (!isWithin(releaseRoot(home), resolved)) {
    throw new Error(`release is outside the managed release root: ${resolved}`);
  }
  const pkg = readJson(path.join(resolved, "package.json"));
  if (!pkg || pkg.name !== "kx-defender" || typeof pkg.version !== "string") {
    throw new Error(`invalid release package: ${resolved}`);
  }
  const entry = path.join(resolved, "scripts", "npm-kx.js");
  if (!fs.existsSync(entry)) throw new Error(`release entry is missing: ${entry}`);
  return { app: resolved, version: pkg.version };
}

function activate({ home, app, commit, branch = "main" }) {
  const valid = validate({ home, app, commit });
  const old = readState(home);
  const current = {
    app: valid.app,
    commit: String(commit),
    branch: String(branch),
    activatedAt: new Date().toISOString(),
  };
  const previous = old.current && old.current.app !== current.app ? old.current : old.previous;
  const next = { version: STATE_VERSION, current, previous: previous || null };
  atomicWriteJson(statePath(home), next);
  return readState(home);
}

function rollback(home) {
  const state = readState(home);
  if (!state.previous) throw new Error("no previous release is available");
  validate({ home, app: state.previous.app, commit: state.previous.commit });
  const next = {
    version: STATE_VERSION,
    current: {
      ...state.previous,
      activatedAt: new Date().toISOString(),
    },
    previous: state.current,
  };
  atomicWriteJson(statePath(home), next);
  return readState(home);
}

function currentApp(home) {
  const state = readState(home);
  if (!state.current) return null;
  try {
    validate({ home, app: state.current.app, commit: state.current.commit });
    return state.current.app;
  } catch (_) {
    return null;
  }
}

module.exports = {
  STATE_VERSION,
  statePath,
  readState,
  validate,
  activate,
  rollback,
  currentApp,
  atomicWriteJson,
  releaseRoot,
};
