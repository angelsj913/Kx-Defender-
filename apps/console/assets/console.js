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
  lexicon: null,          // { verbs: { roast: {objects: [...], default_object, role, family}, ... } }
  suggestions: [],        // current suggestion list
  suggestIndex: -1,       // highlighted suggestion index
};

const LS_HISTORY_KEY = "kx-cmd-history";
const LS_LANG_KEY = "kx-ui-lang";

// ============================================================
// Client-side i18n (UI labels only)
// NOTE: Backend i18n (i18n.py, kx_cli.py) is owned by Cursor.
// This dictionary covers UI chrome only — never touches backend responses.
// ============================================================
const I18N = {
  en: {
    "scope": "SCOPE",
    "scope.lab": "LAB",
    "scope.owned": "OWNED",
    "scope.pact": "PACT",
    "mode": "MODE",
    "mode.sim": "SIM",
    "mode.live": "LIVE",
    "cmd.placeholder": "roast tickets --realm lab.local   |   /h   |   sentry detect",
    "btn.run": "RUN",
    "btn.clear": "CLEAR",
    "btn.refresh": "refresh",
    "stat.status": "STATUS",
    "stat.module": "MODULE",
    "stat.duration": "DURATION",
    "stat.findings": "FINDINGS",
    "stat.artifacts": "ARTIFACTS",
    "stat.runs": "RUNS",
    "status.idle": "IDLE",
    "status.running": "RUNNING",
    "status.ok": "OK",
    "status.error": "ERROR",
    "status.denied": "DENIED",
    "panel.sentry": "SENTRY / DEFENSE",
    "panel.strike": "STRIKE / ATTACK",
    "panel.sweep": "SWEEP / WEB",
    "panel.nexus": "NEXUS / C2",
    "panel.ledger": "LEDGER / HISTORY",
    "badge.idle": "idle",
    "badge.ready": "ready",
    "badge.running": "running",
    "badge.error": "error",
    "msg.loading": "loading…",
    "msg.no_runs": "no runs yet",
    "msg.ready": "ready",
  },
  ko: {
    "scope": "범위",
    "scope.lab": "실험실",
    "scope.owned": "자산",
    "scope.pact": "계약",
    "mode": "모드",
    "mode.sim": "시뮬레이션",
    "mode.live": "실행",
    "cmd.placeholder": "roast tickets --realm lab.local   |   /h   |   sentry detect",
    "btn.run": "실행",
    "btn.clear": "초기화",
    "btn.refresh": "새로고침",
    "stat.status": "상태",
    "stat.module": "모듈",
    "stat.duration": "소요",
    "stat.findings": "탐지",
    "stat.artifacts": "산출물",
    "stat.runs": "실행수",
    "status.idle": "대기",
    "status.running": "실행중",
    "status.ok": "정상",
    "status.error": "오류",
    "status.denied": "거부",
    "panel.sentry": "센트리 / 방어",
    "panel.strike": "스트라이크 / 공격",
    "panel.sweep": "스윕 / 웹",
    "panel.nexus": "넥서스 / C2",
    "panel.ledger": "원장 / 이력",
    "badge.idle": "대기",
    "badge.ready": "준비",
    "badge.running": "실행중",
    "badge.error": "오류",
    "msg.loading": "불러오는 중…",
    "msg.no_runs": "실행 기록 없음",
    "msg.ready": "준비",
  },
};

let currentLang = (() => {
  try {
    const saved = localStorage.getItem(LS_LANG_KEY);
    if (saved === "en" || saved === "ko") return saved;
  } catch {}
  const nav = (navigator.language || "en").slice(0, 2).toLowerCase();
  return nav === "ko" ? "ko" : "en";
})();

function t(key, fallback) {
  const dict = I18N[currentLang] || I18N.en;
  return dict[key] ?? fallback ?? key;
}

