"""KxExport — write local telemetry to portable files.

Sources:
  - alerts:  ~/.kx-defender/alerts.jsonl (via kx_defender.alerts)
  - runs:    orchestrator's RunStore (SQLite via kx_defender.store)

Sinks (chosen with --format):
  - json     one file, canonical JSON with metadata wrapper
  - jsonl    line-delimited JSON (streaming-friendly)
  - csv      row-per-record (nested fields flattened to JSON strings)

All I/O local. Nothing is uploaded anywhere.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# We keep our own minimal JSONL reader to avoid coupling to alerts.py internals.


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
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


def _read_runs(limit: int = 10000) -> list[dict[str, Any]]:
    from kx_defender.orchestrator import Orchestrator  # noqa: PLC0415
    orch = Orchestrator()
    return orch.list_results(limit=limit)


def _flatten(value: Any) -> str:
    """CSV-friendly stringifier for nested fields."""
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    # Determine union of keys, preserving first-seen order.
    seen: dict[str, None] = {}
    for r in rows:
        for k in r.keys():
            seen.setdefault(k, None)
    fieldnames = list(seen.keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: _flatten(r.get(k)) for k in fieldnames})
    return buf.getvalue()


def _to_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def _to_json(rows: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    return json.dumps({"meta": meta, "records": rows}, indent=2, ensure_ascii=False) + "\n"


def export(
    source: str,
    fmt: str = "json",
    out_path: Path | None = None,
    limit: int = 10000,
    alerts_path: Path | None = None,
) -> dict[str, Any]:
    """Export ``source`` (alerts | runs | all) in ``fmt``.

    When ``out_path`` is None, writes into ``~/.kx-defender/exports/<name>-<ts>.<ext>``.
    """
    src = source.lower()
    if src not in {"alerts", "runs", "all"}:
        return {"exported": False, "error": f"unknown source: {source}"}
    fmt = fmt.lower()
    if fmt not in {"json", "jsonl", "csv"}:
        return {"exported": False, "error": f"unknown format: {fmt}"}

    from kx_defender.alerts import ALERT_LOG_PATH, _DEFAULT_HOME as KX_HOME  # noqa: PLC0415

    rows: list[dict[str, Any]] = []
    if src in {"alerts", "all"}:
        rows.extend(_tag(_read_jsonl(alerts_path or ALERT_LOG_PATH), "alert"))
    if src in {"runs", "all"}:
        rows.extend(_tag(_read_runs(limit=limit), "run"))

    if not rows:
        return {"exported": False, "error": "no records to export", "source": src}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if out_path is None:
        exports_dir = KX_HOME / "exports"
        try: exports_dir.mkdir(parents=True, exist_ok=True)
        except OSError: pass
        out_path = exports_dir / f"kx-{src}-{ts}.{fmt}"

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": src,
        "format": fmt,
        "record_count": len(rows),
    }

    if fmt == "csv":
        payload = _to_csv(rows)
    elif fmt == "jsonl":
        payload = _to_jsonl(rows)
    else:
        payload = _to_json(rows, meta)

    try:
        out_path.write_text(payload, encoding="utf-8")
    except OSError as exc:
        return {"exported": False, "error": f"write failed: {exc}"}

    return {
        "exported": True,
        "path": str(out_path),
        "source": src,
        "format": fmt,
        "records": len(rows),
        "bytes": len(payload),
    }


def _tag(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    """Add ``_kind`` marker for combined exports so downstream can filter."""
    return [{"_kind": kind, **r} for r in rows]
