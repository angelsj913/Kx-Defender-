#!/usr/bin/env node
"use strict";

const { runKx } = require("./npm-setup");

const args = process.argv.slice(2);
const res = runKx(args);
process.exit(res.status == null ? 1 : res.status);
