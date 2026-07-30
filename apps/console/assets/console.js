const $ = (id) => document.getElementById(id);

// ============================================================
// State (single UI instance — DOM never regenerated)
// ============================================================
const state = {
  runCount: 0,
  commandHistory: [],
  historyIndex: -1,
  execStartTime: 0,
  execTimer: null,
  activePanel: null,
};

const LS_HISTORY_KEY = "kx-cmd-history";

// ============================================================
// Command Routing (verb → panel)
// ============================================================
const VERB_PANEL = {
  // Sentry / Defense
  watch: "sentry", sentry: "sentry", sig: "sentry", triage: "sentry",
  trace: "sentry", audit: "sentry", harden: "sentry", comply: "sentry",
  forge: "sentry", kill: "sentry",
  // Strike / Attack
  roast: "strike", relay: "strike", loot: "strike", bait: "strike",
  crack: "strike", breach: "strike", probe: "strike", graph: "strike",
  // Sweep / Web
  sweep: "sweep",
  // Nexus / C2
  nexus: "nexus",
};

function routeToPanel(command) {
  const verb = command.trim().split(/\s+/)[0]?.toLowerCase() || "";
  return VERB_PANEL[verb] || "strike";
}

// ============================================================
// Command Composition
// ============================================================
function flags() {
  const scope = $("scope").value;
  const mode = $("mode").value === "live" ? "--live" : "--sim";
  return `--scope ${scope} ${mode}`;
}

function decorate(cmd) {
  const c = cmd.trim();
  if (!c) return c;
  if (c === "/h" || c.startsWith("/h ") || c.startsWith("help")) return c;
  if (c.includes("--scope")) return c;
  return `${c} ${flags()}`;
}

// ============================================================
// Status Bar Updates (Reactive — no DOM regen)
// ============================================================
function setStatus(status, className = "") {
  const el = $("stat-status");
  el.textContent = status;
  el.className = "status-value " + className;
}

function setModule(name) {
  $("stat-module").textContent = name || "—";
}

function setDuration(ms) {
  const el = $("stat-duration");
  if (ms < 1000) {
    el.textContent = `${Math.round(ms)}ms`;
  } else {
    el.textContent = `${(ms / 1000).toFixed(2)}s`;
  }
}

function setCounts(findings, artifacts, runs) {
  if (findings !== undefined) $("stat-findings").textContent = findings;
  if (artifacts !== undefined) $("stat-artifacts").textContent = artifacts;
  if (runs !== undefined) $("stat-runs").textContent = runs;
}

function startTimer() {
  state.execStartTime = performance.now();
  if (state.execTimer) clearInterval(state.execTimer);
  state.execTimer = setInterval(() => {
    setDuration(performance.now() - state.execStartTime);
  }, 100);
}

function stopTimer() {
  if (state.execTimer) {
    clearInterval(state.execTimer);
    state.execTimer = null;
  }
  const elapsed = performance.now() - state.execStartTime;
  setDuration(elapsed);
  return elapsed;
}

// ============================================================
// Panel Highlighting (Reactive — no DOM regen)
// ============================================================
function activatePanel(panelKey) {
  // Deactivate previous
  if (state.activePanel) {
    const prev = $(`panel-${state.activePanel}`);
    if (prev) prev.classList.remove("active");
  }
  // Activate new
  const el = $(`panel-${panelKey}`);
  if (el) el.classList.add("active");
  state.activePanel = panelKey;
}

function setBadge(panelKey, text, className = "") {
  const el = $(`badge-${panelKey}`);
  if (el) {
    el.textContent = text;
    el.className = "panel-badge " + className;
  }
}

