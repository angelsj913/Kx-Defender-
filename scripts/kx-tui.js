"use strict";

const readline = require("readline");
const { spawnSync } = require("child_process");
const { Readable } = require("stream");
const { ensureSetup, SETUP_VERSION, ROOT, isWin, readState } = require("./npm-setup");
const { readLang, writeLang, splitArgs } = require("./kx-shell");
const {
  login,
  handleAuthCmd,
  load: loadUsers,
  takeBufferedInput,
} = require("./kx-auth");
const {
  clearScreen,
  colorEnabled,
  promptPrefix,
  renderDashboard,
  renderLoading,
  renderPromptBottom,
  renderPromptTop,
} = require("./terminal-ui");

const TEXT = {
  en: {
    loading: [
      "Starting secure session",
      "Preparing local runtime",
      "Loading security engines",
      "Restoring operator settings",
      "Ready",
    ],
    closed: "Session closed.",
    language: "Language changed to English.",
    languageHelp: "Use: lang en | lang ko",
  },
  ko: {
    loading: [
      "보안 세션을 시작하는 중",
      "로컬 실행 환경을 준비하는 중",
      "보안 엔진을 불러오는 중",
      "사용자 설정을 복원하는 중",
      "준비 완료",
    ],
    closed: "세션을 종료했습니다.",
    language: "언어를 한국어로 변경했습니다.",
    languageHelp: "사용법: lang en | lang ko",
  },
};

