"""Tests for the IP rotation attack module (KxRotate)."""

from __future__ import annotations

import pytest
from kx_defender.orchestrator import Orchestrator
from modules.attack.ip_rotation import IpRotationModule, _parse_proxy_list


# ---- unit: proxy list parser -------------------------------------------

def test_parse_proxy_list_http():
    entries = _parse_proxy_list("http://10.0.0.1:8080")
    assert len(entries) == 1
    assert entries[0] == {"addr": "10.0.0.1", "port": 8080, "proto": "http"}


def test_parse_proxy_list_mixed():
    raw = "http://10.0.0.1:8080,socks5://10.0.0.2:1080"
    entries = _parse_proxy_list(raw)
    assert len(entries) == 2
    assert entries[1]["proto"] == "socks5"


def test_parse_proxy_list_no_proto():
    entries = _parse_proxy_list("10.0.0.1:3128")
    assert entries[0]["proto"] == "http"
    assert entries[0]["port"] == 3128


def test_parse_proxy_list_empty():
    assert _parse_proxy_list("") == []


def test_parse_proxy_list_bad_tokens():
    entries = _parse_proxy_list("not-valid,,http://10.0.0.1:8080")
    assert len(entries) == 1


# ---- unit: module actions (simulate mode) --------------------------------

@pytest.fixture
def mod():
    return IpRotationModule()


def _base(action: str, **extra) -> dict:
    return {"mode": "simulate", "authorized_scope": "lab", "action": action, **extra}


def test_status(mod):
    r = mod.run(_base("status"))
    assert r.status == "ok"
    assert r.artifacts["pool_size"] == 5
    assert "report_html" in r.artifacts


def test_check_ip_simulate(mod):
    r = mod.run(_base("check_ip"))
    assert r.status == "ok"
    assert r.artifacts["origin_ip"] == "203.0.113.42"
    assert any(f.title == "Current external IP (simulated)" for f in r.findings)


def test_probe_default_pool(mod):
    r = mod.run(_base("probe"))
    assert r.status == "ok"
    assert r.artifacts["proxies_probed"] == 5
    assert r.artifacts["reachable"] == 5
    assert r.artifacts["unreachable"] == 0


def test_probe_custom_proxy_list(mod):
    r = mod.run(_base("probe", proxy_list="http://10.9.9.1:8080,socks5://10.9.9.2:1080"))
    assert r.status == "ok"
    assert r.artifacts["proxies_probed"] == 2


def test_rotate_defaults(mod):
    r = mod.run(_base("rotate"))
    assert r.status == "ok"
    assert len(r.artifacts["hops"]) == 3
    assert r.artifacts["unique_effective_ips"] >= 1
    assert "report_html" in r.artifacts


def test_rotate_count_capped(mod):
    r = mod.run(_base("rotate", rotate_count="10"))
    # pool has 5 entries, so capped at 5
    assert len(r.artifacts["hops"]) == 5


def test_rotate_no_ip_check(mod):
    r = mod.run(_base("rotate", rotate_count="2", check_ip="false"))
    assert r.status == "ok"
    assert r.artifacts["origin_ip"] is None


def test_rotate_custom_proxies(mod):
    r = mod.run(_base("rotate",
                      proxy_list="http://10.0.0.9:8080,socks5://10.0.0.10:1080",
                      rotate_count="2",
                      check_ip="false"))
    assert r.status == "ok"
    assert len(r.artifacts["hops"]) == 2
    for hop in r.artifacts["hops"]:
        assert hop["success"] is True


def test_rotate_all_hops_have_ips(mod):
    r = mod.run(_base("rotate", rotate_count="3", check_ip="true"))
    for hop in r.artifacts["hops"]:
        assert hop["effective_ip"] is not None
        assert hop["effective_ip"].startswith("198.51.100.")


def test_origin_masking_check_in_findings(mod):
    r = mod.run(_base("rotate", rotate_count="2", check_ip="true"))
    titles = [f.title for f in r.findings]
    assert "Origin IP masking check" in titles


def test_unknown_action_returns_error(mod):
    r = mod.run(_base("bad_action"))
    assert r.status == "error"
    assert r.errors


# ---- probe: no proxies in execute mode without proxy_list ----------------

def test_probe_execute_no_proxy_list(mod):
    r = mod.run({"mode": "execute", "authorized_scope": "lab", "action": "probe"})
    assert r.status == "error"


def test_rotate_execute_no_proxy_list(mod):
    r = mod.run({"mode": "execute", "authorized_scope": "lab", "action": "rotate"})
    assert r.status == "error"


# ---- orchestrator integration -------------------------------------------

def test_orchestrator_registers_module():
    orch = Orchestrator()
    modules = orch.list_modules(category="attack")
    names = [m["name"] for m in modules]
    assert "ip_rotation" in names


def test_orchestrator_simulate_rotate():
    orch = Orchestrator()
    result = orch.run(
        "ip_rotation",
        {"authorized_scope": "lab", "mode": "simulate", "action": "rotate", "rotate_count": "2"},
    )
    assert result.status == "ok"
    assert len(result.artifacts["hops"]) == 2
