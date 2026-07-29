"""NTLM relay / ADCS ESC8 lab state machine."""

from __future__ import annotations

from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult


class NtlmRelayModule(AttackModule):
    name = "ntlm_relay"
    description = "Model NTLM capture→ADCS ESC8 relay workflow for authorized labs."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        target = params.get("target") or params.get("host") or "adcs.lab.local"
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"target": target},
        )

        session = {
            "listener": "http://127.0.0.1:8081/certsrv/",
            "capture_protocol": "SMB",
            "relay_path": "ADCS_ESC8",
            "stages": [
                {"name": "listen", "status": "ok"},
                {"name": "capture_ntlm", "status": "ok" if mode == "simulate" else "ok"},
                {"name": "relay_to_adcs", "status": "ok"},
                {"name": "certificate_issued", "status": "simulated" if mode == "simulate" else "fixture"},
                {"name": "tgt_request", "status": "pending_lab"},
            ],
        }
        result.findings.append(
            Finding(
                title="ESC8 relay chain modeled",
                severity="high",
                detail=f"NTLM relay path toward {target} completed in {mode} mode",
                evidence={"relay_path": "ADCS_ESC8"},
            )
        )
        result.artifacts = {
            "session": session,
            "certificate": {
                "subject": "CN=labuser",
                "template": "Machine",
                "thumbprint": "LABONLY" + ("0" * 32),
                "masked": True,
            },
        }
        return result.finish("ok")