function size() {
  return {
    width: Math.max(40, process.stdout.columns || 80),
    height: Math.max(16, process.stdout.rows || 30),
  };
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildCliArgs(args) {
  return args.includes("--json") ? [...args] : ["--pretty", ...args];
}

function runCmd(args, lang) {
  const state = readState();
  const env = {
    ...process.env,
    KX_LANG: lang,
    PYTHONUTF8: "1",
    PYTHONIOENCODING: "utf-8",
  };
  const code = "import sys; from kx_defender.kx_cli import main; sys.argv=['kx']+sys.argv[1:]; main()";
  const pyExe = state?.python || (isWin() ? "python" : "python3");
  const interactive = args[0] === "ask";
  const cliArgs = buildCliArgs(args);
  const options = {
    cwd: ROOT,
    shell: false,
    windowsHide: true,
    env,
  };

  if (interactive) {
    return spawnSync(pyExe, ["-c", code, ...cliArgs], { ...options, stdio: "inherit" });
  }
  return spawnSync(pyExe, ["-c", code, ...cliArgs], {
    ...options,
    encoding: "utf8",
    stdio: ["inherit", "pipe", "pipe"],
  });
}

class KxClient {
  constructor({ bootstrap = ensureSetup } = {}) {
    this.bootstrap = bootstrap;
    this.lang = "en";
    this.user = null;
    this.lastResult = "";
    this.rl = null;
    this.loading = false;
    this.frame = 0;
    this.onResize = () => {
      if (this.loading || !this.user || !this.rl) return;
      this.draw();
      this.showPrompt(true);
    };
  }

  renderLoading(percent, label) {
    const { width } = size();
    if (process.stdout.isTTY) process.stdout.write(clearScreen());
    process.stdout.write(renderLoading({
      width,
      percent,
      label,
      frame: this.frame++,
      color: colorEnabled(),
    }));
    process.stdout.write("\n");
  }

  async pulse(percent, label, frames = 3) {
    if (!process.stdout.isTTY || process.env.TERM === "dumb") {
      console.log(`[Kx] ${label} (${percent}%)`);
      return;
    }
    for (let i = 0; i < frames; i++) {
      this.renderLoading(percent, label);
      await delay(80);
    }
  }

  async loadAfterLogin() {
    this.loading = true;
    this.lang = readLang();
    const labels = TEXT[this.lang].loading;
    await this.pulse(0, labels[0]);
    await this.pulse(20, labels[1]);
    this.renderLoading(45, labels[2]);
    this.bootstrap();
    await this.pulse(70, labels[2]);
    await this.pulse(90, labels[3]);
    await this.pulse(100, labels[4], 2);
    this.loading = false;
  }

  async start() {
    if (process.stdout.isTTY) process.stdout.write(clearScreen());
    const { width } = size();
    process.stdout.write(renderLoading({
      width,
      percent: 0,
      label: "Sign in to continue",
      frame: 0,
      color: colorEnabled(),
    }));
    process.stdout.write("\n\n");

    this.user = await login();
    await this.loadAfterLogin();
    this.openInput();
  }

  draw() {
    const { width, height } = size();
    if (process.stdout.isTTY) process.stdout.write(clearScreen());
    process.stdout.write(renderDashboard({
      width,
      height,
      lang: this.lang,
      username: this.user.username,
      result: this.lastResult,
      version: `v${SETUP_VERSION}`,
      color: colorEnabled(),
    }));
    process.stdout.write("\n");
  }

  showPrompt(refresh = false) {
    if (!this.rl || this.rl.closed) return;
    const { width } = size();
    process.stdout.write(`${renderPromptTop(width)}\n`);
    this.rl.setPrompt(promptPrefix(width));
    this.rl.prompt(refresh);
  }

  openInput() {
    this.draw();
    const bufferedInput = takeBufferedInput();
    const input = bufferedInput === null ? process.stdin : Readable.from([bufferedInput]);
    this.rl = readline.createInterface({
      input,
      output: process.stdout,
      terminal: input === process.stdin && Boolean(process.stdin.isTTY && process.stdout.isTTY),
      historySize: 100,
      removeHistoryDuplicates: true,
    });
    process.stdout.on("resize", this.onResize);
    this.rl.on("SIGINT", () => {
      process.exitCode = 130;
      this.rl.close();
    });
    this.rl.on("line", (line) => {
      const { width } = size();
      process.stdout.write(`\n${renderPromptBottom(width)}\n`);
      this.handle(line);
      if (!this.rl.closed) {
        this.draw();
        this.showPrompt();
      }
    });
    this.rl.on("close", () => {
      process.stdout.removeListener("resize", this.onResize);
      console.log(`\n[Kx] ${TEXT[this.lang].closed}`);
    });
    this.showPrompt();
  }

  handle(line) {
    const trimmed = String(line || "").trim();
    if (!trimmed) return;
    const lower = trimmed.toLowerCase();
    if (["exit", "logout", "quit", "q"].includes(lower)) {
      this.rl.close();
      return;
    }
    if (["clear", "cls"].includes(lower)) {
      this.lastResult = "";
      return;
    }

    let args = splitArgs(trimmed);
    if (args[0]?.toLowerCase() === "kx") args = args.slice(1);
    if (!args.length) args = ["/h"];
    const head = String(args[0] || "").toLowerCase();

    if (["users", "useradd", "userdel", "passwd"].includes(head)) {
      handleAuthCmd(args, loadUsers(), this.user);
      return;
    }

    if (["lang", "language", "locale", "언어"].includes(head)) {
      const raw = String(args[1] || "").toLowerCase();
      const next = ["ko", "kr", "korean", "kor", "한국어", "한국"].includes(raw)
        ? "ko"
        : ["en", "english", "eng", "us"].includes(raw) ? "en" : null;
      if (!next) {
        this.lastResult = TEXT[this.lang].languageHelp;
        return;
      }
      writeLang(next);
      this.lang = next;
      this.lastResult = TEXT[next].language;
      return;
    }

    if (["update", "upgrade"].includes(head)) {
      try {
        require("./kx-update").updateKx();
        this.lastResult = this.lang === "ko" ? "업데이트가 완료되었습니다." : "Update completed.";
      } catch (err) {
        this.lastResult = `[update] ${err.message || err}`;
      }
      return;
    }

    const result = runCmd(args, this.lang);
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
    this.lastResult = output || (
      result.status === 0
        ? (this.lang === "ko" ? "명령을 완료했습니다." : "Command completed.")
        : (this.lang === "ko" ? `명령 실패 (코드 ${result.status ?? 1})` : `Command failed (code ${result.status ?? 1}).`)
    );
  }
}

function startKxTui(options) {
  const ui = new KxClient(options);
  ui.start().catch((err) => {
    console.error(`[Kx] ${err.message || err}`);
    process.exitCode = 1;
  });
  return ui;
}

function startEdexShell(options) { return startKxTui(options); }
function startKxClient(options) { return startKxTui(options); }

module.exports = {
  startKxTui,
  startEdexShell,
  startKxClient,
  KxClient,
  EdexShell: KxClient,
  buildCliArgs,
  runCmd,
};

if (require.main === module) startKxTui();