function applyI18n() {
  // Update text nodes
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    // Preserve existing content as fallback so keys stay debuggable
    el.textContent = t(key, el.textContent);
  });
  // Update placeholders
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    el.setAttribute("placeholder", t(key, el.getAttribute("placeholder") || ""));
  });
  // Update lang toggle button label to show the OTHER language
  const btn = document.getElementById("lang-toggle");
  if (btn) {
    btn.textContent = currentLang === "ko" ? "EN" : "한";
    btn.setAttribute("title", currentLang === "ko" ? "Switch to English" : "한국어로 전환");
  }
  // Update <html lang="">
  document.documentElement.setAttribute("lang", currentLang);
}

function toggleLang() {
  currentLang = currentLang === "ko" ? "en" : "ko";
  try { localStorage.setItem(LS_LANG_KEY, currentLang); } catch {}
  applyI18n();
}

// Global flag suggestions (all known flags across modules)
const GLOBAL_FLAGS = [
  { token: "--scope", hint: "lab | owned | pact | engagement", tag: "SCOPE" },
  { token: "--sim", hint: "simulate mode (default, safe)", tag: "MODE" },
  { token: "--live", hint: "execute mode (real ops)", tag: "MODE" },
  { token: "--at", hint: "target host / file / pid", tag: "FLAG" },
  { token: "--realm", hint: "AD / Entra realm domain", tag: "FLAG" },
  { token: "--url", hint: "http(s):// target url", tag: "FLAG" },
  { token: "--bind", hint: "host:port for listener", tag: "FLAG" },
  { token: "--pid", hint: "process id integer", tag: "FLAG" },
  { token: "--path", hint: "filesystem path", tag: "FLAG" },
  { token: "--pact-file", hint: "engagement pact json", tag: "FLAG" },
  { token: "--with", hint: "key=value custom param", tag: "FLAG" },
];

const SCOPE_VALUES = ["lab", "owned", "pact", "engagement"];

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
  const key = "status." + String(status).toLowerCase();
  el.textContent = t(key, status);
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
  html += `<div style="color:var(--muted);margin-bottom:6px;">▸ ${escapeHtml(module)} [${escapeHtml(mode)}]</div>`;

  if (findings.length > 0) {
    html += `<div style="color:var(--orange);margin-bottom:4px;">FINDINGS (${findings.length}) · click to expand</div>`;
    findings.forEach((f, i) => {
      const sev = (f.severity || "info").toLowerCase();
      const hasEvidence = f.evidence && Object.keys(f.evidence).length > 0;
      html += `<div class="finding-card ${sev}" data-finding-idx="${i}">`;
      html += `<div class="finding-title">`;
      html += `<span class="finding-severity ${sev}">${sev.toUpperCase()}</span>`;
      html += escapeHtml(f.title || "");
      if (hasEvidence) html += `<span class="finding-toggle">EVIDENCE ▾</span>`;
      html += `</div>`;
      if (f.detail) {
        html += `<div class="finding-detail">${escapeHtml(f.detail)}</div>`;
      }
      if (hasEvidence) {
        const evJson = JSON.stringify(f.evidence, null, 2);
        html += `<div class="finding-evidence">`;
        html += `<button class="evidence-copy" data-copy="${escapeAttr(evJson)}">COPY</button>`;
        html += renderJsonSyntax(f.evidence);
        html += `</div>`;
      }
      html += `</div>`;
    });
  }

  if (Object.keys(artifacts).length > 0) {
    // Specialized widgets for defense modules (process tree, signature matrix)
    const widget = renderSpecialWidget(module, artifacts);
    if (widget) {
      html += widget;
    } else {
      html += `<div style="color:var(--orange);margin-top:8px;margin-bottom:4px;">ARTIFACTS</div>`;
      html += `<div class="artifact-tree">${renderArtifactTree(artifacts)}</div>`;
    }
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

  // Wire finding expansion (event delegation on the out container)
  wireFindingExpansion(out);

  // Update badges
  const badgeClass = status === "ok" ? "count" : "";
  setBadge(panelKey, `${status} • ${findings.length}f • ${Object.keys(artifacts).length}a`, badgeClass);
}

