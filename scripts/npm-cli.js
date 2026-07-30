#!/usr/bin/env node
"use strict";

const args = process.argv.slice(2);
if (args.length === 0 || args[0] === "serve") {
  require("./npm-start.js");
} else if (args[0] === "setup") {
  require("./npm-setup.js");
} else {
  process.argv = [process.argv[0], process.argv[1], ...args];
  require("./npm-kx.js");
}
