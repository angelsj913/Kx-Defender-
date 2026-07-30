#!/usr/bin/env node
"use strict";

/**
 * Quiet agent-skill installer for Kx-Defender.
 * Copies bundled skills/ into supported global skill dirs.
 * Does not call the third-party `skills` CLI (no GitHub Source line, no Eve/PromptScript noise).
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

const ROOT = path.resolve(__dirname, "..");
const SKILLS_SRC = path.join(ROOT, "skills");

function home() {
  return os.homedir();
}

/** Only dirs that support global install (skip Eve / PromptScript). */
function globalSkillRoots() {
  const h = home();
  const roots = [
    path.join(h, ".agents", "skills"),
    path.join(h, ".cursor", "skills"),
  ];
  // dedupe
  return [...new Set(roots.map((p) => path.resolve(p)))];
}

function listSkillDirs() {
  if (!fs.existsSync(SKILLS_SRC)) return [];
  return fs
    .readdirSync(SKILLS_SRC, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .filter((name) => fs.existsSync(path.join(SKILLS_SRC, name, "SKILL.md")))
    .sort();
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(from, to);
    else fs.copyFileSync(from, to);
  }
}

function installAgentSkills({ global = true } = {}) {
  const names = listSkillDirs();
  if (!names.length) {
    throw new Error("No skills found under skills/");
  }

  const targets = global
    ? globalSkillRoots()
    : [path.join(process.cwd(), ".agents", "skills")];

  const installed = [];
  for (const root of targets) {
    fs.mkdirSync(root, { recursive: true });
    for (const name of names) {
      const dest = path.join(root, name);
      if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true, force: true });
      copyDir(path.join(SKILLS_SRC, name), dest);
      installed.push({ name, root });
    }
  }

  return { names, targets, installed };
}

function printQuietSummary(result) {
  console.log(`Installed ${result.names.length} skills:`);
  for (const name of result.names) {
    console.log(`  ✓ ${name}`);
  }
  console.log(`Locations:`);
  for (const t of result.targets) {
    console.log(`  ${t}`);
  }
  console.log("Done.");
}

module.exports = {
  installAgentSkills,
  listSkillDirs,
  globalSkillRoots,
  SKILLS_SRC,
  ROOT,
};

if (require.main === module) {
  try {
    const argv = process.argv.slice(2);
    const global = argv.includes("-g") || argv.includes("--global") || !argv.includes("--project");
    const result = installAgentSkills({ global });
    printQuietSummary(result);
  } catch (err) {
    console.error(err.message || err);
    process.exit(1);
  }
}
