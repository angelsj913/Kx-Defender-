"""Family-specific run logic for catalog skills (lab-safe, no SaaS API keys)."""

from __future__ import annotations

from typing import Any, Callable

from kx_defender.auth import mask_secret
from kx_defender.result import Finding, ModuleResult
from modules.attack.c2 import C2Module
from modules.attack.device_code import DeviceCodeModule
from modules.attack.dpapi import DpapiModule
from modules.attack.kerberoasting import KerberoastingModule
from modules.attack.llm_redteam import LlmRedteamModule
from modules.attack.ntlm_relay import NtlmRelayModule
from modules.attack.web_scanner import WebScannerModule
from modules.attack.wifi import WifiModule

Handler = Callable[[str, dict[str, Any]], ModuleResult]


def _base(skill: str, params: dict[str, Any], category: str) -> ModuleResult:
    return ModuleResult(
        module=skill,
        status="running",
        mode=params["mode"],
        authorized_scope=params["authorized_scope"],
        meta={"family_skill": skill, "category": category},
    )


def handle_detecting(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "defense")
    topic = skill.replace("detecting-", "").replace("-", " ")
    result.findings.append(
        Finding(
            title=f"Detection playbook: {topic}",
            severity="medium",
            detail=f"Ran local detection workflow for '{topic}' ({params['mode']})",
            evidence={"signals": ["process", "network", "auth"], "threshold": 70},
        )
    )
    result.artifacts = {
        "detections": [{"rule": skill, "matched": params["mode"] == "simulate", "score": 72}],
        "recommended_actions": ["triage", "contain", "hunt"],
    }
    return result.finish("ok")


def handle_analyzing(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "defense")
    topic = skill.replace("analyzing-", "").replace("-", " ")
    result.findings.append(
        Finding(
            title=f"Analysis complete: {topic}",
            severity="info",
            detail=f"Produced structured analysis notes for '{topic}'",
            evidence={"artifacts_reviewed": 3},
        )
    )
    result.artifacts = {
        "summary": f"Analysis notebook for {topic}",
        "iocs": ["lab.local", "127.0.0.1"],
        "mitre": ["T1059", "T1071"],
    }
    return result.finish("ok")


def handle_auditing(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "defense")
    topic = skill.replace("auditing-", "").replace("-", " ")
    result.findings.append(
        Finding(
            title=f"Audit finding: {topic}",
            severity="medium",
            detail=f"Configuration drift / control gap identified in '{topic}'",
            evidence={"controls_checked": 8, "failed": 2},
        )
    )
    result.artifacts = {
        "checklist": ["inventory", "permissions", "logging", "encryption"],
        "failed_controls": ["excessive_privilege", "missing_mfa_policy"],
    }
    return result.finish("ok")


def handle_securing(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "defense")
    topic = skill.replace("securing-", "").replace("-", " ")
    result.findings.append(
        Finding(
            title=f"Hardening plan: {topic}",
            severity="info",
            detail=f"Generated securing steps for '{topic}'",
            evidence={"steps": 5},
        )
    )
    result.artifacts = {
        "hardening_steps": [
            "inventory assets",
            "apply least privilege",
            "enable logging",
            "verify controls",
            "document exceptions",
        ],
        "target": params.get("target") or params.get("url") or "lab",
    }
    return result.finish("ok")


def handle_triaging(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "defense")
    topic = skill.replace("triaging-", "").replace("-", " ")
    result.findings.append(
        Finding(
            title=f"Triage decision: {topic}",
            severity="high",
            detail="Prioritized as investigate-now based on local scoring",
            evidence={"priority": "P2", "confidence": 0.81},
        )
    )
    result.artifacts = {
        "decision": "investigate",
        "playbook": skill,
        "next_steps": ["scope", "contain", "eradicate", "recover"],
    }
    return result.finish("ok")


def handle_compliance(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "defense")
    result.findings.append(
        Finding(
            title=f"Compliance assessment: {skill}",
            severity="medium",
            detail="Mapped controls and gaps for lab/demo evidence pack",
            evidence={"controls": 12, "gaps": 3},
        )
    )
    result.artifacts = {
        "framework": skill,
        "gaps": ["policy-evidence", "logging-retention", "access-review"],
        "status": "partial",
    }
    return result.finish("ok")


def handle_building_defense(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "defense")
    topic = skill.replace("building-", "").replace("-", " ")
    result.findings.append(
        Finding(
            title=f"Build blueprint: {topic}",
            severity="info",
            detail=f"Emitted defensive build plan for '{topic}'",
            evidence={"components": 4},
        )
    )
    result.artifacts = {
        "blueprint": {
            "name": skill,
            "components": ["ingest", "detect", "respond", "report"],
            "outputs": ["dashboard", "playbook", "metrics"],
        }
    }
    return result.finish("ok")


