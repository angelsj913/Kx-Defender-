from __future__ import annotations

import json
from io import StringIO

import pytest

from kx_defender.kx_cli import main
from kx_defender.kx_cli import _format_daemon_result
from kx_defender.render import render_result_text


def test_result_text_explains_purpose_result_and_next_action() -> None:
    payload = {
        "module": "detecting-anomalous-authentication-patterns",
        "status": "ok",
        "mode": "simulate",
        "authorized_scope": "lab",
        "run_id": "12345678-aaaa",
        "findings": [
            {
                "title": "Anomalous authentication pattern",
                "severity": "medium",
                "detail": "A local simulation matched the detection threshold.",
                "evidence": {"score": 72},
            }
        ],
        "artifacts": {"recommended_actions": ["triage", "contain"]},
    }

    text = render_result_text(payload, color=False)

    assert "PURPOSE" in text
    assert "RESULT" in text
    assert "WHY THIS RAN" in text
    assert "NEXT ACTION" in text
    assert '"module"' not in text
    assert '"artifacts"' not in text


def test_daemon_status_has_human_explanation(monkeypatch) -> None:
    monkeypatch.setenv("KX_LANG", "en")
    text = _format_daemon_result("status", {"running": False, "reason": "no pid file"})

    assert "Daemon is stopped" in text
    assert "no pid file" in text
    assert not text.lstrip().startswith("{")


def test_module_json_escape_hatch(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["sentry", "--json"])

    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["kxlang"]["verb"] == "sentry"


def test_ask_accepts_documented_option_separator(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("KX_HOME", str(tmp_path))
    monkeypatch.setattr("sys.stdin", StringIO("\n"))

    with pytest.raises(SystemExit) as exc:
        main(["ask", "sentry", "detect", "--", "--scope", "lab", "--sim"])

    assert exc.value.code == 0
    assert "unknown flag '--'" not in capsys.readouterr().err
