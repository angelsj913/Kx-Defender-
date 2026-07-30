"use strict";

const KX_LOGO = [
  "██╗  ██╗██╗  ██╗",
  "██║ ██╔╝╚██╗██╔╝",
  "█████╔╝  ╚███╔╝ ",
  "██╔═██╗  ██╔██╗ ",
  "██║  ██╗██╔╝ ██╗",
  "╚═╝  ╚═╝╚═╝  ╚═╝",
].join("\n");

function printKxBanner(stream = process.stdout) {
  const line = "─".repeat(50);
  stream.write("\n");
  for (const l of KX_LOGO.split("\n")) stream.write(`  ${l}\n`);
  stream.write(`  KX DEFCOM  ·  OPERATOR CLIENT\n`);
  stream.write(`${line}\n\n`);
}

module.exports = { KX_LOGO, printKxBanner };
