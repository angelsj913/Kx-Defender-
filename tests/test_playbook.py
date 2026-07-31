from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from kx_defender.playbook import PlaybookError, PlaybookRunner
from kx_defender.scheduler import ScheduleStore


def write_playbook(path: Path, *, live: bool = False, on_error: str = "stop") -> None:
    path.write_text(
        json.dumps(
            {
                "name": "daily-local-check",
                "version": 1,
                "allow_live": live,
                "steps": [
                    {
                        "run": [
                            "sentry",
                            "--scope",
                            "lab",
                            "--live" if live else "--sim",
                        ],
                        "timeout": 10,
                    },
                    {"run": ["watch", "procs", "--scope", "lab", "--sim"]},
                ],
                "on_error": on_error,
            }
        ),
        encoding="utf-8",
    )


def test_validate_dry_run_execute_and_live_confirmation(tmp_path: Path):
    playbook = tmp_path / "daily.json"
    write_playbook(playbook)
    calls: list[list[str]] = []

    def executor(args: list[str], timeout: float):
        calls.append(args)
        return {"status": 0, "stdout": '{"status":"ok"}', "stderr": ""}

    runner = PlaybookRunner(tmp_path / "home", executor=executor)
    assert runner.validate(playbook)["valid"] is True
    dry = runner.run(playbook, dry_run=True)
    assert dry["status"] == "dry-run"
    assert calls == []
    result = runner.run(playbook)
    assert result["status"] == "ok"
    assert len(calls) == 2
    assert Path(result["journal"]).is_file()

    live = tmp_path / "live.json"
    write_playbook(live, live=True)
    with pytest.raises(PlaybookError, match="confirm-live"):
        runner.run(live)
    assert runner.run(live, confirm_live=True)["status"] == "ok"


def test_validation_blocks_meta_commands_and_scheduler_runs_due(tmp_path: Path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        json.dumps({"name": "bad", "version": 1, "steps": [{"run": ["update"]}]}),
        encoding="utf-8",
    )
    runner = PlaybookRunner(tmp_path / "home", executor=lambda *_: {})
    assert runner.validate(invalid)["valid"] is False

    valid = tmp_path / "daily.json"
    write_playbook(valid)
    schedules = ScheduleStore(tmp_path / "home")
    added = schedules.add("daily-check", valid, "09:00")
    assert added["enabled"] is True
    fake_runner = type(
        "Runner",
        (),
        {"run": lambda self, path: {"status": "ok", "path": str(path)}},
    )()
    outcomes = schedules.run_due(
        now=datetime(2026, 7, 31, 9, 1),
        runner=fake_runner,
    )
    assert outcomes[0]["status"] == "ok"
    assert schedules.run_due(
        now=datetime(2026, 7, 31, 9, 2),
        runner=fake_runner,
    ) == []
    assert schedules.disable("daily-check")["enabled"] is False


def test_playbook_and_schedule_cli_contract(tmp_path: Path):
    playbook = tmp_path / "daily.json"
    write_playbook(playbook)
    env = {**os.environ, "KX_HOME": str(tmp_path / "home")}
    code = "from kx_defender.kx_cli import main; main()"
    validated = subprocess.run(
        [sys.executable, "-c", code, "playbook", "validate", str(playbook)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(validated.stdout)["valid"] is True
    planned = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            "playbook",
            "run",
            str(playbook),
            "--dry-run",
            "--json",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(planned.stdout)["status"] == "dry-run"
    added = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            "schedule",
            "add",
            "daily-check",
            "--playbook",
            str(playbook),
            "--daily",
            "09:00",
            "--json",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(added.stdout)["enabled"] is True
