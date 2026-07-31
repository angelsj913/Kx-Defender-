from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from kx_defender.alert_store import AlertStore
from kx_defender.alerts import emit_alert


def sample(ts: str = "2026-07-31T00:00:00+00:00") -> dict:
    return {
        "ts": ts,
        "severity": "high",
        "module": "sentry",
        "title": "Suspicious process",
        "evidence": {"pid": 42, "signals": ["process"]},
    }


def test_alert_lifecycle_deduplicates_and_audits(tmp_path: Path):
    store = AlertStore(tmp_path / "operator.db")
    first = store.ingest(sample())
    second = store.ingest(sample("2026-07-31T00:05:00+00:00"))

    assert first["alert_id"] == second["alert_id"]
    alert = store.get_alert(first["alert_id"])
    assert alert["count"] == 2
    assert alert["status"] == "new"
    assert alert["first_seen"] == "2026-07-31T00:00:00+00:00"
    assert alert["last_seen"] == "2026-07-31T00:05:00+00:00"

    acknowledged = store.transition(
        first["alert_id"], "acknowledged", actor="admin", note="investigating"
    )
    assert acknowledged["status"] == "acknowledged"
    resolved = store.transition(
        first["alert_id"], "resolved", actor="admin", note="benign"
    )
    assert resolved["status"] == "resolved"
    reopened = store.transition(first["alert_id"], "new", actor="admin", note="reopened")
    assert reopened["status"] == "new"

    shown = store.get_alert(first["alert_id"], include_events=True)
    assert [event["action"] for event in shown["events"]] == [
        "created",
        "deduplicated",
        "acknowledged",
        "resolved",
        "reopened",
    ]
    assert store.list_alerts(status="new", severity="high")[0]["alert_id"] == first["alert_id"]


def test_case_workflow_and_idempotent_jsonl_migration(tmp_path: Path):
    store = AlertStore(tmp_path / "operator.db")
    alert = store.ingest(sample())
    case = store.create_case("Process investigation", from_alert=alert["alert_id"])
    store.add_case_alert(case["case_id"], alert["alert_id"])
    store.add_case_note(case["case_id"], "admin", "Collected process tree")
    closed = store.close_case(case["case_id"], "contained")

    assert closed["status"] == "closed"
    shown = store.get_case(case["case_id"])
    assert shown["resolution"] == "contained"
    assert [item["alert_id"] for item in shown["alerts"]] == [alert["alert_id"]]
    assert shown["notes"][0]["body"] == "Collected process tree"

    legacy = tmp_path / "alerts.jsonl"
    legacy.write_text(json.dumps(sample("2026-07-30T00:00:00+00:00")) + "\n", encoding="utf-8")
    first = store.migrate_jsonl(legacy)
    second = store.migrate_jsonl(legacy)
    assert first == {"imported": 1, "skipped": 0, "invalid": 0}
    assert second == {"imported": 0, "skipped": 1, "invalid": 0}


def test_emit_alert_indexes_compatibility_log(tmp_path: Path):
    log = tmp_path / "alerts.jsonl"
    emitted = emit_alert(
        "sentry",
        "Suspicious process",
        severity="high",
        evidence={"pid": 42},
        also_stderr=False,
        path=log,
    )
    assert emitted["alert_id"].startswith("ALT-")
    assert AlertStore(tmp_path / "operator.db").get_alert(emitted["alert_id"])["count"] == 1
    assert json.loads(log.read_text(encoding="utf-8"))["alert_id"] == emitted["alert_id"]


def test_cli_alert_and_case_json_contract(tmp_path: Path):
    env = {**os.environ, "KX_HOME": str(tmp_path), "NO_COLOR": "1"}
    code = "from kx_defender.kx_cli import main; main()"

    created = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from kx_defender.alerts import emit_alert;"
                "print(emit_alert('sentry','CLI alert','high',"
                "{'pid':7},also_stderr=False)['alert_id'])"
            ),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    alert_id = created.stdout.strip()

    listed = subprocess.run(
        [sys.executable, "-c", code, "alert", "list", "--status", "new", "--json"],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(listed.stdout)["alerts"][0]["alert_id"] == alert_id

    acknowledged = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            "alert",
            "ack",
            alert_id,
            "--note",
            "investigating",
            "--json",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(acknowledged.stdout)["status"] == "acknowledged"

    case = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            "case",
            "create",
            "--from-alert",
            alert_id,
            "--title",
            "CLI investigation",
            "--json",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(case.stdout)["title"] == "CLI investigation"
