"use strict";

/** Kx ASCII brand mark */

const KX_LOGO = [
  "██╗  ██╗██╗  ██╗",
  "██║ ██╔╝╚██╗██╔╝",
  "█████╔╝  ╚███╔╝ ",
  "██╔═██╗  ██╔██╗ ",
  "██║  ██╗██╔╝ ██╗",
  "╚═╝  ╚═╝╚═╝  ╚═╝",
].join("\n");

function printKxBanner(stream = process.stdout) {
  const line = "─".repeat(40);
  stream.write("\n");
  stream.write(KX_LOGO + "\n");
  stream.write(`  DEFCOM OPERATOR\n`);
  stream.write(`${line}\n\n`);
}

module.exports = { KX_LOGO, printKxBanner };
