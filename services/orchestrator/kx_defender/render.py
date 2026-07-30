"""ANSI-colored terminal renderers for ModuleResult payloads.

Ports the retired web UI's specialized widgets to the CLI:
  - `render_result_text(payload, color=True)` — full text view
  - `render_findings(findings, color=True)` — finding cards
  - `render_process_tree(processes, alert_count, color=True)` — process tree widget
  - `render_signature_matrix(hits, rule_count, hit_count, color=True)` — sig matrix

Every renderer returns a plain ``str`` so the caller controls where it goes
(stdout, stderr, embedded log, JSON debug wrapper, …).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Iterable


# ============================================================
# ANSI helpers
# ============================================================
_ANSI = {
    "reset":   "\x1b[0m",
    "bold":    "\x1b[1m",
    "dim":     "\x1b[2m",
    "fg":      "\x1b[38;2;186;230;236m",   # cyan-ice
    "accent":  "\x1b[38;2;0;229;255m",     # cyan-hot
    "orange":  "\x1b[38;2;255;140;0m",
    "green":   "\x1b[38;2;35;209;139m",
    "red":     "\x1b[38;2;255;56;96m",
    "yellow":  "\x1b[38;2;255;207;64m",
    "muted":   "\x1b[38;2;70;100;110m",
}

_SEV_COLOR = {
    "critical": _ANSI["red"],
    "high":     _ANSI["orange"],
    "medium":   _ANSI["yellow"],
    "low":      _ANSI["accent"],
    "info":     _ANSI["muted"],
}


def _isatty(stream=None) -> bool:
    stream = stream or sys.stdout
    try:
        return bool(getattr(stream, "isatty", lambda: False)())
    except Exception:
        return False


def _color_enabled(color_flag: bool | None) -> bool:
    if color_flag is False:
        return False
    if color_flag is True:
        return True
    # Auto: respect NO_COLOR, otherwise TTY
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("KX_NO_COLOR"):
        return False
    return _isatty()


def _c(name: str, use_color: bool) -> str:
    return _ANSI[name] if use_color else ""


def _clip(s: str, width: int) -> str:
    s = str(s)
    if len(s) <= width:
        return s
    return s[: max(0, width - 1)] + "…"


# ============================================================
# Findings
# ============================================================
def render_findings(findings: Iterable[dict[str, Any]], color: bool | None = None) -> str:
    use_color = _color_enabled(color)
    reset = _c("reset", use_color)
    orange = _c("orange", use_color)
    muted = _c("muted", use_color)
    accent = _c("accent", use_color)

    items = list(findings or [])
    if not items:
        return f"{muted}(no findings){reset}\n"

    lines: list[str] = []
    lines.append(f"{orange}FINDINGS ({len(items)}){reset}")
    for f in items:
        sev = str(f.get("severity", "info")).lower()
        sev_color = _SEV_COLOR.get(sev, _ANSI["muted"]) if use_color else ""
        badge = f"[{sev.upper():^8}]"
        title = f.get("title", "")
        lines.append(f"  {sev_color}{badge}{reset} {title}")
        detail = f.get("detail")
        if detail:
            lines.append(f"    {muted}{detail}{reset}")
        evidence = f.get("evidence") or {}
        if evidence:
            for line in _dump_evidence(evidence, use_color):
                lines.append(f"    {accent}│{reset} {line}")
    return "\n".join(lines) + "\n"


def _dump_evidence(obj: Any, use_color: bool, indent: int = 0) -> list[str]:
    """Compact key: value dump for evidence dicts (2-space indent per level)."""
    orange = _c("orange", use_color)
    green = _c("green", use_color)
    yellow = _c("yellow", use_color)
    red = _c("red", use_color)
    muted = _c("muted", use_color)
    reset = _c("reset", use_color)

    pad = "  " * indent
    lines: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{orange}{k}{reset}:")
                lines.extend(_dump_evidence(v, use_color, indent + 1))
            else:
                lines.append(f"{pad}{orange}{k}{reset}: {_fmt_leaf(v, use_color)}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{muted}[{i}]{reset}")
                lines.extend(_dump_evidence(v, use_color, indent + 1))
            else:
                lines.append(f"{pad}{muted}[{i}]{reset} {_fmt_leaf(v, use_color)}")
    else:
        lines.append(f"{pad}{_fmt_leaf(obj, use_color)}")
    return lines


def _fmt_leaf(v: Any, use_color: bool) -> str:
    green = _c("green", use_color)
    yellow = _c("yellow", use_color)
    red = _c("red", use_color)
    muted = _c("muted", use_color)
    reset = _c("reset", use_color)
    if v is None:
        return f"{muted}null{reset}"
    if isinstance(v, bool):
        return f"{red}{str(v).lower()}{reset}"
    if isinstance(v, (int, float)):
        return f"{yellow}{v}{reset}"
    if isinstance(v, str):
        return f"{green}{v}{reset}"
    try:
        return f"{green}{json.dumps(v, ensure_ascii=False)}{reset}"
    except (TypeError, ValueError):
        return f"{green}{v!r}{reset}"


# ============================================================
# Process Tree (KxWatch)
# ============================================================
def render_process_tree(
    processes: list[dict[str, Any]],
    alert_count: int = 0,
    engine: str = "KxWatch",
    color: bool | None = None,
) -> str:
    use_color = _color_enabled(color)
    reset = _c("reset", use_color)
    orange = _c("orange", use_color)
    accent = _c("accent", use_color)
    muted = _c("muted", use_color)
    red = _c("red", use_color)
    yellow = _c("yellow", use_color)

    lines = [
        f"{orange}PROCESS TREE{reset}  {muted}·{reset}  engine={accent}{engine}{reset}  "
        f"{muted}·{reset}  total={accent}{len(processes)}{reset}  alerts={red}{alert_count}{reset}",
    ]

    # Build ppid → children map. PIDs not in the list anchor at depth 0.
    seen = {p.get("pid") for p in processes}
    by_ppid: dict[Any, list[dict[str, Any]]] = {}
    for p in processes:
        parent = p.get("ppid")
        if parent not in seen:
            parent = None
        by_ppid.setdefault(parent, []).append(p)

    def walk(parent, depth):
        kids = sorted(
            by_ppid.get(parent, []),
            key=lambda x: (-(x.get("score") or 0), x.get("pid") or 0),
        )
        for p in kids:
            level = str(p.get("level", "low")).lower()
            score = p.get("score") or 0
            score_color = red if score >= 70 else orange if score >= 45 else muted
            level_marker = red if level in {"critical","high"} else muted
            branch = ""
            if depth > 0:
                branch = ("  " * (depth - 1)) + "└─ "
            pid = p.get("pid", "?")
            name = p.get("name", "")
            cmd = p.get("cmdline", "") or ""
            lines.append(
                f"  {muted}pid={reset}{accent}{pid:<6}{reset} "
                f"{level_marker}{level:<8}{reset} "
                f"score={score_color}{score:>3}{reset}  {branch}{name}"
            )
            if cmd:
                lines.append(f"      {muted}└ {_clip(cmd, 96)}{reset}")
            reasons = p.get("reasons") or []
            if reasons:
                tags = "  ".join(f"{orange}[{r}]{reset}" for r in reasons)
                lines.append(f"      {tags}")
            walk(pid, depth + 1)

    walk(None, 0)
    return "\n".join(lines) + "\n"


# ============================================================
# Signature Matrix (KxSig)
# ============================================================
def render_signature_matrix(
    hits: list[dict[str, Any]],
    rule_count: int | str = "?",
    hit_count: int | None = None,
    engine: str = "KxSig",
    color: bool | None = None,
) -> str:
    use_color = _color_enabled(color)
    reset = _c("reset", use_color)
    orange = _c("orange", use_color)
    accent = _c("accent", use_color)
    muted = _c("muted", use_color)
    hits = list(hits or [])
    if hit_count is None:
        hit_count = len(hits)

    lines = [
        f"{orange}SIGNATURE MATRIX{reset}  {muted}·{reset}  engine={accent}{engine}{reset}  "
        f"{muted}·{reset}  rules={accent}{rule_count}{reset}  hits={accent}{hit_count}{reset}",
    ]

    if not hits:
        lines.append(f"  {muted}(no signature hits){reset}")
        return "\n".join(lines) + "\n"

    header = f"  {muted}{'RULE ID':<14}{'SEV':<10}{'NAME':<28}PATTERN{reset}"
    lines.append(header)
    lines.append(f"  {muted}{'-'*70}{reset}")
    for h in hits:
        rid = str(h.get("rule_id", "—"))
        sev = str(h.get("severity", "info")).lower()
        sev_c = _SEV_COLOR.get(sev, _ANSI["muted"]) if use_color else ""
        name = str(h.get("name", "unnamed"))
        pat = str(h.get("pattern", ""))
        lines.append(
            f"  {accent}{rid:<14}{reset}{sev_c}{sev.upper():<10}{reset}{name:<28}{_clip(pat, 40)}"
        )
    return "\n".join(lines) + "\n"


# ============================================================
# Top-level dispatcher
# ============================================================
def render_result_text(payload: dict[str, Any], color: bool | None = None) -> str:
    """Render a ModuleResult dict as a colored, human-readable text block."""
    use_color = _color_enabled(color)
    reset = _c("reset", use_color)
    orange = _c("orange", use_color)
    accent = _c("accent", use_color)
    muted = _c("muted", use_color)
    red = _c("red", use_color)
    green = _c("green", use_color)
    yellow = _c("yellow", use_color)

    status = str(payload.get("status", "?"))
    status_c = green if status == "ok" else red if status == "error" else yellow if status == "denied" else muted
    module = str(payload.get("module", "?"))
    mode = str(payload.get("mode", "?"))
    scope = str(payload.get("authorized_scope", "?"))
    run_id = str(payload.get("run_id", ""))[:8]

    header = (
        f"{orange}▸{reset} {accent}{module}{reset}  "
        f"{muted}status={reset}{status_c}{status}{reset}  "
        f"{muted}mode={reset}{mode}  "
        f"{muted}scope={reset}{scope}  "
        f"{muted}run={reset}{run_id}"
    )

    parts = [header, ""]

    # Findings
    findings = payload.get("findings") or []
    if findings:
        parts.append(render_findings(findings, color=color))

    # Errors
    errors = payload.get("errors") or []
    if errors:
        parts.append(f"{red}ERRORS{reset}")
        for e in errors:
            parts.append(f"  {red}✗{reset} {e}")
        parts.append("")

    # Specialized widgets vs generic artifacts.
    # Match module name exactly (not substring) so future modules whose names
    # incidentally contain "process_monitor" or "sig_scan" don't get pushed
    # through the wrong renderer.
    artifacts = payload.get("artifacts") or {}
    module_key = module.lower()
    rendered_widget = False

    if module_key == "process_monitor" and isinstance(artifacts.get("processes"), list):
        parts.append(render_process_tree(
            processes=artifacts["processes"],
            alert_count=artifacts.get("alert_count", 0),
            engine=str(artifacts.get("engine") or "KxWatch"),
            color=color,
        ))
        rendered_widget = True
    elif module_key == "sig_scan" and (artifacts.get("sample_hits") or artifacts.get("file")):
        hits = artifacts.get("sample_hits")
        if hits is None and isinstance(artifacts.get("file"), dict):
            hits = artifacts["file"].get("hits", [])
        parts.append(render_signature_matrix(
            hits=hits or [],
            rule_count=artifacts.get("rule_count", "?"),
            hit_count=artifacts.get("hit_count"),
            engine=str(artifacts.get("engine") or "KxSig"),
            color=color,
        ))
        rendered_widget = True

    if not rendered_widget and artifacts:
        parts.append(f"{orange}ARTIFACTS{reset}")
        # Skip the noisy report_html blob if present
        preview = {k: v for k, v in artifacts.items() if k != "report_html"}
        parts.extend(f"  {ln}" for ln in _dump_evidence(preview, use_color))
        if "report_html" in artifacts:
            parts.append(f"  {muted}(report_html: {len(artifacts['report_html'])} bytes omitted){reset}")

    return "\n".join(parts) + "\n"