def handle_testing_for(skill: str, params: dict[str, Any]) -> ModuleResult:
    """Delegate shallow web checks to web_scanner when URL present; else simulate."""
    result = _base(skill, params, "attack")
    topic = skill.replace("testing-for-", "").replace("-", " ")
    url = params.get("url") or params.get("target")
    if params["mode"] == "execute" and url:
        nested = WebScannerModule().run(params)
        result.findings = nested.findings
        result.artifacts = {
            "delegated_to": "web_scanner",
            "focus": topic,
            "web": nested.artifacts,
        }
        result.errors = nested.errors
        return result.finish(nested.status)

    result.findings.append(
        Finding(
            title=f"Web test scenario: {topic}",
            severity="medium",
            detail=f"Simulated OWASP-oriented checks for '{topic}'",
            evidence={"payload_families": ["injection", "auth", "xss", "xxe"]},
        )
    )
    result.artifacts = {"focus": topic, "cases": 5, "mode": "simulate"}
    return result.finish("ok")


def _delegate(module_cls: type, skill: str, params: dict[str, Any], extra_meta: dict[str, Any] | None = None) -> ModuleResult:
    nested = module_cls().run(params)
    nested.module = skill
    nested.meta = {**nested.meta, "delegated_from": module_cls().name, **(extra_meta or {})}
    return nested


def handle_attack_named(skill: str, params: dict[str, Any]) -> ModuleResult:
    mapping: dict[str, Callable[[dict[str, Any]], ModuleResult]] = {
        "attacking-oauth-with-device-code-phishing": lambda p: _delegate(DeviceCodeModule, skill, p),
        "relaying-ntlm-for-adcs-esc8": lambda p: _delegate(NtlmRelayModule, skill, p),
        "abusing-dpapi-for-credential-access": lambda p: _delegate(DpapiModule, skill, p),
        "performing-wifi-password-cracking-with-aircrack": lambda p: _delegate(WifiModule, skill, p),
        "performing-kerberoasting-attack": lambda p: _delegate(KerberoastingModule, skill, p),
        "red-teaming-llms-with-garak": lambda p: _delegate(LlmRedteamModule, skill, p, {"engine": "garak-style-local"}),
        "building-red-team-c2-infrastructure-with-havoc": lambda p: _c2_framework(skill, p, "havoc"),
        "building-c2-infrastructure-with-sliver-framework": lambda p: _c2_framework(skill, p, "sliver"),
        "attacking-entra-id-with-roadtools": lambda p: _entra(skill, p),
        "post-exploiting-microsoft-graph-with-graphrunner": lambda p: _graph(skill, p),
    }
    handler = mapping.get(skill)
    if handler is None:
        result = _base(skill, params, "attack")
        result.errors.append(f"no handler for {skill}")
        return result.finish("error")
    return handler(params)


def _c2_framework(skill: str, params: dict[str, Any], framework: str) -> ModuleResult:
    p = dict(params)
    p.setdefault("action", "start_listener" if params["mode"] == "execute" else "status")
    p.setdefault("host", "127.0.0.1")
    p.setdefault("port", 4455 if framework == "havoc" else 4456)
    result = _delegate(C2Module, skill, p, {"framework": framework, "implant": False})
    result.findings.insert(
        0,
        Finding(
            title=f"{framework} lab infrastructure blueprint",
            severity="info",
            detail="Listener/session manager only — no implant/shellcode/AMSI bypass",
            evidence={"framework": framework},
        ),
    )
    result.artifacts["framework"] = framework
    result.artifacts["exclusions"] = ["implant", "shellcode", "amsi_bypass"]
    return result


def _entra(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "attack")
    tenant = params.get("target") or params.get("domain") or "contoso.lab.local"
    users = [
        {"upn": f"admin@{tenant}", "roles": ["Global Reader"]},
        {"upn": f"svc-app@{tenant}", "roles": ["Application Developer"]},
        {"upn": f"user1@{tenant}", "roles": ["User"]},
    ]
    result.findings.append(
        Finding(
            title="Entra ID recon (ROADtools-style lab)",
            severity="medium",
            detail="Enumerated lab directory objects without cloud API keys",
            evidence={"users": len(users), "tenant": tenant},
        )
    )
    result.artifacts = {
        "tenant": tenant,
        "users": users,
        "apps": [{"name": "LabApp", "permissions": ["User.Read.All"]}],
        "token_ops": {"prt": "simulated", "foci_exchange": "simulated"},
        "tooling": "self-built roadtools-style workflow",
    }
    return result.finish("ok")


def _graph(skill: str, params: dict[str, Any]) -> ModuleResult:
    result = _base(skill, params, "attack")
    token = params.get("access_token") or "labtok_mock"
    result.findings.append(
        Finding(
            title="Microsoft Graph post-exploit (mock)",
            severity="high",
            detail="Queried mock Graph endpoints with lab token (no real M365 tenant)",
            evidence={"token_masked": mask_secret(token, keep=4)},
        )
    )
    result.artifacts = {
        "mail_sample": [{"subject": "Lab invoice", "from": "billing@lab.local"}],
        "drive_sample": [{"name": "secrets-lab.txt", "path": "/Documents"}],
        "teams_sample": [{"channel": "General", "message": "lab ping"}],
        "note": "Mock GraphRunner-style collection only",
    }
    return result.finish("ok")


HANDLERS: dict[str, Handler] = {
    "detecting": handle_detecting,
    "analyzing": handle_analyzing,
    "auditing": handle_auditing,
    "securing": handle_securing,
    "triaging": handle_triaging,
    "compliance": handle_compliance,
    "building_defense": handle_building_defense,
    "testing_for": handle_testing_for,
    "attack_named": handle_attack_named,
}
