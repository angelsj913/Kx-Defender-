from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from kx_defender.alert_store import AlertStore
from kx_defender.kxsig_workbench import RuleWorkbench
from kx_defender.operations import build_snapshot, render_snapshot
from kx_defender.result import ModuleResult
from kx_defender.store import RunStore


def test_default_run_store_follows_persistent_home(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("KX_HOME", str(tmp_path))
    store = RunStore()
    assert store.db_path == tmp_path / "operator.db"


def test_dashboard_sections_aggregate_local_state(tmp_path: Path) -> None:
    alerts = AlertStore(tmp_path / "operator.db")
    runs = RunStore(tmp_path / "runs.db")
    rules = RuleWorkbench(tmp_path / "home")
    now = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)

    alerts.ingest(
        {
            "ts": "2026-07-31T11:30:00+00:00",
            "severity": "high",
            "module": "test",
            "title": "Recent alert",
            "evidence": {"source": "unit"},
        }
    )
    old = alerts.ingest(
        {
            "ts": "2026-07-29T11:30:00+00:00",
            "severity": "critical",
            "module": "test",
            "title": "Old alert",
            "evidence": {"source": "unit"},
        }
    )
    alerts.transition(old["alert_id"], "resolved")
    alerts.create_case("Investigate recent alert", severity="high")
    runs.save(
        ModuleResult(
            module="sentry",
            status="ok",
            mode="simulate",
            authorized_scope="lab",
        ).finish("ok")
    )
    rules.disable("KXSIG-TEST", "unit test")

    overview = build_snapshot(
        "overview",
        alert_store=alerts,
        run_store=runs,
        rule_workbench=rules,
        daemon_provider=lambda: {"running": False, "reason": "test"},
        now=now,
    )
    assert overview["section"] == "overview"
    assert overview["alerts_24h"]["total"] == 1
    assert overview["alerts_24h"]["by_severity"]["high"] == 1
    assert overview["open_cases"] == 1
    assert overview["latest_run"]["module"] == "sentry"
    assert overview["daemon"]["running"] is False

    alerts_view = build_snapshot("alerts", alert_store=alerts)
    assert len(alerts_view["items"]) == 2
    assert alerts_view["by_status"] == {
        "new": 1,
        "acknowledged": 0,
        "resolved": 1,
    }

    rules_view = build_snapshot("rules", rule_workbench=rules)
    assert rules_view["disabled"] == 1
    assert rules_view["quarantined"] == 0
    assert "KXSIG-TEST" not in render_snapshot(rules_view)


def test_dashboard_rejects_unknown_section() -> None:
    try:
        build_snapshot("secrets")
    except ValueError as exc:
        assert "unknown dashboard section" in str(exc)
    else:
        raise AssertionError("unknown section was accepted")