function wireFindingExpansion(container) {
  container.querySelectorAll(".finding-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      // Ignore clicks on the copy button
      if (e.target.classList.contains("evidence-copy")) return;
      card.classList.toggle("expanded");
      const toggle = card.querySelector(".finding-toggle");
      if (toggle) toggle.textContent = card.classList.contains("expanded") ? "EVIDENCE ▴" : "EVIDENCE ▾";
    });
  });
  container.querySelectorAll(".evidence-copy").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const text = btn.getAttribute("data-copy") || "";
      try {
        await navigator.clipboard.writeText(text.replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">"));
        btn.textContent = "COPIED";
        btn.classList.add("copied");
        setTimeout(() => { btn.textContent = "COPY"; btn.classList.remove("copied"); }, 1200);
      } catch {
        btn.textContent = "FAILED";
      }
    });
  });
  container.querySelectorAll(".artifact-key").forEach((key) => {
    key.addEventListener("click", () => {
      key.classList.toggle("open");
      const val = key.nextElementSibling;
      if (val && val.classList.contains("artifact-value")) {
        val.classList.toggle("open");
      }
    });
  });
}

// Syntax-highlighted JSON for evidence
function renderJsonSyntax(obj) {
  const json = JSON.stringify(obj, null, 2);
  return `<pre style="margin:0;">${json
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"([^"]+)":/g, '<span class="evidence-key">"$1"</span>:')
    .replace(/: "([^"]*)"/g, ': <span class="evidence-str">"$1"</span>')
    .replace(/: (-?\d+(?:\.\d+)?)/g, ': <span class="evidence-num">$1</span>')
    .replace(/: (true|false)/g, ': <span class="evidence-bool">$1</span>')
    .replace(/: null/g, ': <span class="evidence-null">null</span>')
  }</pre>`;
}

// Recursive collapsible artifact tree
function renderArtifactTree(obj, depth = 0) {
  if (obj === null) return `<span class="evidence-null">null</span>`;
  if (typeof obj !== "object") {
    return `<span class="artifact-leaf">${escapeHtml(String(obj))}</span>`;
  }
  const isArray = Array.isArray(obj);
  const entries = isArray ? obj.map((v, i) => [i, v]) : Object.entries(obj);
  if (entries.length === 0) return `<span class="evidence-null">${isArray ? "[]" : "{}"}</span>`;
  let html = "";
  entries.forEach(([k, v]) => {
    const isLeaf = v === null || typeof v !== "object";
    const label = `${escapeHtml(String(k))}${isArray ? "" : ""}`;
    const count = isLeaf ? "" : ` <span style="color:var(--muted)">(${Array.isArray(v) ? v.length : Object.keys(v).length})</span>`;
    if (isLeaf) {
      html += `<div class="artifact-node"><span style="color:var(--orange)">${label}</span>: <span class="artifact-leaf">${escapeHtml(JSON.stringify(v))}</span></div>`;
    } else {
      const openByDefault = depth < 1;
      html += `<div class="artifact-node">`;
      html += `<span class="artifact-key${openByDefault ? " open" : ""}">${label}${count}</span>`;
      html += `<div class="artifact-value${openByDefault ? " open" : ""}">${renderArtifactTree(v, depth + 1)}</div>`;
      html += `</div>`;
    }
  });
  return html;
}

// ============================================================
// Specialized Widgets (defense modules)
// ============================================================
function renderSpecialWidget(moduleName, artifacts) {
  const name = String(moduleName || "").toLowerCase();
  if (name.includes("process_monitor") && Array.isArray(artifacts.processes)) {
    return renderProcessTree(artifacts);
  }
  if (name.includes("sig_scan") && (artifacts.sample_hits || artifacts.file || artifacts.rule_count !== undefined)) {
    return renderSignatureMatrix(artifacts);
  }
  return null;
}

