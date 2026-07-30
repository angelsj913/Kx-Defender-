"""KxWatch defense module — process snapshot + scoring."""

from __future__ import annotations

from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult
from modules.engines.kxscore import score_process
from modules.engines.kxwatch import list_processes


class ProcessMonitorModule(AttackModule):
    name = "process_monitor"
    category = "defense"
    description = "Self-built process snapshot with KxScore behavioral scoring."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"engine": "KxWatch"},
        )

        if mode == "simulate":
            processes = [
                {"pid": 1, "name": "systemd", "cmdline": "/sbin/init", "ppid": 0},
                {"pid": 4242, "name": "powershell", "cmdline": "powershell -enc AAAA", "ppid": 1},
                {"pid": 7, "name": "kx", "cmdline": "kx watch procs", "ppid": 1},
            ]
        else:
            processes = list_processes(limit=int(params.get("limit", 200)))

        scored = []
        alerts = []
        for proc in processes:
            s = score_process(proc)
            row = {**proc, **s}
            scored.append(row)
            if s["score"] >= 45:
                alerts.append(row)

        result.findings.append(
            Finding(
                title="Process snapshot scored",
                severity="high" if alerts else "info",
                detail=f"{len(scored)} processes, {len(alerts)} elevated",
                evidence={"alerts": len(alerts), "engine": "KxWatch+KxScore"},
            )
        )
        for a in alerts[:10]:
            result.findings.append(
                Finding(
                    title=f"Suspicious process pid={a['pid']}",
                    severity=a["level"],
                    detail=f"{a.get('name')} score={a['score']}",
                    evidence={"reasons": a.get("reasons", []), "cmdline": a.get("cmdline", "")[:200]},
                )
            )
        result.artifacts = {
            "processes": scored,
            "alert_count": len(alerts),
            "engine": "KxWatch",
            "self_built": True,
        }
        return result.finish("ok")
