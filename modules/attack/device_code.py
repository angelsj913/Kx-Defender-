"""OAuth device-code phishing simulator with local mock IdP (no cloud API keys)."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from kx_defender.auth import mask_secret
from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult


class DeviceCodeModule(AttackModule):
    name = "device_code"
    description = "Simulate OAuth device-code phishing against a local mock IdP (no API keys)."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        target = params.get("target") or "mock.idp.local"
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"idp": target},
        )

        user_code = "KX-LAB-" + hashlib.sha1(target.encode()).hexdigest()[:4].upper()
        device_code = hashlib.sha256(f"{target}:{time.time()}".encode()).hexdigest()[:24]
        # Local mock approval — never contacts real cloud IdPs.
        access_token = "labtok_" + hashlib.sha256(device_code.encode()).hexdigest()[:20]

        result.findings.append(
            Finding(
                title="Device code flow completed against mock IdP",
                severity="high",
                detail="Local mock IdP approved the device code; no external API key used",
                evidence={"idp": target, "user_code": user_code},
            )
        )
        result.artifacts = {
            "device_code": device_code,
            "user_code": user_code,
            "verification_uri": f"http://{target}/device",
            "access_token_masked": mask_secret(access_token, keep=4),
            "token_usable_against": "mock Graph API fixture only",
        }
        return result.finish("ok")
