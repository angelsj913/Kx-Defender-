"""Validated sequential KxLang playbooks with local run journals."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from kx_defender.kxlang import KxLangError, parse_argv

MAX_STEPS = 20
MAX_OUTPUT = 1024 * 1024
META_COMMANDS = {
    "alert", "baseline", "case", "daemon", "doctor", "evidence", "favorite",
    "history", "playbook", "schedule", "security", "setup", "update", "upgrade",
}
_SECRET = re.compile(
    r"(?i)\b(password|passwd|token|secret|cookie|authorization|api[_-]?key)"
    r"(\s*[:=]\s*)\S+"
)


class PlaybookError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_text(value: str) -> str:
    return _SECRET.sub(r"\1\2<redacted>", str(value))


def _redact_args(args: list[str]) -> list[str]:
    result = list(args)
    for index, value in enumerate(result):
        if re.fullmatch(
            r"(?i)--?(password|passwd|token|secret|cookie|authorization|api[_-]?key)",
            value,
        ) and index + 1 < len(result):
            result[index + 1] = "<redacted>"
        else:
            result[index] = _redact_text(value)
    return result


class PlaybookRunner:
    def __init__(
        self,
        home: Path | str | None = None,
        executor: Callable[[list[str], float], dict[str, Any]] | None = None,
    ):
        self.home = Path(
            home or os.environ.get("KX_HOME") or (Path.home() / ".kx-defender")
        ).expanduser().resolve()
        self.run_dir = self.home / "playbook-runs"
        self.lock_file = self.home / "playbook.lock"
        self.executor = executor or self._execute

    @staticmethod
    def _load(path: Path | str) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise PlaybookError(f"playbook not found: {source}")
        if source.stat().st_size > 1024 * 1024:
            raise PlaybookError("playbook exceeds 1 MiB")
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PlaybookError(f"invalid playbook JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise PlaybookError("playbook root must be an object")
        return value

    def validate(self, path: Path | str) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        errors: list[str] = []
        commands: list[dict[str, Any]] = []
        try:
            document = self._load(source)
        except PlaybookError as exc:
            return {"valid": False, "path": str(source), "errors": [str(exc)], "steps": []}
        unknown = set(document) - {"name", "version", "allow_live", "steps", "on_error"}
        if unknown:
            errors.append(f"unknown playbook fields: {', '.join(sorted(unknown))}")
        if document.get("version") != 1:
            errors.append("playbook version must be 1")
        if not str(document.get("name") or "").strip():
            errors.append("playbook name is required")
        on_error = document.get("on_error", "stop")
        if on_error not in {"stop", "continue"}:
            errors.append("on_error must be stop or continue")
        steps = document.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append("steps must be a non-empty list")
            steps = []
        if len(steps) > MAX_STEPS:
            errors.append(f"playbook exceeds {MAX_STEPS} steps")
        live_found = False
        for index, step in enumerate(steps[:MAX_STEPS]):
            if not isinstance(step, dict):
                errors.append(f"step {index + 1}: must be an object")
                continue
            extra = set(step) - {"run", "timeout"}
            if extra:
                errors.append(f"step {index + 1}: unknown fields {', '.join(sorted(extra))}")
            args = step.get("run")
            if (
                not isinstance(args, list)
                or not args
                or len(args) > 50
                or not all(isinstance(item, str) and item for item in args)
            ):
                errors.append(f"step {index + 1}: run must be a non-empty string array")
                continue
            if args[0].lower() in META_COMMANDS:
                errors.append(f"step {index + 1}: meta command {args[0]!r} is not allowed")
                continue
            timeout = step.get("timeout", 60)
            if not isinstance(timeout, (int, float)) or not 1 <= float(timeout) <= 300:
                errors.append(f"step {index + 1}: timeout must be between 1 and 300 seconds")
                continue
            try:
                parsed = parse_argv(args)
                is_live = parsed.params.get("mode") == "execute"
                live_found = live_found or is_live
                commands.append(
                    {
                        "index": index + 1,
                        "run": args,
                        "timeout": float(timeout),
                        "module": parsed.module,
                        "live": is_live,
                    }
                )
            except KxLangError as exc:
                errors.append(f"step {index + 1}: {exc}")
        if live_found and document.get("allow_live") is not True:
            errors.append("playbook contains --live but allow_live is not true")
        return {
            "valid": not errors,
            "path": str(source),
            "name": document.get("name"),
            "on_error": on_error,
            "allow_live": document.get("allow_live") is True,
            "steps": commands,
            "errors": errors,
        }

    @staticmethod
    def _execute(args: list[str], timeout: float) -> dict[str, Any]:
        code = "from kx_defender.kx_cli import main; main()"
        try:
            completed = subprocess.run(
                [sys.executable, "-c", code, *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            return {
                "status": completed.returncode,
                "stdout": completed.stdout[:MAX_OUTPUT],
                "stderr": completed.stderr[:MAX_OUTPUT],
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "status": 124,
                "stdout": str(exc.stdout or "")[:MAX_OUTPUT],
                "stderr": "step timed out",
            }

    def _lock(self) -> int:
        self.home.mkdir(parents=True, exist_ok=True)
        if self.lock_file.exists():
            try:
                if time.time() - self.lock_file.stat().st_mtime > 7200:
                    self.lock_file.unlink()
            except OSError:
                pass
        try:
            descriptor = os.open(
                self.lock_file,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as exc:
            raise PlaybookError("another playbook is already running") from exc
        os.write(descriptor, f"{os.getpid()}\n".encode())
        return descriptor

    def _write_journal(self, journal: dict[str, Any]) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        target = self.run_dir / f"{journal['run_id']}.json"
        temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        temp.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, target)
        return target

    def run(
        self,
        path: Path | str,
        *,
        dry_run: bool = False,
        confirm_live: bool = False,
    ) -> dict[str, Any]:
        plan = self.validate(path)
        if not plan["valid"]:
            raise PlaybookError("; ".join(plan["errors"]))
        if plan["allow_live"] and any(step["live"] for step in plan["steps"]) and not confirm_live:
            raise PlaybookError("live playbook requires --confirm-live")
        if dry_run:
            return {
                "status": "dry-run",
                "name": plan["name"],
                "steps": [
                    {**step, "run": _redact_args(step["run"])} for step in plan["steps"]
                ],
            }

        descriptor = self._lock()
        run_id = f"PLAY-{uuid.uuid4().hex.upper()}"
        journal: dict[str, Any] = {
            "version": 1,
            "run_id": run_id,
            "name": plan["name"],
            "playbook": plan["path"],
            "started_at": _utc_now(),
            "status": "running",
            "steps": [],
        }
        try:
            for step in plan["steps"]:
                started = _utc_now()
                outcome = self.executor(step["run"], step["timeout"])
                status = int(outcome.get("status", 1))
                journal["steps"].append(
                    {
                        "index": step["index"],
                        "run": _redact_args(step["run"]),
                        "module": step["module"],
                        "started_at": started,
                        "finished_at": _utc_now(),
                        "exit_code": status,
                        "stdout": _redact_text(str(outcome.get("stdout") or ""))[:MAX_OUTPUT],
                        "stderr": _redact_text(str(outcome.get("stderr") or ""))[:MAX_OUTPUT],
                    }
                )
                if status != 0 and plan["on_error"] == "stop":
                    break
            journal["status"] = (
                "ok" if all(step["exit_code"] == 0 for step in journal["steps"]) else "failed"
            )
            journal["finished_at"] = _utc_now()
            target = self._write_journal(journal)
            return {**journal, "journal": str(target)}
        finally:
            os.close(descriptor)
            try:
                self.lock_file.unlink()
            except OSError:
                pass
