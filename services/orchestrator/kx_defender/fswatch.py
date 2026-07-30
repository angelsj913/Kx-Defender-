"""KxFsWatch — poll-based filesystem watcher (no inotify/FSEvents dep).

Every ``interval`` seconds it walks the target directory, records
(mtime, size, sha256) per file, and reports new / modified / deleted files.
Optionally runs KxSig on new/modified files and emits alerts for hits.

Zero external dependencies. Uses only ``os``, ``time``, ``hashlib``.
"""

from __future__ import annotations

import hashlib
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

from kx_defender.alerts import emit_alert


class KxFsWatch:
    def __init__(
        self,
        root: Path,
        interval: float = 15.0,
        max_bytes: int = 5 * 1024 * 1024,  # skip hashing files > 5MB by default
        include_glob: str | None = None,
        scan_new: bool = True,
        max_iterations: int | None = None,
        stream: Any = None,
    ) -> None:
        self.root = root
        self.interval = max(1.0, float(interval))
        self.max_bytes = int(max_bytes)
        self.include_glob = include_glob
        self.scan_new = scan_new
        self.max_iterations = max_iterations
        self.stream = stream or sys.stderr
        self._stop = False
        self._prev: dict[str, dict[str, Any]] = {}

    def request_stop(self, *_args: Any) -> None:
        self._stop = True

    def _snapshot(self) -> dict[str, dict[str, Any]]:
        snap: dict[str, dict[str, Any]] = {}
        if not self.root.is_dir():
            return snap
        matcher = self.include_glob
        for base, _dirs, files in os.walk(self.root):
            for name in files:
                if matcher and not Path(name).match(matcher):
                    continue
                fp = Path(base) / name
                try:
                    st = fp.stat()
                except OSError:
                    continue
                entry: dict[str, Any] = {
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "sha256": None,
                }
                if st.st_size <= self.max_bytes:
                    try:
                        with open(fp, "rb") as fh:
                            entry["sha256"] = hashlib.sha256(fh.read()).hexdigest()
                    except OSError:
                        pass
                snap[str(fp)] = entry
        return snap

    def _diff(self, prev: dict[str, dict[str, Any]], curr: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
        prev_keys = set(prev.keys())
        curr_keys = set(curr.keys())
        added = sorted(curr_keys - prev_keys)
        removed = sorted(prev_keys - curr_keys)
        modified: list[str] = []
        for k in sorted(prev_keys & curr_keys):
            p, c = prev[k], curr[k]
            if p.get("sha256") and c.get("sha256"):
                if p["sha256"] != c["sha256"]:
                    modified.append(k)
            elif p.get("mtime") != c.get("mtime") or p.get("size") != c.get("size"):
                modified.append(k)
        return {"added": added, "removed": removed, "modified": modified}

    def _maybe_sig_scan(self, paths: list[str]) -> int:
        """Run KxSig against a batch of paths, emit an alert per hit-set."""
        if not self.scan_new or not paths:
            return 0
        from modules.engines.kxsig import load_rules, scan_file  # noqa: PLC0415
        rules = load_rules()
        alerts_written = 0
        for p in paths:
            path = Path(p)
            if not path.is_file():
                continue
            try:
                res = scan_file(path, rules=rules)
            except (OSError, ValueError):
                continue
            hits = res.get("hits") or []
            if not hits:
                continue
            top_sev = max(
                (h.get("severity", "info") for h in hits),
                key=lambda s: {"critical":4,"high":3,"medium":2,"low":1,"info":0}.get(s, 0),
            )
            emit_alert(
                module="fs_watch",
                title=f"signature hit on {path.name}",
                severity=top_sev,
                evidence={"path": p, "sha256": res.get("sha256"), "hits": hits[:10]},
                also_stderr=False,
            )
            alerts_written += 1
        return alerts_written

    def run(self) -> dict[str, Any]:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try: signal.signal(sig, self.request_stop)
            except (ValueError, OSError): pass

        print(
            f"[kx watch fs] root={self.root}  interval={self.interval:.0f}s  "
            f"include={self.include_glob or '*'}  scan_new={self.scan_new}  — Ctrl+C to stop",
            file=self.stream,
        )
        emit_alert(
            module="fs_watch",
            title="filesystem watcher started",
            severity="info",
            evidence={"root": str(self.root), "interval": self.interval, "include": self.include_glob},
            also_stderr=False,
        )

        self._prev = self._snapshot()
        iterations = 0
        totals = {"added": 0, "removed": 0, "modified": 0, "alerts": 0}

        while not self._stop:
            self._interruptible_sleep(self.interval)
            if self._stop:
                break
            iterations += 1
            curr = self._snapshot()
            diff = self._diff(self._prev, curr)
            self._prev = curr
            totals["added"] += len(diff["added"])
            totals["removed"] += len(diff["removed"])
            totals["modified"] += len(diff["modified"])
            print(
                f"[kx watch fs] tick {iterations:>4}  "
                f"+{len(diff['added']):>3}  -{len(diff['removed']):>3}  ~{len(diff['modified']):>3}",
                file=self.stream,
            )
            new_alerts = self._maybe_sig_scan(diff["added"] + diff["modified"])
            totals["alerts"] += new_alerts
            if self.max_iterations is not None and iterations >= self.max_iterations:
                break

        emit_alert(
            module="fs_watch",
            title="filesystem watcher stopped",
            severity="info",
            evidence={"iterations": iterations, **totals},
            also_stderr=False,
        )
        print(
            f"[kx watch fs] stopped after {iterations} iter — "
            f"+{totals['added']}, -{totals['removed']}, ~{totals['modified']}, alerts={totals['alerts']}",
            file=self.stream,
        )
        return {"iterations": iterations, **totals}

    def _interruptible_sleep(self, seconds: float) -> None:
        remaining = seconds
        chunk = 0.5
        while remaining > 0 and not self._stop:
            time.sleep(min(chunk, remaining))
            remaining -= chunk
