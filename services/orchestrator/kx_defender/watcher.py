"""KxWatcher — polling loop that repeatedly runs process_monitor + sig_scan
and forwards elevated findings to the local alert log.

Zero external dependencies. Uses only stdlib (time, signal, sys). No sockets,
no HTTP, no cloud APIs.
"""

from __future__ import annotations

import signal
import sys
import time
from typing import Any

from kx_defender.alerts import emit_alert, emit_from_findings
from kx_defender.orchestrator import Orchestrator

DEFAULT_INTERVAL = 15   # seconds between polls
DEFAULT_LIMIT = 200     # max processes per snapshot
DEFAULT_MIN_SEV = "high"


def _severity_rank(sev: str) -> int:
    return {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(str(sev).lower(), 0)


class KxWatcher:
    """Polling loop that runs process_monitor and forwards elevated findings.

    The loop can be interrupted via SIGINT/SIGTERM (Ctrl+C). Every iteration is
    a fresh orchestrator run — no in-memory state that would drift, no
    background threads that could deadlock.
    """

    def __init__(
        self,
        interval: float = DEFAULT_INTERVAL,
        limit: int = DEFAULT_LIMIT,
        min_severity: str = DEFAULT_MIN_SEV,
        scope: str = "lab",
        mode: str = "execute",
        max_iterations: int | None = None,
        stream: Any = None,
    ) -> None:
        self.interval = max(1.0, float(interval))
        self.limit = int(limit)
        self.min_severity = str(min_severity).lower()
        self.scope = scope
        self.mode = mode
        self.max_iterations = max_iterations
        self.stream = stream or sys.stderr
        self._stop = False
        self.orch = Orchestrator()

    def request_stop(self, *_args: Any) -> None:
        self._stop = True

    def run(self) -> dict[str, int]:
        """Run the poll loop until stopped. Returns simple counters."""
        # Install signal handlers on the main thread only; guard against
        # ValueError when called from a non-main thread (unit tests etc).
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self.request_stop)
            except (ValueError, OSError):
                pass

        iterations = 0
        total_alerts = 0
        total_procs = 0
        print(
            f"[kx watch] polling every {self.interval:.0f}s "
            f"(mode={self.mode}, scope={self.scope}, min_severity={self.min_severity})  "
            f"— Ctrl+C to stop",
            file=self.stream,
        )
        emit_alert(
            module="watcher",
            title="continuous watcher started",
            severity="info",
            evidence={
                "interval": self.interval,
                "min_severity": self.min_severity,
                "scope": self.scope,
                "mode": self.mode,
            },
            also_stderr=False,
        )

        while not self._stop:
            iterations += 1
            snapshot_alerts, snapshot_procs = self._one_tick(iterations)
            total_alerts += snapshot_alerts
            total_procs += snapshot_procs
            if self.max_iterations is not None and iterations >= self.max_iterations:
                break
            self._interruptible_sleep(self.interval)

        emit_alert(
            module="watcher",
            title="continuous watcher stopped",
            severity="info",
            evidence={
                "iterations": iterations,
                "alerts_written": total_alerts,
                "procs_scanned": total_procs,
            },
            also_stderr=False,
        )
        print(
            f"[kx watch] stopped after {iterations} iteration(s) "
            f"— {total_alerts} alerts, {total_procs} process reads",
            file=self.stream,
        )
        return {
            "iterations": iterations,
            "alerts": total_alerts,
            "procs_scanned": total_procs,
        }

    def _one_tick(self, iteration: int) -> tuple[int, int]:
        try:
            result = self.orch.run("process_monitor", {
                "authorized_scope": self.scope,
                "mode": self.mode,
                "limit": self.limit,
            })
        except Exception as exc:  # noqa: BLE001 - watcher must not die on module errors
            print(f"[kx watch] tick {iteration} error: {exc}", file=self.stream)
            return (0, 0)

        procs = (result.artifacts or {}).get("processes", []) or []
        # Only forward findings ≥ min_severity to the alert log. process_monitor
        # itself already emits a per-alert Finding per elevated process.
        findings = [f.to_dict() if hasattr(f, "to_dict") else f for f in (result.findings or [])]
        written = emit_from_findings(
            module="process_monitor",
            findings=findings,
            min_severity=self.min_severity,
            also_stderr=False,
        )
        alert_count = (result.artifacts or {}).get("alert_count", 0)
        print(
            f"[kx watch] tick {iteration:>4}  procs={len(procs):>4}  "
            f"raised={alert_count:>3}  alerts_written={written}",
            file=self.stream,
        )
        return (written, len(procs))

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep in small chunks so SIGINT is honored quickly."""
        remaining = seconds
        chunk = 0.5
        while remaining > 0 and not self._stop:
            time.sleep(min(chunk, remaining))
            remaining -= chunk
