"use strict";

/** Kx ASCII brand mark — single-cell safe for Windows Terminal */

const KX_LOGO = `
  _  __
 | |/ /__  __
 | ' </\\ \\/ /
 |_|\\_\\\\_/\\_\\
`.trimEnd();

function printKxBanner(stream = process.stdout) {
  const line = "─".repeat(40);
  stream.write("\n");
  stream.write(KX_LOGO + "\n");
  stream.write(`  DEFCOM OPERATOR\n`);
  stream.write(`${line}\n\n`);
}

module.exports = { KX_LOGO, printKxBanner };
