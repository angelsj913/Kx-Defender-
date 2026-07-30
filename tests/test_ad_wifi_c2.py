from kx_defender.orchestrator import Orchestrator


def test_kerberoasting_execute_fixture():
    orch = Orchestrator()
    result = orch.run(
        "kerberoasting",
        {"authorized_scope": "lab", "mode": "execute", "domain": "lab.local"},
    )
    assert result.status == "ok"
    assert len(result.artifacts["tgs_hashes"]) >= 3


def test_dpapi_masks_secrets():
    orch = Orchestrator()
    result = orch.run(
        "dpapi",
        {"authorized_scope": "lab", "mode": "execute", "target": "127.0.0.1"},
    )
    assert result.status == "ok"
    for cred in result.artifacts["credentials"]:
        assert "*" in cred["secret_masked"]


def test_wifi_cracks_fixture():
    orch = Orchestrator()
    result = orch.run(
        "wifi",
        {"authorized_scope": "lab", "mode": "execute", "essid": "LabWiFi"},
    )
    assert result.status == "ok"
    assert result.artifacts["cracked"] is True


def test_device_code_mock_idp():
    orch = Orchestrator()
    result = orch.run(
        "device_code",
        {"authorized_scope": "lab", "mode": "execute", "target": "mock.idp.local"},
    )
    assert result.status == "ok"
    assert result.artifacts["verification_uri"].startswith("http://mock.idp.local/")


def test_c2_listener_loopback_only():
    orch = Orchestrator()
    deniedish = orch.run(
        "c2",
        {
            "authorized_scope": "lab",
            "mode": "execute",
            "action": "start_listener",
            "host": "8.8.8.8",
            "port": 4444,
            "engagement_file": "fixtures/engagement/lab.example.txt",
        },
    )
    # host 8.8.8.8 fails auth gate before module (not private) unless engagement lists it — it doesn't
    assert deniedish.status == "denied"

    ok = orch.run(
        "c2",
        {
            "authorized_scope": "lab",
            "mode": "execute",
            "action": "start_listener",
            "host": "127.0.0.1",
            "port": 4455,
        },
    )
    assert ok.status == "ok"
    assert "listener_id" in ok.artifacts
