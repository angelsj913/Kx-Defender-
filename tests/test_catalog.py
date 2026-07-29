from kx_defender.orchestrator import Orchestrator
from modules.catalog.factory import load_catalog


def test_catalog_loaded():
    skills = load_catalog()
    assert len(skills) >= 250
    families = {s["family"] for s in skills}
    for required in {
        "detecting",
        "analyzing",
        "auditing",
        "securing",
        "triaging",
        "compliance",
        "building_defense",
        "testing_for",
        "attack_named",
    }:
        assert required in families


def test_named_attack_skills_simulate():
    orch = Orchestrator()
    names = [
        "attacking-entra-id-with-roadtools",
        "attacking-oauth-with-device-code-phishing",
        "building-red-team-c2-infrastructure-with-havoc",
        "building-c2-infrastructure-with-sliver-framework",
        "relaying-ntlm-for-adcs-esc8",
        "abusing-dpapi-for-credential-access",
        "performing-wifi-password-cracking-with-aircrack",
        "performing-kerberoasting-attack",
        "post-exploiting-microsoft-graph-with-graphrunner",
        "red-teaming-llms-with-garak",
    ]
    for name in names:
        result = orch.run(
            name,
            {
                "authorized_scope": "lab",
                "mode": "simulate",
                "domain": "lab.local",
                "target": "lab.local",
                "essid": "LabWiFi",
                "action": "status",
            },
        )
        assert result.status == "ok", (name, result.errors)


def test_testing_for_prefix_registered():
    orch = Orchestrator()
    names = orch.list_modules(prefix="testing-for-")
    assert len(names) == 12
    result = orch.run(
        "testing-for-xss-vulnerabilities",
        {"authorized_scope": "lab", "mode": "simulate", "url": "http://127.0.0.1/"},
    )
    assert result.status == "ok"


def test_defense_families_sample():
    orch = Orchestrator()
    samples = [
        "detecting-anomalous-authentication-patterns",
        "analyzing-threat-actor-ttps-with-mitre-attack",
        "auditing-aws-s3-bucket-permissions",
        "securing-aws-iam-permissions",
        "triaging-security-incident",
        "achieving-cmmc-level-2-compliance",
        "building-detection-rules-with-sigma",
    ]
    for name in samples:
        result = orch.run(name, {"authorized_scope": "lab", "mode": "simulate", "target": "lab.local"})
        assert result.status == "ok", name


def test_all_catalog_skills_simulate():
    orch = Orchestrator()
    for item in load_catalog():
        result = orch.run(
            item["name"],
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
        assert result.status == "ok", (item["name"], result.errors)
