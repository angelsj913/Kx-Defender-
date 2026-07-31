"""SQLite persistence for module runs."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from kx_defender.result import ModuleResult


class RunStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        home = Path(os.environ.get("KX_HOME") or (Path.home() / ".kx-defender"))
        default = Path(
            os.environ.get("KX_RUN_DB")
            or os.environ.get("KX_OPERATOR_DB")
            or (home / "operator.db")
        )
        self.db_path = Path(db_path) if db_path else default
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    module TEXT NOT NULL,
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    authorized_scope TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, result: ModuleResult) -> None:
        payload = json.dumps(result.to_dict(), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs
                (run_id, module, status, mode, authorized_scope, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    result.module,
                    result.status,
                    result.mode,
                    result.authorized_scope,
                    payload,
                    result.started_at,
                ),
            )
            conn.commit()

    def get(self, run_id: str) -> ModuleResult | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if not row:
            return None
        return ModuleResult.from_dict(json.loads(row["payload"]))

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, module, status, mode, authorized_scope, created_at
                FROM runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
