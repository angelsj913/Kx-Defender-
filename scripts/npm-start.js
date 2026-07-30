"use strict";

const { spawn, spawnSync } = require("child_process");
const { ensureSetup, runKx, isWin, log, ROOT } = require("./npm-setup");

function openBrowser(url) {
  try {
    if (isWin()) {
      spawn("cmd", ["/c", "start", "", url], { detached: true, stdio: "ignore" }).unref();
    } else if (process.platform === "darwin") {
      spawn("open", [url], { detached: true, stdio: "ignore" }).unref();
    } else {
      spawn("xdg-open", [url], { detached: true, stdio: "ignore" }).unref();
    }
  } catch (_) {
    /* ignore */
  }
}

try {
  ensureSetup();
  const bind = process.env.KX_BIND || "127.0.0.1:8787";
  log(`Starting Console at http://${bind}/`);
  if (process.env.KX_OPEN !== "0") {
    openBrowser(`http://${bind}/`);
  }
  const res = runKx(["serve", "--bind", bind]);
  process.exit(res.status == null ? 1 : res.status);
} catch (err) {
  console.error(`[Kx] ${err.message || err}`);
  process.exit(err.status || 1);
}
