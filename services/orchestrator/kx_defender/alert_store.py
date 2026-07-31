"""SQLite-backed alert lifecycle and local incident case storage."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}
VALID_ALERT_STATUSES = {"new", "acknowledged", "resolved"}
_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_db() -> Path:
    home = Path(os.environ.get("KX_HOME") or (Path.home() / ".kx-defender"))
    return Path(os.environ.get("KX_OPERATOR_DB") or (home / "operator.db"))


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(record: dict[str, Any]) -> str:
    stable = {
        "module": str(record.get("module") or ""),
        "title": str(record.get("title") or ""),
        "evidence": record.get("evidence") or {},
    }
    return hashlib.sha256(_canonical(stable).encode("utf-8")).hexdigest()


class AlertStore:
    """Small connection-per-operation store suitable for CLI and daemon use."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or _default_db()).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version(
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS alerts(
                    alert_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    ts TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    module TEXT NOT NULL,
                    title TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assignee TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    count INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS alert_events(
                    event_id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL REFERENCES alerts(alert_id) ON DELETE CASCADE,
                    ts TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    note TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cases(
                    case_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolution TEXT
                );
                CREATE TABLE IF NOT EXISTS case_alerts(
                    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
                    alert_id TEXT NOT NULL REFERENCES alerts(alert_id) ON DELETE RESTRICT,
                    PRIMARY KEY(case_id, alert_id)
                );
                CREATE TABLE IF NOT EXISTS case_notes(
                    note_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
                    ts TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS legacy_alert_imports(
                    line_hash TEXT PRIMARY KEY,
                    imported_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS alerts_status_severity
                    ON alerts(status, severity, last_seen DESC);
                CREATE INDEX IF NOT EXISTS alert_events_alert
                    ON alert_events(alert_id, ts);
                """
            )
            row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            elif int(row["version"]) != SCHEMA_VERSION:
                raise RuntimeError(
                    f"unsupported operator database schema {row['version']}; expected {SCHEMA_VERSION}"
                )

    @staticmethod
    def _event(
        conn: sqlite3.Connection,
        alert_id: str,
        action: str,
        actor: str = "system",
        note: str = "",
    ) -> None:
        conn.execute(
            """
            INSERT INTO alert_events(event_id, alert_id, ts, actor, action, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"EVT-{uuid.uuid4().hex}", alert_id, _utc_now(), actor, action, note),
        )

    def _ingest(self, conn: sqlite3.Connection, record: dict[str, Any]) -> dict[str, Any]:
        fingerprint = _fingerprint(record)
        alert_id = f"ALT-{fingerprint[:12].upper()}"
        severity = str(record.get("severity") or "info").lower()
        if severity not in VALID_SEVERITIES:
            severity = "info"
        ts = str(record.get("ts") or _utc_now())
        existing = conn.execute(
            "SELECT alert_id FROM alerts WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE alerts
                SET ts = MAX(ts, ?), severity = ?,
                    first_seen = MIN(first_seen, ?), last_seen = MAX(last_seen, ?),
                    count = count + 1
                WHERE fingerprint = ?
                """,
                (ts, severity, ts, ts, fingerprint),
            )
            self._event(conn, existing["alert_id"], "deduplicated")
            return self._get_alert(conn, existing["alert_id"])

        inserted = conn.execute(
            """
            INSERT OR IGNORE INTO alerts(
                alert_id, fingerprint, ts, severity, module, title, evidence_json,
                status, assignee, first_seen, last_seen, count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'new', NULL, ?, ?, 1)
            """,
            (
                alert_id,
                fingerprint,
                ts,
                severity,
                str(record.get("module") or "unknown"),
                str(record.get("title") or ""),
                _canonical(record.get("evidence") or {}),
                ts,
                ts,
            ),
        )
        if inserted.rowcount == 0:
            conn.execute(
                """
                UPDATE alerts
                SET ts = MAX(ts, ?), severity = ?,
                    first_seen = MIN(first_seen, ?), last_seen = MAX(last_seen, ?),
                    count = count + 1
                WHERE fingerprint = ?
                """,
                (ts, severity, ts, ts, fingerprint),
            )
            row = conn.execute(
                "SELECT alert_id FROM alerts WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
            self._event(conn, row["alert_id"], "deduplicated")
            return self._get_alert(conn, row["alert_id"])
        self._event(conn, alert_id, "created")
        return self._get_alert(conn, alert_id)

    def ingest(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            return self._ingest(conn, record)

    @staticmethod
    def _alert_dict(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        value["evidence"] = json.loads(value.pop("evidence_json"))
        value.pop("fingerprint", None)
        return value

    def _get_alert(self, conn: sqlite3.Connection, alert_id: str) -> dict[str, Any]:
        row = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
        if row is None:
            raise KeyError(f"alert not found: {alert_id}")
        return self._alert_dict(row)

    def get_alert(self, alert_id: str, include_events: bool = False) -> dict[str, Any]:
        with self._connect() as conn:
            alert = self._get_alert(conn, alert_id)
            if include_events:
                alert["events"] = [
                    dict(row)
                    for row in conn.execute(
                        """
                        SELECT event_id, ts, actor, action, note
                        FROM alert_events WHERE alert_id = ? ORDER BY rowid
                        """,
                        (alert_id,),
                    )
                ]
            return alert

    def list_alerts(
        self,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if status:
            if status not in VALID_ALERT_STATUSES:
                raise ValueError(f"invalid alert status: {status}")
            clauses.append("status = ?")
            values.append(status)
        if severity:
            if severity not in VALID_SEVERITIES:
                raise ValueError(f"invalid severity: {severity}")
            clauses.append("severity = ?")
            values.append(severity)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(max(1, min(int(limit), 500)))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM alerts {where} ORDER BY last_seen DESC LIMIT ?", values
            ).fetchall()
            return [self._alert_dict(row) for row in rows]

    def transition(
        self,
        alert_id: str,
        status: str,
        actor: str = "admin",
        note: str = "",
    ) -> dict[str, Any]:
        if status not in VALID_ALERT_STATUSES:
            raise ValueError(f"invalid alert status: {status}")
        with self._connect() as conn:
            current = self._get_alert(conn, alert_id)
            allowed = {
                "new": {"acknowledged", "resolved"},
                "acknowledged": {"resolved"},
                "resolved": {"new"},
            }
            if status not in allowed[current["status"]]:
                raise ValueError(f"cannot change alert from {current['status']} to {status}")
            action = "reopened" if current["status"] == "resolved" and status == "new" else status
            if status == "acknowledged":
                conn.execute(
                    "UPDATE alerts SET status = ?, assignee = ? WHERE alert_id = ?",
                    (status, actor, alert_id),
                )
            elif status == "new":
                conn.execute(
                    "UPDATE alerts SET status = ?, assignee = NULL WHERE alert_id = ?",
                    (status, alert_id),
                )
            else:
                conn.execute(
                    "UPDATE alerts SET status = ? WHERE alert_id = ?", (status, alert_id)
                )
            self._event(conn, alert_id, action, actor=actor, note=note)
            return self._get_alert(conn, alert_id)

    def create_case(
        self,
        title: str,
        from_alert: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        if not str(title).strip():
            raise ValueError("case title is required")
        now = _utc_now()
        case_id = f"CASE-{uuid.uuid4().hex[:12].upper()}"
        with self._connect() as conn:
            if from_alert:
                alert = self._get_alert(conn, from_alert)
                severity = severity or alert["severity"]
            severity = str(severity or "medium").lower()
            if severity not in VALID_SEVERITIES:
                raise ValueError(f"invalid severity: {severity}")
            conn.execute(
                """
                INSERT INTO cases(case_id, title, status, severity, created_at, updated_at, resolution)
                VALUES (?, ?, 'open', ?, ?, ?, NULL)
                """,
                (case_id, str(title).strip(), severity, now, now),
            )
            if from_alert:
                conn.execute(
                    "INSERT INTO case_alerts(case_id, alert_id) VALUES (?, ?)",
                    (case_id, from_alert),
                )
            return self._get_case(conn, case_id)

    def add_case_alert(self, case_id: str, alert_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            case = self._get_case(conn, case_id)
            if case["status"] == "closed":
                raise ValueError("cannot add an alert to a closed case")
            self._get_alert(conn, alert_id)
            conn.execute(
                "INSERT OR IGNORE INTO case_alerts(case_id, alert_id) VALUES (?, ?)",
                (case_id, alert_id),
            )
            conn.execute("UPDATE cases SET updated_at = ? WHERE case_id = ?", (_utc_now(), case_id))
            return self._get_case(conn, case_id)

    def add_case_note(self, case_id: str, actor: str, body: str) -> dict[str, Any]:
        if not str(body).strip():
            raise ValueError("case note is required")
        with self._connect() as conn:
            case = self._get_case(conn, case_id)
            if case["status"] == "closed":
                raise ValueError("cannot add a note to a closed case")
            conn.execute(
                """
                INSERT INTO case_notes(note_id, case_id, ts, actor, body)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"NOTE-{uuid.uuid4().hex}", case_id, _utc_now(), actor, str(body).strip()),
            )
            conn.execute("UPDATE cases SET updated_at = ? WHERE case_id = ?", (_utc_now(), case_id))
            return self._get_case(conn, case_id)

    def close_case(self, case_id: str, resolution: str) -> dict[str, Any]:
        if not str(resolution).strip():
            raise ValueError("case resolution is required")
        with self._connect() as conn:
            case = self._get_case(conn, case_id)
            if case["status"] == "closed":
                raise ValueError("case is already closed")
            conn.execute(
                """
                UPDATE cases SET status = 'closed', resolution = ?, updated_at = ?
                WHERE case_id = ?
                """,
                (str(resolution).strip(), _utc_now(), case_id),
            )
            return self._get_case(conn, case_id)

    def _get_case(self, conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
        row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise KeyError(f"case not found: {case_id}")
        return dict(row)

    def get_case(self, case_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            case = self._get_case(conn, case_id)
            case["alerts"] = [
                self._alert_dict(row)
                for row in conn.execute(
                    """
                    SELECT a.* FROM alerts a
                    JOIN case_alerts ca ON ca.alert_id = a.alert_id
                    WHERE ca.case_id = ? ORDER BY a.last_seen DESC
                    """,
                    (case_id,),
                )
            ]
            case["notes"] = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT note_id, ts, actor, body FROM case_notes
                    WHERE case_id = ? ORDER BY rowid
                    """,
                    (case_id,),
                )
            ]
            return case

    def list_cases(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        if status and status not in {"open", "closed"}:
            raise ValueError(f"invalid case status: {status}")
        where = "WHERE status = ?" if status else ""
        values: list[Any] = [status] if status else []
        values.append(max(1, min(int(limit), 500)))
        with self._connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    f"SELECT * FROM cases {where} ORDER BY updated_at DESC LIMIT ?", values
                )
            ]

    def migrate_jsonl(self, path: Path | str) -> dict[str, int]:
        source = Path(path)
        result = {"imported": 0, "skipped": 0, "invalid": 0}
        if not source.is_file():
            return result
        source_key = str(source.expanduser().resolve())
        with self._connect() as conn, source.open("r", encoding="utf-8", errors="replace") as stream:
            for line_number, raw in enumerate(stream, start=1):
                line = raw.strip()
                if not line:
                    continue
                identity = f"{source_key}:{line_number}:{line}"
                line_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
                if conn.execute(
                    "SELECT 1 FROM legacy_alert_imports WHERE line_hash = ?", (line_hash,)
                ).fetchone():
                    result["skipped"] += 1
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("record must be an object")
                    existing_id = str(record.get("alert_id") or "")
                    if existing_id and conn.execute(
                        "SELECT 1 FROM alerts WHERE alert_id = ?", (existing_id,)
                    ).fetchone():
                        conn.execute(
                            "INSERT INTO legacy_alert_imports(line_hash, imported_at) VALUES (?, ?)",
                            (line_hash, _utc_now()),
                        )
                        result["skipped"] += 1
                        continue
                    self._ingest(conn, record)
                except (json.JSONDecodeError, TypeError, ValueError):
                    result["invalid"] += 1
                    continue
                conn.execute(
                    "INSERT INTO legacy_alert_imports(line_hash, imported_at) VALUES (?, ?)",
                    (line_hash, _utc_now()),
                )
                result["imported"] += 1
        return result
