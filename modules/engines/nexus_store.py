"""Persistent Nexus session/listener ledger (SQLite)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class NexusStore:
    def __init__(self, db_path: Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self.db_path = db_path or (root / "data" / "nexus.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS listeners (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert_listener(self, listener_id: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO listeners(id, payload) VALUES (?, ?)",
                (listener_id, json.dumps(payload)),
            )
            conn.commit()

    def upsert_session(self, session_id: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions(id, payload) VALUES (?, ?)",
                (session_id, json.dumps(payload)),
            )
            conn.commit()

    def list_listeners(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM listeners").fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM sessions").fetchall()
        return [json.loads(r["payload"]) for r in rows]
