"""Terminate a process via KxAction (self-built)."""

from __future__ import annotations

from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult
from modules.engines.kxaction import terminate


class ProcessKillModule(AttackModule):
    name = "process_kill"
    category = "defense"
    description = "Terminate a process by PID using self-built KxAction."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=params["mode"],
            authorized_scope=params["authorized_scope"],
            meta={"engine": "KxAction"},
        )
        pid_raw = params.get("pid") or params.get("target")
        if pid_raw is None:
            result.errors.append("pid required")
            return result.finish("error")
        try:
            pid = int(pid_raw)
        except (TypeError, ValueError):
            result.errors.append("pid must be int")
            return result.finish("error")

        if params["mode"] == "simulate":
            outcome = {"ok": True, "pid": pid, "force": False, "simulated": True}
        else:
            force = str(params.get("force", "false")).lower() in {"1", "true", "yes"}
            outcome = terminate(pid, force=force)

        result.findings.append(
            Finding(
                title="Process terminate requested",
                severity="medium" if outcome.get("ok") else "high",
                detail=str(outcome),
                evidence=outcome,
            )
        )
        result.artifacts = {"action": outcome, "engine": "KxAction", "self_built": True}
        return result.finish("ok" if outcome.get("ok") else "error")