function renderProcessTree(artifacts) {
  const procs = artifacts.processes || [];
  const alerts = artifacts.alert_count || 0;
  const engine = artifacts.engine || "KxWatch";

  // Build ppid → children map to render as a tree
  const byPpid = new Map();
  const seen = new Set();
  procs.forEach((p) => { seen.add(p.pid); });
  procs.forEach((p) => {
    // Root = ppid not in this list (orphans anchored at depth 0)
    const parent = seen.has(p.ppid) ? p.ppid : null;
    if (!byPpid.has(parent)) byPpid.set(parent, []);
    byPpid.get(parent).push(p);
  });

  function walk(parent, depth) {
    const children = byPpid.get(parent) || [];
    // Sort: high-risk first, then by pid
    children.sort((a, b) => (b.score || 0) - (a.score || 0) || a.pid - b.pid);
    let html = "";
    children.forEach((p) => {
      const level = String(p.level || "low").toLowerCase();
      const scoreClass = p.score >= 70 ? "critical" : p.score >= 45 ? "high" : "";
      const nameClass = p.score >= 70 ? "critical" : p.score >= 45 ? "high" : "";
      const indent = "  ".repeat(depth) + (depth > 0 ? "└─ " : "");
      html += `<div class="proc-node risk-${level}">`;
      html += `<div class="proc-pid">${escapeHtml(String(p.pid))}</div>`;
      html += `<div>`;
      html += `<span class="proc-indent">${escapeHtml(indent)}</span>`;
      html += `<span class="proc-name ${nameClass}">${escapeHtml(p.name || "")}</span>`;
      if (p.cmdline) html += `<span class="proc-cmdline">${escapeHtml(p.cmdline)}</span>`;
      if (Array.isArray(p.reasons) && p.reasons.length) {
        html += `<div style="margin-top:2px;">`;
        p.reasons.forEach((r) => { html += `<span class="proc-reason">${escapeHtml(r)}</span>`; });
        html += `</div>`;
      }
      html += `</div>`;
      html += `<div class="proc-score ${scoreClass}">${escapeHtml(String(p.score ?? 0))}</div>`;
      html += `</div>`;
      html += walk(p.pid, depth + 1);
    });
    return html;
  }

  let out = "";
  out += `<div class="widget-header">`;
  out += `<span>PROCESS TREE · ${escapeHtml(engine)}</span>`;
  out += `<span class="widget-stats">total <span class="accent">${procs.length}</span> · alerts <span class="danger">${alerts}</span></span>`;
  out += `</div>`;
  out += `<div class="proc-tree">${walk(null, 0)}</div>`;
  return out;
}

