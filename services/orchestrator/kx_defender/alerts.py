"""KxAlerts — local-only alert sink.

Strict constraint: NO external services. No HTTP webhooks, no email, no
Slack/Discord, no LLM APIs. Alerts land in a JSONL file the operator reads
with `kx alert list` or tails with any standard tool (`Get-Content -Wait`
on Windows, `tail -F` on POSIX).

Storage layout::

    ~/.kx-defender/alerts.jsonl        # append-only JSON Lines log

Each line is a self-contained JSON object with UTC ISO timestamp.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Configurable via env; default is under the user's home dir.
_DEFAULT_HOME = Path(os.environ.get("KX_HOME") or (Path.home() / ".kx-defender"))
ALERT_LOG_PATH = Path(os.environ.get("KX_ALERT_LOG") or (_DEFAULT_HOME / "alerts.jsonl"))

# Cap the log to prevent unbounded growth in long-running daemon usage.
# When exceeded, oldest lines are trimmed. Fully local, no rotation daemon.
DEFAULT_MAX_LINES = int(os.environ.get("KX_ALERT_MAX_LINES") or 10000)


def _ensure_parent(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def emit_alert(
    module: str,
    title: str,
    severity: str = "medium",
    evidence: dict[str, Any] | None = None,
    also_stderr: bool = True,
    path: Path | None = None,
    max_lines: int = DEFAULT_MAX_LINES,
) -> dict[str, Any]:
    """Append a single alert record to the local JSONL log.

    Returns the record that was written.
    """
    target = path or ALERT_LOG_PATH
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "severity": str(severity or "info").lower(),
        "module": str(module),
        "title": str(title),
        "evidence": evidence or {},
    }
    _ensure_parent(target)
    try:
        from kx_defender.alert_store import AlertStore

        stored = AlertStore(target.parent / "operator.db").ingest(record)
        record.update(
            {
                "alert_id": stored["alert_id"],
                "status": stored["status"],
                "count": stored["count"],
            }
        )
    except Exception as exc:
        print(f"[kx-alerts] failed to index alert: {exc}", file=sys.stderr)
    line = json.dumps(record, ensure_ascii=False)
    try:
        # Append first — cheap and atomic on modern filesystems.
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        _maybe_trim(target, max_lines)
    except OSError as exc:
        # Alerting must never crash the caller — degrade to stderr only.
        print(f"[kx-alerts] failed to persist alert: {exc}", file=sys.stderr)
    if also_stderr:
        print(f"[ALERT {record['severity'].upper()}] {module} · {title}", file=sys.stderr)
    return record


def _maybe_trim(path: Path, max_lines: int) -> None:
    if max_lines <= 0:
        return
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return
    if len(lines) <= max_lines:
        return
    # Keep the last max_lines; write back atomically via a sibling temp file.
    tail = lines[-max_lines:]
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.writelines(tail)
        os.replace(tmp, path)
    except OSError:
        # Best-effort — leave the file as-is if replace fails.
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def read_recent_alerts(limit: int = 25, path: Path | None = None) -> list[dict[str, Any]]:
    """Return up to `limit` most recent alert records (newest first)."""
    target = path or ALERT_LOG_PATH
    if not target.is_file():
        return []
    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out


def clear_alerts(path: Path | None = None) -> int:
    """Truncate the alert log. Returns the number of lines removed."""
    target = path or ALERT_LOG_PATH
    if not target.is_file():
        return 0
    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as fh:
            count = sum(1 for _ in fh)
        target.unlink()
    except OSError:
        return 0
    return count


def emit_from_findings(
    module: str,
    findings: Iterable[dict[str, Any]],
    min_severity: str = "medium",
    also_stderr: bool = True,
    path: Path | None = None,
) -> int:
    """Persist any findings at-or-above `min_severity` as alerts.

    Returns the number of alerts written.
    """
    ranks = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    floor = ranks.get(min_severity.lower(), 2)
    written = 0
    for f in findings or []:
        sev = str(f.get("severity", "info")).lower()
        if ranks.get(sev, 0) < floor:
            continue
        emit_alert(
            module=module,
            title=str(f.get("title", "")),
            severity=sev,
            evidence=dict(f.get("evidence") or {}),
            also_stderr=also_stderr,
            path=path,
        )
        written += 1
    return written
