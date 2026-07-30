"""KxReport — aggregate the local alerts.jsonl into readable summaries.

Pure stdlib. Reads alerts.jsonl and produces:
  - text (default, colorized)
  - json (machine-readable)
  - markdown (share/paste-ready)

Time window is any timedelta in hours (default 24). No external services.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from kx_defender.alerts import ALERT_LOG_PATH


SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def _parse_ts(ts: str) -> datetime | None:
    try:
        # Handle both '+00:00' and 'Z' suffixes.
        s = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def load_alerts(path=None) -> list[dict[str, Any]]:
    target = path or ALERT_LOG_PATH
    if not target.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return out


def summarize(
    alerts: list[dict[str, Any]] | None = None,
    hours: float = 24.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return an aggregated summary over the last `hours` hours."""
    alerts = alerts if alerts is not None else load_alerts()
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max(0.0, float(hours)))

    windowed: list[dict[str, Any]] = []
    for a in alerts:
        ts = _parse_ts(str(a.get("ts", "")))
        if ts is None or ts < cutoff:
            continue
        windowed.append(a)

    by_severity: Counter[str] = Counter()
    by_module: Counter[str] = Counter()
    by_title: Counter[str] = Counter()
    per_hour: Counter[str] = Counter()  # key: 'YYYY-MM-DDTHH'
    latest_per_severity: dict[str, dict[str, Any]] = {}

    for a in windowed:
        sev = str(a.get("severity", "info")).lower()
        mod = str(a.get("module", "?"))
        title = str(a.get("title", ""))
        by_severity[sev] += 1
        by_module[mod] += 1
        by_title[f"{mod}::{title}"] += 1
        ts = _parse_ts(str(a.get("ts", "")))
        if ts is not None:
            per_hour[ts.strftime("%Y-%m-%dT%H")] += 1
        prev = latest_per_severity.get(sev)
        if prev is None or str(a.get("ts", "")) > str(prev.get("ts", "")):
            latest_per_severity[sev] = a

    return {
        "generated_at": now.isoformat(),
        "window_hours": hours,
        "cutoff": cutoff.isoformat(),
        "alerts_total": len(windowed),
        "by_severity": {s: by_severity.get(s, 0) for s in SEVERITY_ORDER if by_severity.get(s)},
        "by_module": dict(by_module.most_common()),
        "top_titles": [
            {"module_title": k, "count": v} for k, v in by_title.most_common(10)
        ],
        "per_hour": dict(sorted(per_hour.items())),
        "latest_per_severity": latest_per_severity,
    }


def render_text(summary: dict[str, Any], color: bool | None = None) -> str:
    from kx_defender.render import _color_enabled, _c, _SEV_COLOR  # noqa: PLC0415
    from kx_defender.i18n import get_lang, t as _t  # noqa: PLC0415

    use_color = _color_enabled(color)
    reset = _c("reset", use_color)
    orange = _c("orange", use_color)
    accent = _c("accent", use_color)
    muted = _c("muted", use_color)
    _lg = get_lang()

    total = summary.get("alerts_total", 0)
    hours = summary.get("window_hours", 0)
    generated = summary.get("generated_at", "?")
    lines = [
        f"{orange}{_t('KX-DEFENDER REPORT', 'KX-DEFENDER 리포트', _lg)}{reset}  {muted}·{reset}  "
        f"{_t('window','기간',_lg)}={accent}{hours}h{reset}  "
        f"{_t('generated','생성시각',_lg)}={muted}{generated}{reset}",
        f"{_t('total alerts','전체 알람',_lg)}: {accent}{total}{reset}",
        "",
    ]

    by_sev = summary.get("by_severity") or {}
    if by_sev:
        lines.append(f"{orange}{_t('BY SEVERITY','심각도별',_lg)}{reset}")
        for sev in SEVERITY_ORDER:
            if sev not in by_sev:
                continue
            sev_c = _SEV_COLOR.get(sev, "") if use_color else ""
            lines.append(f"  {sev_c}{sev.upper():<8}{reset} {by_sev[sev]}")
        lines.append("")

    by_mod = summary.get("by_module") or {}
    if by_mod:
        lines.append(f"{orange}{_t('BY MODULE','모듈별',_lg)}{reset}")
        for mod, n in list(by_mod.items())[:15]:
            lines.append(f"  {accent}{mod:<40}{reset} {n}")
        lines.append("")

    top = summary.get("top_titles") or []
    if top:
        lines.append(f"{orange}{_t('TOP EVENTS','상위 이벤트',_lg)}{reset}")
        for entry in top:
            mt = entry.get("module_title", "?")
            n = entry.get("count", 0)
            lines.append(f"  {n:>4}  {mt}")
        lines.append("")

    per_hour = summary.get("per_hour") or {}
    if per_hour:
        peak_key = max(per_hour, key=per_hour.get)
        peak_n = per_hour[peak_key]
        lines.append(f"{orange}{_t('PEAK HOUR','피크 시각',_lg)}{reset}  {muted}(UTC){reset}")
        lines.append(f"  {accent}{peak_key}{reset}  → {peak_n} {_t('alerts','건',_lg)}")
        lines.append("")

    latest = summary.get("latest_per_severity") or {}
    if latest:
        lines.append(f"{orange}{_t('LATEST PER SEVERITY','심각도별 최신',_lg)}{reset}")
        for sev in SEVERITY_ORDER:
            if sev not in latest:
                continue
            a = latest[sev]
            sev_c = _SEV_COLOR.get(sev, "") if use_color else ""
            lines.append(
                f"  {sev_c}{sev.upper():<8}{reset} {muted}{a.get('ts','?')}{reset}  "
                f"{a.get('module','?')}  ·  {a.get('title','')}"
            )
    return "\n".join(lines) + "\n"


def render_markdown(summary: dict[str, Any]) -> str:
    total = summary.get("alerts_total", 0)
    hours = summary.get("window_hours", 0)
    generated = summary.get("generated_at", "?")
    lines = [
        f"# Kx-Defender Report",
        "",
        f"- **Window**: {hours}h",
        f"- **Generated**: {generated}",
        f"- **Total alerts**: {total}",
        "",
    ]
    by_sev = summary.get("by_severity") or {}
    if by_sev:
        lines += ["## By Severity", "", "| Severity | Count |", "|---|---:|"]
        for sev in SEVERITY_ORDER:
            if sev in by_sev:
                lines.append(f"| {sev} | {by_sev[sev]} |")
        lines.append("")
    by_mod = summary.get("by_module") or {}
    if by_mod:
        lines += ["## By Module", "", "| Module | Count |", "|---|---:|"]
        for mod, n in list(by_mod.items())[:20]:
            lines.append(f"| `{mod}` | {n} |")
        lines.append("")
    top = summary.get("top_titles") or []
    if top:
        lines += ["## Top Events", "", "| Count | Module :: Title |", "|---:|---|"]
        for e in top:
            lines.append(f"| {e.get('count',0)} | `{e.get('module_title','?')}` |")
        lines.append("")
    return "\n".join(lines) + "\n"
