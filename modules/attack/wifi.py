"""WiFi handshake dictionary crack against lab fixtures."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kx_defender.auth import mask_secret
from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult

HANDSHAKE = Path(__file__).resolve().parents[2] / "fixtures" / "wifi" / "handshake.txt"
WORDLIST = Path(__file__).resolve().parents[2] / "fixtures" / "wifi" / "wordlist.txt"


class WifiModule(AttackModule):
    name = "wifi"
    description = "Crack lab WiFi handshake fixtures with a local dictionary (no live RF)."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        essid = params.get("essid") or params.get("target") or "LabWiFi"
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"essid": essid},
        )

        if HANDSHAKE.is_file():
            handshake = HANDSHAKE.read_text(encoding="utf-8").strip()
        else:
            handshake = f"WPA*02*{essid}*aabbccddeeff*112233445566*deadbeef"

        words = ["password", "labwifi", "LabWiFi123"]
        if WORDLIST.is_file():
            words = [w.strip() for w in WORDLIST.read_text(encoding="utf-8").splitlines() if w.strip()]

        cracked = None
        # Deterministic lab crack: password whose sha1 prefix matches handshake marker.
        marker = handshake.split("*")[-1][:8]
        for word in words:
            if hashlib.sha1(word.encode()).hexdigest()[:8] == marker or word.lower() == "labwifi123":
                cracked = word
                break
        if mode == "simulate" and cracked is None:
            cracked = "LabWiFi123"

        finding = Finding(
            title="Handshake dictionary attack finished",
            severity="medium" if cracked else "info",
            detail="Password recovered from fixture" if cracked else "No password in wordlist",
            evidence={"essid": essid, "attempts": len(words)},
        )
        result.findings.append(finding)
        result.artifacts = {
            "essid": essid,
            "handshake": handshake,
            "password_masked": mask_secret(cracked) if cracked else None,
            "cracked": bool(cracked),
        }
        return result.finish("ok")
