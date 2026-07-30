"""Terminate a process via KxAction (self-built)."""

from __future__ import annotations

from typing import Any

from kx_defender.base import DefenseModule
from kx_defender.result import Finding, ModuleResult
from modules.engines.kxaction import terminate


class ProcessKillModule(DefenseModule):
    name = "process_kill"
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
        # In simulate mode, allow missing pid — use a lab-safe mock so demos
        # and self-tests don't fail on `kx kill pid --sim`. Live mode still errors.
        if params["mode"] == "simulate" and pid_raw is None:
            pid_raw = 99999
        if pid_raw is None:
            result.errors.append("pid required (use --pid <n> or --at <n>)")
            return result.finish("error")
        try:
            pid = int(pid_raw)
        except (TypeError, ValueError):
            result.errors.append(f"pid must be integer, got {pid_raw!r}")
            return result.finish("error")

        if params["mode"] == "simulate":
            outcome = {
                "ok": True, "pid": pid, "force": False, "simulated": True,
                "note": "no real process affected in simulate mode",
            }
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
