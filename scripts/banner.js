"use strict";

/** Kx block logo (SKILLS-style) for PowerShell / terminal */

const KX_LOGO = `
██╗  ██╗██╗  ██╗
██║ ██╔╝╚██╗██╔╝
█████╔╝  ╚███╔╝
██╔═██╗  ██╔██╗
██║  ██╗██╔╝ ██╗
╚═╝  ╚═╝╚═╝  ╚═╝
`.trimEnd();

function printKxBanner(stream = process.stdout) {
  const line = "─".repeat(40);
  stream.write("\n");
  stream.write(KX_LOGO + "\n");
  stream.write(`  DEFENDER  ·  Self-Built Only\n`);
  stream.write(`${line}\n\n`);
}

module.exports = { KX_LOGO, printKxBanner };
