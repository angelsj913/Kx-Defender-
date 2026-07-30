"""KxSig scan module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult
from modules.engines.kxsig import load_rules, scan_file, scan_text


class SigScanModule(AttackModule):
    name = "sig_scan"
    category = "defense"
    description = "Scan text/files with self-built KxSig rules."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=params["mode"],
            authorized_scope=params["authorized_scope"],
            meta={"engine": "KxSig"},
        )
        rules = load_rules()
        hits: list[dict[str, Any]] = []
        target = params.get("path") or params.get("target")
        sample = params.get("sample") or params.get("text")

        if params["mode"] == "simulate" and not target and not sample:
            sample = "powershell -enc AAAA KX_LAB_MALICIOUS_MARKER"

        if target and Path(str(target)).is_file():
            scan = scan_file(Path(str(target)), rules=rules)
            hits = scan["hits"]
            result.artifacts["file"] = scan
        elif sample:
            hits = scan_text(str(sample), rules=rules)
            result.artifacts["sample_hits"] = hits
        else:
            result.errors.append("provide --at <file> or --with sample=...")
            return result.finish("error")

        for hit in hits:
            result.findings.append(
                Finding(
                    title=f"KxSig hit: {hit.get('name')}",
                    severity=hit.get("severity", "medium"),
                    detail=hit.get("pattern", ""),
                    evidence=hit,
                )
            )
        if not hits:
            result.findings.append(
                Finding(title="No KxSig matches", severity="info", detail="Scan complete")
            )
        result.artifacts.update({"rule_count": len(rules), "hit_count": len(hits), "engine": "KxSig", "self_built": True})
        return result.finish("ok")
