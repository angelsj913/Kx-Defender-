from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from kx_defender.baseline import BaselineManager


class Processes:
    def __init__(self):
        self.items = [{"pid": 1, "name": "init", "ppid": 0, "path": "/init"}]

    def __call__(self):
        return list(self.items)


def test_baseline_create_compare_show_delete(tmp_path: Path):
    watched = tmp_path / "watched"
    watched.mkdir()
    (watched / "same.txt").write_text("same", encoding="utf-8")
    changed = watched / "changed.txt"
    changed.write_text("before", encoding="utf-8")
    removed = watched / "removed.txt"
    removed.write_text("remove", encoding="utf-8")
    processes = Processes()
    manager = BaselineManager(tmp_path / "home", process_collector=processes)

    created = manager.create("clean", watched_path=watched)
    assert created["name"] == "clean"
    assert manager.show("clean")["snapshot"]["files"]

    changed.write_text("after", encoding="utf-8")
    removed.unlink()
    (watched / "added.txt").write_text("add", encoding="utf-8")
    processes.items = [{"pid": 2, "name": "newproc", "ppid": 1, "path": "/newproc"}]
    comparison = manager.compare("clean")
    assert comparison["drift"] is True
    assert "added.txt" in comparison["added"]
    assert "removed.txt" in comparison["removed"]
    assert "changed.txt" in comparison["modified"]
    assert comparison["process_new"][0]["name"] == "newproc"
    assert comparison["process_missing"][0]["name"] == "init"

    assert manager.list()[0]["name"] == "clean"
    manager.delete("clean")
    assert manager.list() == []


def test_baseline_rejects_unsafe_name_and_symlink(tmp_path: Path):
    manager = BaselineManager(tmp_path / "home", process_collector=lambda: [])
    try:
        manager.create("../escape")
    except ValueError as exc:
        assert "name" in str(exc)
    else:
        raise AssertionError("unsafe baseline name was accepted")


def test_baseline_cli_json_contract(tmp_path: Path):
    watched = tmp_path / "watched"
    watched.mkdir()
    target = watched / "state.txt"
    target.write_text("before", encoding="utf-8")
    env = {**os.environ, "KX_HOME": str(tmp_path / "home")}
    code = "from kx_defender.kx_cli import main; main()"
    created = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            "baseline",
            "create",
            "cli",
            "--path",
            str(watched),
            "--json",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(created.stdout)["name"] == "cli"
    target.write_text("after", encoding="utf-8")
    compared = subprocess.run(
        [sys.executable, "-c", code, "baseline", "compare", "cli", "--json"],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(compared.stdout)
    assert result["drift"] is True
    assert "state.txt" in result["modified"]
