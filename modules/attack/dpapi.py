"""DPAPI credential workflow against local fixtures."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from kx_defender.auth import mask_secret
from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "dpapi" / "secrets.json"


class DpapiModule(AttackModule):
    name = "dpapi"
    description = "Extract and decode DPAPI-protected secrets from authorized lab fixtures."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
        )

        if FIXTURE.is_file():
            secrets = json.loads(FIXTURE.read_text(encoding="utf-8")).get("secrets", [])
        else:
            secrets = [
                {
                    "source": "chrome",
                    "username": "labuser@lab.local",
                    "secret_b64": base64.b64encode(b"LabPass123!").decode(),
                }
            ]

        decoded = []
        for item in secrets:
            plain = base64.b64decode(item["secret_b64"]).decode("utf-8", errors="replace")
            decoded.append(
                {
                    "source": item.get("source", "unknown"),
                    "username": item.get("username", ""),
                    "secret_masked": mask_secret(plain),
                }
            )

        result.findings.append(
            Finding(
                title="DPAPI secrets decoded from fixture",
                severity="high",
                detail=f"Recovered {len(decoded)} secret(s)",
                evidence={"count": len(decoded)},
            )
        )
        result.artifacts = {"credentials": decoded, "wifi_profiles": ["LabWiFi"]}
        return result.finish("ok")
