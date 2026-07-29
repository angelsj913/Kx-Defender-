from kx_defender.orchestrator import Orchestrator


ATTACK_MODULES = [
    "kerberoasting",
    "ntlm_relay",
    "dpapi",
    "device_code",
    "wifi",
    "c2",
    "web_scanner",
    "llm_redteam",
]


def test_registry_lists_phase1_modules():
    orch = Orchestrator()
    names = {m["name"] for m in orch.list_modules()}
    for name in ATTACK_MODULES:
        assert name in names
    assert "process_monitor" in names


def test_all_attack_modules_simulate():
    orch = Orchestrator()
    for name in ATTACK_MODULES:
        result = orch.run(
            name,
            {
                "authorized_scope": "lab",
                "mode": "simulate",
                "domain": "lab.local",
                "target": "lab.local",
                "url": "http://127.0.0.1/",
                "essid": "LabWiFi",
                "action": "status",
            },
        )
        assert result.status == "ok", name
        assert result.run_id
        loaded = orch.get_result(result.run_id)
        assert loaded is not None
        assert loaded.module == name
