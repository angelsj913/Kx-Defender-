from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

import pytest

from kx_defender.alert_store import AlertStore
from kx_defender.evidence import (
    EvidenceError,
    export_bundle,
    import_bundle,
    inspect_bundle,
    verify_bundle,
)


def build_case(tmp_path: Path) -> tuple[AlertStore, str]:
    store = AlertStore(tmp_path / "operator.db")
    alert = store.ingest(
        {
            "module": "sentry",
            "title": "Credential signal",
            "severity": "high",
            "evidence": {
                "token": "secret-token-value",
                "username": "angel",
                "source_ip": "192.168.1.20",
                "path": r"C:\Users\angel\private.txt",
            },
        }
    )
    case = store.create_case("Credential investigation", from_alert=alert["alert_id"])
    store.add_case_note(case["case_id"], "admin", "Authorization: Bearer abc123")
    return store, case["case_id"]


def test_case_bundle_redacts_hashes_and_imports_read_only(tmp_path: Path):
    store, case_id = build_case(tmp_path)
    bundle = tmp_path / "incident.kxev"
    result = export_bundle(
        "case",
        case_id,
        bundle,
        redact="strict",
        alert_store=store,
    )

    assert result["files"] >= 3
    verified = verify_bundle(bundle)
    assert verified["valid"] is True
    inspected = inspect_bundle(bundle)
    assert inspected["manifest"]["source"] == {"type": "case", "id": case_id}
    assert inspected["manifest"]["redaction"]["profile"] == "strict"

    with zipfile.ZipFile(bundle) as archive:
        combined = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist()
        )
    assert "secret-token-value" not in combined
    assert "192.168.1.20" not in combined
    assert r"C:\Users\angel" not in combined
    assert "<redacted>" in combined

    imported = import_bundle(bundle, tmp_path / "imports")
    assert imported["read_only"] is True
    assert (Path(imported["path"]) / "manifest.json").is_file()


def test_verify_rejects_duplicate_and_traversal_entries(tmp_path: Path):
    store, case_id = build_case(tmp_path)
    bundle = tmp_path / "good.kxev"
    export_bundle("case", case_id, bundle, alert_store=store)

    duplicate = tmp_path / "duplicate.kxev"
    duplicate.write_bytes(bundle.read_bytes())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(duplicate, "a") as archive:
            archive.writestr("manifest.json", "{}")
    assert verify_bundle(duplicate)["valid"] is False

    traversal = tmp_path / "traversal.kxev"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("../escape.txt", "bad")
        archive.writestr("manifest.json", json.dumps({"bundle_version": 1}))
        archive.writestr("hashes.sha256", "")
    with pytest.raises(EvidenceError, match="unsafe"):
        import_bundle(traversal, tmp_path / "imports")


def test_evidence_cli_json_contract(tmp_path: Path):
    _, case_id = build_case(tmp_path)
    bundle = tmp_path / "cli.kxev"
    env = {**os.environ, "KX_HOME": str(tmp_path)}
    code = "from kx_defender.kx_cli import main; main()"
    exported = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            "evidence",
            "export",
            "--case",
            case_id,
            "--to",
            str(bundle),
            "--redact",
            "standard",
            "--json",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(exported.stdout)["path"] == str(bundle.resolve())
    verified = subprocess.run(
        [sys.executable, "-c", code, "evidence", "verify", str(bundle), "--json"],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(verified.stdout)["valid"] is True
