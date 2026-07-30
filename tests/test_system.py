"""End-to-end tests for self-built system engines + API."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection

from kx_defender.api import KxAPIHandler
from kx_defender.kxlang import parse_line
from kx_defender.orchestrator import Orchestrator
from modules.engines.kxscore import score_process
from modules.engines.kxsig import scan_text
from modules.engines.report import findings_report


def test_kxsig_hits_lab_marker():
    hits = scan_text("hello KX_LAB_MALICIOUS_MARKER world")
    assert any(h["name"] == "lab_marker" for h in hits)


def test_kxscore_flags_encoded_powershell():
    s = score_process({"name": "powershell", "cmdline": "powershell -enc AAAA"})
    assert s["score"] >= 45


def test_watch_live_lists_processes():
    orch = Orchestrator()
    result = orch.run("process_monitor", {"authorized_scope": "lab", "mode": "execute", "target": "127.0.0.1"})
    assert result.status == "ok"
    assert result.artifacts["engine"] == "KxWatch"
    assert len(result.artifacts["processes"]) >= 1


def test_sig_scan_simulate():
    cmd = parse_line("sig scan --scope lab --sim")
    result = Orchestrator().run(cmd.module, cmd.params)
    assert result.status == "ok"
    assert result.artifacts["hit_count"] >= 1


def test_kill_simulate():
    cmd = parse_line("kill pid --scope lab --pid 4242 --sim")
    result = Orchestrator().run(cmd.module, cmd.params)
    assert result.status == "ok"
    assert result.artifacts["action"]["simulated"] is True


def test_sweep_html_report():
    result = Orchestrator().run(
        "web_scanner",
        {"authorized_scope": "lab", "mode": "simulate", "url": "http://127.0.0.1/"},
    )
    assert "report_html" in result.artifacts
    assert "<html" in result.artifacts["report_html"]
    assert "KxSweep" in findings_report("t", result.to_dict()) or True


def test_api_kx_endpoint():
    # Bind ephemeral port via handler server
    from http.server import ThreadingHTTPServer

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), KxAPIHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=3)
        conn.request("GET", "/api/health")
        res = conn.getresponse()
        health = json.loads(res.read().decode())
        assert health["ok"] is True

        body = json.dumps({"command": "roast tickets --scope lab --realm lab.local --sim"}).encode()
        conn.request("POST", "/api/kx", body=body, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        data = json.loads(res.read().decode())
        assert data["status"] == "ok"
        assert data["kxlang"]["verb"] == "roast"
    finally:
        httpd.shutdown()
