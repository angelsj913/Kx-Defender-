from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from kx_defender.kxsig_workbench import RuleWorkbench


def write_rules(path: Path, rules: list[dict]) -> None:
    path.write_text(json.dumps({"rules": rules}), encoding="utf-8")


def rule(rule_id: str = "CUSTOM-001", pattern: str = "KX_TEST_MARKER") -> dict:
    return {
        "id": rule_id,
        "name": "custom_marker",
        "severity": "high",
        "category": "lab-marker",
        "patterns": [pattern],
    }


def test_validate_test_and_rule_state(tmp_path: Path):
    source = tmp_path / "custom.json"
    sample = tmp_path / "sample.txt"
    write_rules(source, [rule()])
    sample.write_text("prefix KX_TEST_MARKER suffix", encoding="utf-8")
    workbench = RuleWorkbench(tmp_path / "home")

    validated = workbench.validate_file(source)
    assert validated["valid"] is True
    tested = workbench.test_file(source, sample)
    assert tested["matched"] is True
    assert tested["hits"][0]["rule_id"] == "CUSTOM-001"

    disabled = workbench.disable("CUSTOM-001", reason="noisy")
    assert disabled["enabled"] is False
    assert workbench.show("CUSTOM-001", extra_files=[source])["enabled"] is False
    assert workbench.enable("CUSTOM-001")["enabled"] is True


def test_rejects_duplicates_dangerous_regex_and_quarantines(tmp_path: Path):
    duplicate = tmp_path / "duplicate.json"
    write_rules(duplicate, [rule(), rule()])
    workbench = RuleWorkbench(tmp_path / "home")
    result = workbench.validate_file(duplicate)
    assert result["valid"] is False
    assert any("duplicate rule id" in error for error in result["errors"])

    dangerous = tmp_path / "dangerous.json"
    write_rules(dangerous, [rule(pattern=r"(a+)+$")])
    result = workbench.validate_file(dangerous)
    assert result["valid"] is False
    assert any("nested quantifier" in error for error in result["errors"])

    quarantined = workbench.quarantine(dangerous)
    assert Path(quarantined["destination"]).is_file()
    assert dangerous.is_file(), "quarantine copies external input; it must not delete the source"


def test_kxsig_cli_contract(tmp_path: Path):
    source = tmp_path / "custom.json"
    sample = tmp_path / "sample.txt"
    write_rules(source, [rule()])
    sample.write_text("KX_TEST_MARKER", encoding="utf-8")
    env = {**os.environ, "KX_HOME": str(tmp_path / "home")}
    code = "from kx_defender.kx_cli import main; main()"

    validated = subprocess.run(
        [sys.executable, "-c", code, "sig", "validate", str(source)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(validated.stdout)["valid"] is True
    imported = subprocess.run(
        [sys.executable, "-c", code, "sig", "import", str(source)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(imported.stdout)["imported"] is True
    tested = subprocess.run(
        [sys.executable, "-c", code, "sig", "test", str(source), "--sample", str(sample)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(tested.stdout)["matched"] is True
    disabled = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            "sig",
            "disable",
            "CUSTOM-001",
            "--reason",
            "noisy",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(disabled.stdout)["enabled"] is False
