"""Read-only operations dashboard snapshots for CLI and terminal clients."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from kx_defender.alert_store import AlertStore
from kx_defender.daemon import daemon_status
from kx_defender.kxsig_workbench import RuleWorkbench
from kx_defender.store import RunStore

SECTIONS = ("overview", "alerts", "runs", "cases", "rules", "health")
SEVERITIES = ("critical", "high", "medium", "low", "info")
ALERT_STATUSES = ("new", "acknowledged", "resolved")


def _parse_time(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _home() -> Path:
    return Path(os.environ.get("KX_HOME") or (Path.home() / ".kx-defender")).resolve()


def _release(home: Path) -> dict[str, Any]:
    try:
        state = json.loads((home / "current.json").read_text(encoding="utf-8"))
        current = state.get("current") if isinstance(state, dict) else None
        if isinstance(current, dict):
            return {
                "commit": current.get("commit"),
                "branch": current.get("branch"),
                "activated_at": current.get("activatedAt"),
                "rollback_available": isinstance(state.get("previous"), dict),
            }
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "commit": None,
        "branch": None,
        "activated_at": None,
        "rollback_available": False,
    }


def _rule_summary(workbench: RuleWorkbench) -> dict[str, Any]:
    return workbench.summary()


def build_snapshot(
    section: str = "overview",
    *,
    alert_store: AlertStore | None = None,
    run_store: RunStore | None = None,
    rule_workbench: RuleWorkbench | None = None,
    daemon_provider: Callable[[], dict[str, Any]] = daemon_status,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a bounded snapshot without changing operator state."""
    name = str(section or "overview").lower()
    if name not in SECTIONS:
        raise ValueError(f"unknown dashboard section: {name}")

    if name == "alerts":
        items = (alert_store or AlertStore()).list_alerts(limit=50)
        counts = {status: 0 for status in ALERT_STATUSES}
        for item in items:
            status = str(item.get("status") or "")
            if status in counts:
                counts[status] += 1
        return {"section": name, "by_status": counts, "items": items[:10]}

    if name == "runs":
        items = (run_store or RunStore()).list_runs(limit=10)
        return {"section": name, "items": items}

    if name == "cases":
        items = (alert_store or AlertStore()).list_cases(limit=10)
        return {
            "section": name,
            "open": sum(item.get("status") == "open" for item in items),
            "items": items,
        }

    if name == "rules":
        return {"section": name, **_rule_summary(rule_workbench or RuleWorkbench())}

    if name == "health":
        home = _home()
        return {
            "section": name,
            "daemon": daemon_provider(),
            "release": _release(home),
            "storage": {
                "home": str(home),
                "operator_db": str((home / "operator.db").resolve()),
                "home_exists": home.is_dir(),
            },
        }

    alerts = (alert_store or AlertStore()).list_alerts(limit=500)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(hours=24)
    recent = [
        item
        for item in alerts
        if (timestamp := _parse_time(item.get("last_seen"))) is not None
        and timestamp >= cutoff
    ]
    by_severity = {severity: 0 for severity in SEVERITIES}
    for item in recent:
        severity = str(item.get("severity") or "")
        if severity in by_severity:
            by_severity[severity] += 1
    cases = (alert_store or AlertStore()).list_cases(status="open", limit=500)
    runs = (run_store or RunStore()).list_runs(limit=1)
    return {
        "section": name,
        "daemon": daemon_provider(),
        "alerts_24h": {"total": len(recent), "by_severity": by_severity},
        "open_cases": len(cases),
        "latest_run": runs[0] if runs else None,
    }


def render_snapshot(snapshot: dict[str, Any]) -> str:
    """Render a compact, stable human view for terminals."""
    section = str(snapshot["section"])
    lines = [f"Operations / {section.title()}"]
    if section == "overview":
        daemon = snapshot["daemon"]
        lines.append(f"Daemon: {'running' if daemon.get('running') else 'stopped'}")
        counts = snapshot["alerts_24h"]["by_severity"]
        lines.append(
            "Alerts (24h): "
            f"{snapshot['alerts_24h']['total']} total | "
            + " ".join(f"{key}={counts[key]}" for key in SEVERITIES)
        )
        lines.append(f"Open cases: {snapshot['open_cases']}")
        latest = snapshot.get("latest_run")
        lines.append(
            "Latest run: "
            + (
                f"{latest['run_id']} {latest['module']} {latest['status']}"
                if latest
                else "none"
            )
        )
    elif section == "alerts":
        counts = snapshot["by_status"]
        lines.append("Status: " + " ".join(f"{key}={counts[key]}" for key in ALERT_STATUSES))
        lines.extend(
            f"{item['alert_id']} {item['severity']} {item['status']} {item['title']}"
            for item in snapshot["items"]
        )
    elif section == "runs":
        lines.extend(
            f"{item['run_id']} {item['module']} {item['status']} {item['created_at']}"
            for item in snapshot["items"]
        )
    elif section == "cases":
        lines.append(f"Open cases shown: {snapshot['open']}")
        lines.extend(
            f"{item['case_id']} {item['severity']} {item['status']} {item['title']}"
            for item in snapshot["items"]
        )
    elif section == "rules":
        lines.append(
            f"Rules: total={snapshot['total']} enabled={snapshot['enabled']} "
            f"disabled={snapshot['disabled']} quarantined={snapshot['quarantined']}"
        )
        lines.append(
            f"Integrity: conflicts={snapshot['conflicts']} "
            f"invalid_files={snapshot['invalid_files']}"
        )
    else:
        daemon = snapshot["daemon"]
        release = snapshot["release"]
        lines.append(f"Daemon: {'running' if daemon.get('running') else 'stopped'}")
        lines.append(
            f"Release: {release.get('commit') or 'unmanaged'} "
            f"branch={release.get('branch') or '-'} "
            f"rollback={'yes' if release.get('rollback_available') else 'no'}"
        )
        lines.append(
            f"Storage: {'ready' if snapshot['storage']['home_exists'] else 'not initialized'}"
        )
    return "\n".join(lines)