// ============================================================
// Result Rendering (in-place, no regen)
// ============================================================
function renderResult(panelKey, data) {
  const out = $(`out-${panelKey}`);
  if (!out) return;

  const findings = (data.findings || []);
  const artifacts = data.artifacts || {};
  const status = data.status || "unknown";
  const module = data.module || "unknown";
  const mode = data.mode || "?";
  const errors = data.errors || [];

  // Build a formatted view
  let html = "";
  html += `<div style="color:var(--muted);margin-bottom:6px;">▸ ${module} [${mode}]</div>`;

  if (findings.length > 0) {
    html += `<div style="color:var(--orange);margin-bottom:4px;">FINDINGS (${findings.length})</div>`;
    findings.forEach((f) => {
      const sev = (f.severity || "info").toLowerCase();
      html += `<div class="finding-card ${sev}">`;
      html += `<div class="finding-title">`;
      html += `<span class="finding-severity ${sev}">${sev.toUpperCase()}</span>`;
      html += escapeHtml(f.title || "");
      html += `</div>`;
      if (f.detail) {
        html += `<div class="finding-detail">${escapeHtml(f.detail)}</div>`;
      }
      html += `</div>`;
    });
  }

  if (Object.keys(artifacts).length > 0) {
    html += `<div style="color:var(--orange);margin-top:8px;margin-bottom:4px;">ARTIFACTS</div>`;
    html += `<pre style="margin:0;color:var(--cyan);">${escapeHtml(JSON.stringify(artifacts, null, 2))}</pre>`;
  }

  if (errors.length > 0) {
    html += `<div style="color:var(--red);margin-top:8px;">ERRORS</div>`;
    errors.forEach((e) => {
      html += `<div style="color:var(--red);font-size:10px;">✗ ${escapeHtml(e)}</div>`;
    });
  }

  // Replace only the content of #out (single DOM tree, not the whole panel)
  out.innerHTML = html;
  out.scrollTop = 0;

  // Update badges
  const badgeClass = status === "ok" ? "count" : status === "error" || status === "denied" ? "" : "";
  setBadge(panelKey, `${status} • ${findings.length}f • ${Object.keys(artifacts).length}a`, badgeClass);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ============================================================
// Ledger (History Panel — appends only, no regen)
// ============================================================
function renderLedger(runs) {
  const out = $("out-ledger");
  if (!out || !Array.isArray(runs)) return;

  let html = "";
  runs.slice(0, 30).forEach((r) => {
    const time = r.created_at ? new Date(r.created_at).toLocaleTimeString() : "—";
    const status = r.status || "?";
    const module = r.module || "?";
    const duration = r.duration_ms || "—";
    html += `<div class="ledger-entry">`;
    html += `<span class="ledger-time">${escapeHtml(time)}</span>`;
    html += `<span class="ledger-status ${status}">${escapeHtml(status)}</span>`;
    html += `<span class="ledger-module">${escapeHtml(module)}</span>`;
    html += `<span class="ledger-duration">${escapeHtml(String(duration))}</span>`;
    html += `</div>`;
  });

  out.innerHTML = html || `<span style="color:var(--muted);">no runs yet</span>`;
  $("badge-ledger").textContent = runs.length;
}

// ============================================================
// Command Execution (Reactive — single UI update path)
// ============================================================
async function runKx(command) {
  const panelKey = routeToPanel(command);
  const line = decorate(command);

  // Update UI state
  activatePanel(panelKey);
  setStatus("RUNNING", "running");
  setModule(line.split(/\s+/).slice(0, 2).join(" "));
  setBadge(panelKey, "running", "");
  startTimer();

  const out = $(`out-${panelKey}`);
  if (out) out.innerHTML = `<span style="color:var(--orange);">▸ executing: ${escapeHtml(line)}</span>`;

  try {
    const res = await fetch("/api/kx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: line }),
    });
    const data = await res.json();
    stopTimer();

    // Update status bar
    const status = data.status || "error";
    const cls = status === "ok" ? "ok" : status === "error" ? "error" : status === "denied" ? "warning" : "";
    setStatus(status.toUpperCase(), cls);
    setModule(data.module || "—");
    setCounts(
      (data.findings || []).length,
      Object.keys(data.artifacts || {}).length,
      ++state.runCount
    );

    // Render into panel (in-place, no regen)
    renderResult(panelKey, data);

    // Refresh ledger
    refreshLedger();
  } catch (err) {
    stopTimer();
    setStatus("ERROR", "error");
    setBadge(panelKey, "error", "");
    if (out) out.innerHTML = `<div style="color:var(--red);">✗ ${escapeHtml(String(err))}</div>`;
  }
}

async function refreshLedger() {
  try {
    const res = await fetch("/api/results");
    const data = await res.json();
    renderLedger(data);
  } catch (err) {
    $("out-ledger").innerHTML = `<span style="color:var(--red);">ledger error: ${escapeHtml(String(err))}</span>`;
  }
}

// ============================================================
// Command History (local persistence)
// ============================================================
function loadHistory() {
  try {
    state.commandHistory = JSON.parse(localStorage.getItem(LS_HISTORY_KEY) || "[]");
  } catch { state.commandHistory = []; }
}

function pushHistory(cmd) {
  if (!cmd || cmd === state.commandHistory[0]) return;
  state.commandHistory.unshift(cmd);
  state.commandHistory = state.commandHistory.slice(0, 100);
  try {
    localStorage.setItem(LS_HISTORY_KEY, JSON.stringify(state.commandHistory));
  } catch {}
}

function navHistory(dir) {
  if (state.commandHistory.length === 0) return;
  state.historyIndex = Math.max(-1, Math.min(state.commandHistory.length - 1, state.historyIndex + dir));
  if (state.historyIndex === -1) {
    $("cmd").value = "";
  } else {
    $("cmd").value = state.commandHistory[state.historyIndex] || "";
  }
}

// ============================================================
// Initialization
// ============================================================
async function boot() {
  loadHistory();

  // Health check
  try {
    const h = await fetch("/api/health").then((r) => r.json());
    $("health").textContent = h.ok ? "ONLINE" : "DOWN";
  } catch {
    $("health").textContent = "DOWN";
  }

  // Run button
  $("run").onclick = () => {
    const cmd = $("cmd").value.trim();
    if (!cmd) return;
    pushHistory(cmd);
    state.historyIndex = -1;
    runKx(cmd);
  };

  // Clear button (resets output panels; does NOT regenerate UI)
  $("clear-btn").onclick = () => {
    ["sentry", "strike", "sweep", "nexus"].forEach((k) => {
      const out = $(`out-${k}`);
      if (out) out.textContent = "ready";
      setBadge(k, "idle", "");
    });
    if (state.activePanel) {
      $(`panel-${state.activePanel}`)?.classList.remove("active");
      state.activePanel = null;
    }
    setStatus("IDLE", "");
    setModule("—");
    setDuration(0);
    setCounts(0, 0, state.runCount);
  };

  // Enter key + history navigation
  $("cmd").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { $("run").click(); return; }
    if (e.key === "ArrowUp") { e.preventDefault(); navHistory(1); }
    if (e.key === "ArrowDown") { e.preventDefault(); navHistory(-1); }
  });

  // Quick-command buttons
  document.querySelectorAll("button[data-cmd]").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("cmd").value = btn.getAttribute("data-cmd");
      $("run").click();
    });
  });

  // Ledger refresh
  $("refresh").onclick = refreshLedger;
  refreshLedger();

  // Focus command input on load
  $("cmd").focus();
}

boot();
