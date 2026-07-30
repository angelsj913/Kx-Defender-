const $ = (id) => document.getElementById(id);

function flags() {
  const scope = $("scope").value;
  const mode = $("mode").value === "live" ? "--live" : "--sim";
  return `--scope ${scope} ${mode}`;
}

function decorate(cmd) {
  const c = cmd.trim();
  if (!c) return c;
  if (c === "/h" || c.startsWith("/h ")) return c;
  if (c.includes("--scope")) return c;
  return `${c} ${flags()}`;
}

async function runKx(command, outId) {
  const out = $(outId);
  out.textContent = "running…";
  const line = decorate(command);
  try {
    const res = await fetch("/api/kx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: line }),
    });
    const data = await res.json();
    out.textContent = JSON.stringify(data, null, 2);
    refreshLedger();
  } catch (err) {
    out.textContent = String(err);
  }
}

async function refreshLedger() {
  const res = await fetch("/api/results");
  const data = await res.json();
  $("out-ledger").textContent = JSON.stringify(data, null, 2);
}

async function boot() {
  try {
    const h = await fetch("/api/health").then((r) => r.json());
    $("health").textContent = h.ok ? "ONLINE" : "DOWN";
  } catch {
    $("health").textContent = "DOWN";
  }
  $("run").onclick = () => {
    const cmd = $("cmd").value.trim();
    if (!cmd) return;
    const target =
      cmd.startsWith("watch") || cmd.startsWith("sentry") || cmd.startsWith("sig") || cmd.startsWith("triage")
        ? "out-sentry"
        : cmd.startsWith("sweep")
          ? "out-sweep"
          : cmd.startsWith("nexus")
            ? "out-nexus"
            : "out-strike";
    runKx(cmd, target);
  };
  $("cmd").addEventListener("keydown", (e) => {
    if (e.key === "Enter") $("run").click();
  });
  document.querySelectorAll("button[data-cmd]").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("cmd").value = btn.getAttribute("data-cmd");
      $("run").click();
    });
  });
  $("refresh").onclick = refreshLedger;
  refreshLedger();
}

boot();
