"""Process monitor stub (simulate on non-Windows CI)."""

from __future__ import annotations

import os
import platform
from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult


class ProcessMonitorModule(AttackModule):
    name = "process_monitor"
    category = "defense"
    description = "List/snapshot processes (simulate outside Windows or when requested)."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"platform": platform.system()},
        )

        if mode == "simulate" or platform.system() != "Windows":
            processes = [
                {"pid": 1, "name": "init", "cmdline": "/sbin/init"},
                {"pid": os.getpid(), "name": "kxctl", "cmdline": "kxctl"},
            ]
            detail = "Simulated process snapshot (non-Windows or simulate mode)"
        else:
            processes = [{"pid": os.getpid(), "name": "kxctl", "cmdline": "kxctl"}]
            detail = "Minimal local snapshot"

        result.findings.append(
            Finding(title="Process snapshot", severity="info", detail=detail, evidence={"count": len(processes)})
        )
        result.artifacts = {"processes": processes}
        return result.finish("ok")