function renderSignatureMatrix(artifacts) {
  const hits = artifacts.sample_hits || (artifacts.file && artifacts.file.hits) || [];
  const ruleCount = artifacts.rule_count ?? "?";
  const hitCount = artifacts.hit_count ?? hits.length;
  const engine = artifacts.engine || "KxSig";

  let out = "";
  out += `<div class="widget-header">`;
  out += `<span>SIGNATURE MATRIX · ${escapeHtml(engine)}</span>`;
  out += `<span class="widget-stats">rules <span class="accent">${escapeHtml(String(ruleCount))}</span> · hits <span class="danger">${escapeHtml(String(hitCount))}</span></span>`;
  out += `</div>`;

  if (hits.length === 0) {
    out += `<div style="color:var(--muted);padding:10px 4px;font-style:italic;">no signature hits</div>`;
    return out;
  }

  out += `<div class="sig-matrix">`;
  out += `<div class="sig-row sig-header-row">`;
  out += `<div class="sig-cell">RULE ID</div><div class="sig-cell">NAME · PATTERN</div><div class="sig-cell">SEVERITY</div>`;
  out += `</div>`;
  hits.forEach((h) => {
    const sev = String(h.severity || "info").toLowerCase();
    out += `<div class="sig-row hit">`;
    out += `<div class="sig-cell sig-id">${escapeHtml(h.rule_id || "—")}</div>`;
    out += `<div class="sig-cell">`;
    out += `<span class="sig-name">${escapeHtml(h.name || "unnamed")}</span>`;
    if (h.pattern) out += `<span class="sig-pattern">${escapeHtml(h.pattern)}</span>`;
    out += `</div>`;
    out += `<div class="sig-cell"><span class="sig-sev ${sev}">${escapeHtml(sev.toUpperCase())}</span></div>`;
    out += `</div>`;
  });
  out += `</div>`;
  return out;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttr(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
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

  out.innerHTML = html || `<span style="color:var(--muted);">${t("msg.no_runs", "no runs yet")}</span>`;
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
  setStatus("running", "running");
  setModule(line.split(/\s+/).slice(0, 2).join(" "));
  setBadge(panelKey, t("badge.running", "running"), "");
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
    setStatus(status, cls);
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
    setStatus("error", "error");
    setBadge(panelKey, t("badge.error", "error"), "");
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
// Autocomplete (verb / object / flag suggestions)
// ============================================================
async function loadLexicon() {
  try {
    const res = await fetch("/api/lexicon");
    const data = await res.json();
    state.lexicon = data;
  } catch {
    state.lexicon = { verbs: {} };
  }
}

/**
 * Compute suggestions for the current input at the caret position.
 * Returns { header, items: [{token, hint, tag, replaceStart, replaceEnd}] }
 */
function computeSuggestions(input, caret) {
  if (!state.lexicon || !state.lexicon.verbs) return null;
  const verbs = state.lexicon.verbs;

  // Split up to caret (what the user has typed so far)
  const left = input.slice(0, caret);
  const tokens = left.split(/\s+/);
  const currentToken = tokens[tokens.length - 1] || "";
  const currentStart = caret - currentToken.length;

  // No input → show all verbs
  if (tokens.length === 1) {
    const items = Object.keys(verbs)
      .filter((v) => v.startsWith(currentToken.toLowerCase()))
      .sort()
      .slice(0, 40)
      .map((v) => ({
        token: v,
        hint: `${verbs[v].family || verbs[v].role || "verb"} · objs: ${(verbs[v].objects || []).slice(0, 3).join(", ")}${(verbs[v].objects || []).length > 3 ? "…" : ""}`,
        tag: "VERB",
        replaceStart: currentStart,
        replaceEnd: caret,
      }));
    return { header: `VERB (${items.length})`, items };
  }

  // Second token → suggest objects for the verb
  const verb = tokens[0].toLowerCase();
  if (tokens.length === 2 && !currentToken.startsWith("-")) {
    const meta = verbs[verb];
    if (!meta) return null;
    const items = (meta.objects || [])
      .filter((o) => o.startsWith(currentToken.toLowerCase()))
      .sort()
      .slice(0, 40)
      .map((o) => ({
        token: o,
        hint: `object of \`${verb}\`${o === meta.default_object ? " · default" : ""}`,
        tag: "OBJECT",
        replaceStart: currentStart,
        replaceEnd: caret,
      }));
    return { header: `OBJECT of ${verb} (${items.length})`, items };
  }

  // Flag value suggestion: --scope <TAB>, --sim on its own etc.
  const prevToken = tokens[tokens.length - 2] || "";
  if (prevToken === "--scope") {
    const items = SCOPE_VALUES.filter((s) => s.startsWith(currentToken.toLowerCase())).map((s) => ({
      token: s,
      hint: "authorization scope",
      tag: "SCOPE",
      replaceStart: currentStart,
      replaceEnd: caret,
    }));
    return { header: "SCOPE VALUE", items };
  }

  // Flag suggestion (starts with -)
  if (currentToken.startsWith("-") || currentToken === "") {
    const items = GLOBAL_FLAGS
      .filter((f) => f.token.startsWith(currentToken))
      .map((f) => ({ ...f, replaceStart: currentStart, replaceEnd: caret }));
    return { header: `FLAG (${items.length})`, items };
  }

  return null;
}

function renderSuggestions(payload) {
  const box = $("suggest");
  if (!payload || !payload.items || payload.items.length === 0) {
    box.classList.remove("show");
    box.innerHTML = "";
    state.suggestions = [];
    state.suggestIndex = -1;
    return;
  }
  state.suggestions = payload.items;
  state.suggestIndex = 0;

  let html = `<div class="suggest-header">${escapeHtml(payload.header || "")}  ·  TAB accept  ·  ↑↓ nav  ·  ESC close</div>`;
  payload.items.forEach((it, i) => {
    html += `<div class="suggest-item${i === 0 ? " selected" : ""}" data-idx="${i}">`;
    html += `<span class="suggest-token">${escapeHtml(it.token)}</span>`;
    html += `<span class="suggest-hint">${escapeHtml(it.hint || "")}</span>`;
    html += `<span class="suggest-tag">${escapeHtml(it.tag || "")}</span>`;
    html += `</div>`;
  });
  box.innerHTML = html;
  box.classList.add("show");

  // Wire click handlers (delegation not needed at this scale)
  box.querySelectorAll(".suggest-item").forEach((el) => {
    el.addEventListener("mousedown", (e) => {
      e.preventDefault();
      const idx = Number(el.getAttribute("data-idx"));
      acceptSuggestion(idx);
    });
  });
}

function moveSuggestion(dir) {
  if (state.suggestions.length === 0) return;
  const next = (state.suggestIndex + dir + state.suggestions.length) % state.suggestions.length;
  state.suggestIndex = next;
  const box = $("suggest");
  box.querySelectorAll(".suggest-item").forEach((el, i) => {
    el.classList.toggle("selected", i === next);
    if (i === next) el.scrollIntoView({ block: "nearest" });
  });
}

function acceptSuggestion(indexOverride) {
  const idx = indexOverride !== undefined ? indexOverride : state.suggestIndex;
  if (idx < 0 || idx >= state.suggestions.length) return;
  const it = state.suggestions[idx];
  const input = $("cmd");
  const before = input.value.slice(0, it.replaceStart);
  const after = input.value.slice(it.replaceEnd);
  const insertion = it.token + " ";
  input.value = before + insertion + after;
  const newCaret = (before + insertion).length;
  input.setSelectionRange(newCaret, newCaret);
  closeSuggestions();
  triggerSuggestions();
}

function closeSuggestions() {
  $("suggest").classList.remove("show");
  state.suggestions = [];
  state.suggestIndex = -1;
}

function triggerSuggestions() {
  const input = $("cmd");
  const caret = input.selectionStart ?? input.value.length;
  const payload = computeSuggestions(input.value, caret);
  renderSuggestions(payload);
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
  applyI18n();
  await loadLexicon();

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
      if (out) out.textContent = t("msg.ready", "ready");
      setBadge(k, t("badge.idle", "idle"), "");
    });
    if (state.activePanel) {
      $(`panel-${state.activePanel}`)?.classList.remove("active");
      state.activePanel = null;
    }
    setStatus("idle", "");
    setModule("—");
    setDuration(0);
    setCounts(0, 0, state.runCount);
  };

  // Command input events (keyboard + autocomplete)
  const cmdEl = $("cmd");
  cmdEl.addEventListener("keydown", (e) => {
    const suggestOpen = state.suggestions.length > 0 && $("suggest").classList.contains("show");

    if (e.key === "Enter") {
      if (suggestOpen && state.suggestIndex >= 0) {
        e.preventDefault();
        acceptSuggestion();
        return;
      }
      $("run").click();
      closeSuggestions();
      return;
    }
    if (e.key === "Tab") {
      if (suggestOpen && state.suggestIndex >= 0) {
        e.preventDefault();
        acceptSuggestion();
        return;
      }
    }
    if (e.key === "Escape") { closeSuggestions(); return; }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (suggestOpen) { moveSuggestion(-1); }
      else { navHistory(1); }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (suggestOpen) { moveSuggestion(1); }
      else { navHistory(-1); }
      return;
    }
  });
  cmdEl.addEventListener("input", () => triggerSuggestions());
  cmdEl.addEventListener("focus", () => triggerSuggestions());
  cmdEl.addEventListener("blur", () => setTimeout(closeSuggestions, 150));
  cmdEl.addEventListener("click", () => triggerSuggestions());

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

  // Language toggle
  const langBtn = document.getElementById("lang-toggle");
  if (langBtn) langBtn.onclick = toggleLang;

  // Focus command input on load
  $("cmd").focus();
}

boot();
