"""Kerberoasting lab module (simulate + fixture execute)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "ad" / "spns.json"


class KerberoastingModule(AttackModule):
    name = "kerberoasting"
    description = "Enumerate SPNs and collect crackable TGS material in authorized lab mode."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        domain = params.get("domain") or params.get("target") or "lab.local"
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"domain": domain},
        )

        if mode == "simulate":
            spns = [
                {"spn": f"HTTP/web.{domain}", "account": "svc_web", "etype": 23},
                {"spn": f"MSSQLSvc/db.{domain}:1433", "account": "svc_sql", "etype": 23},
            ]
        else:
            if FIXTURE.is_file():
                import json

                data = json.loads(FIXTURE.read_text(encoding="utf-8"))
                spns = data.get("spns", [])
            else:
                spns = [{"spn": f"HTTP/app.{domain}", "account": "svc_app", "etype": 23}]

        hashes = []
        for item in spns:
            digest = hashlib.sha256(f"{item['spn']}:{item['account']}".encode()).hexdigest()[:32]
            hashes.append(
                {
                    "account": item["account"],
                    "spn": item["spn"],
                    "hashcat": f"$krb5tgs$23$*{item['account']}${domain}${item['spn']}*{digest}",
                }
            )

        result.findings.append(
            Finding(
                title="SPN enumeration complete",
                severity="medium",
                detail=f"Discovered {len(spns)} SPN(s) in {domain}",
                evidence={"count": len(spns)},
            )
        )
        result.artifacts = {"spns": spns, "tgs_hashes": hashes}
        return result.finish("ok")
