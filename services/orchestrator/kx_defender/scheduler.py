"""Daemon-friendly daily playbook schedules stored in the Kx home."""

from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from kx_defender.playbook import PlaybookError, PlaybookRunner


class ScheduleStore:
    def __init__(self, home: Path | str | None = None):
        self.home = Path(
            home or os.environ.get("KX_HOME") or (Path.home() / ".kx-defender")
        ).expanduser().resolve()
        self.file = self.home / "schedules.json"
        self.playbook_dir = self.home / "playbooks"

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.file.read_text(encoding="utf-8"))
            if value.get("version") == 1 and isinstance(value.get("schedules"), dict):
                return value
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
        return {"version": 1, "schedules": {}}

    def _save(self, value: dict[str, Any]) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        temp = self.file.with_name(f".{self.file.name}.{uuid.uuid4().hex}.tmp")
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, self.file)

    @staticmethod
    def _name(name: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", str(name or "")):
            raise PlaybookError("schedule name must use letters, numbers, dot, dash, or underscore")
        return str(name)

    @staticmethod
    def _daily(value: str) -> str:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(value or "")):
            raise PlaybookError("daily time must use 24-hour HH:MM")
        return str(value)

    def add(self, name: str, playbook: Path | str, daily: str) -> dict[str, Any]:
        key = self._name(name)
        when = self._daily(daily)
        source = Path(playbook).expanduser().resolve()
        runner = PlaybookRunner(self.home)
        plan = runner.validate(source)
        if not plan["valid"]:
            raise PlaybookError("; ".join(plan["errors"]))
        if any(step["live"] for step in plan["steps"]):
            raise PlaybookError("live playbooks cannot be scheduled")
        state = self._load()
        if key in state["schedules"]:
            raise PlaybookError(f"schedule already exists: {key}")
        self.playbook_dir.mkdir(parents=True, exist_ok=True)
        destination = self.playbook_dir / f"{key}.json"
        temp = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        shutil.copyfile(source, temp)
        os.replace(temp, destination)
        item = {
            "name": key,
            "playbook": str(destination),
            "daily": when,
            "enabled": True,
            "created_at": datetime.now().astimezone().isoformat(),
            "last_run_at": None,
            "last_status": None,
        }
        state["schedules"][key] = item
        self._save(state)
        return item

    def list(self) -> list[dict[str, Any]]:
        return [
            dict(item)
            for _, item in sorted(self._load()["schedules"].items())
        ]

    def disable(self, name: str) -> dict[str, Any]:
        return self._set_enabled(name, False)

    def enable(self, name: str) -> dict[str, Any]:
        return self._set_enabled(name, True)

    def _set_enabled(self, name: str, enabled: bool) -> dict[str, Any]:
        state = self._load()
        if name not in state["schedules"]:
            raise PlaybookError(f"schedule not found: {name}")
        state["schedules"][name]["enabled"] = enabled
        self._save(state)
        return dict(state["schedules"][name])

    def run_due(
        self,
        *,
        now: datetime | None = None,
        runner: PlaybookRunner | None = None,
    ) -> list[dict[str, Any]]:
        current = now or datetime.now().astimezone()
        day = current.date().isoformat()
        clock = current.strftime("%H:%M")
        state = self._load()
        outcomes: list[dict[str, Any]] = []
        executor = runner or PlaybookRunner(self.home)
        for name, item in state["schedules"].items():
            last = str(item.get("last_run_at") or "")
            if not item.get("enabled") or clock < item["daily"] or last.startswith(day):
                continue
            try:
                result = executor.run(item["playbook"])
                status = str(result.get("status") or "unknown")
                outcome = {"name": name, "status": status, "run_id": result.get("run_id")}
            except Exception as exc:
                status = "failed"
                outcome = {"name": name, "status": status, "error": str(exc)}
            item["last_run_at"] = current.isoformat()
            item["last_status"] = status
            outcomes.append(outcome)
        if outcomes:
            self._save(state)
        return outcomes
