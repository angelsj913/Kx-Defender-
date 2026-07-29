"""KxWatch — self-built process enumerator (stdlib / OS only)."""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Any


def list_processes(limit: int = 200) -> list[dict[str, Any]]:
    system = platform.system()
    if system == "Windows":
        return _windows_processes(limit=limit)
    return _posix_processes(limit=limit)


def _posix_processes(limit: int) -> list[dict[str, Any]]:
    procs: list[dict[str, Any]] = []
    proc_root = "/proc"
    if not os.path.isdir(proc_root):
        return [
            {"pid": os.getpid(), "name": "kx", "cmdline": "kx", "ppid": os.getppid()},
        ]
    for entry in sorted(os.listdir(proc_root), key=lambda x: int(x) if x.isdigit() else 0):
        if not entry.isdigit():
            continue
        pid = int(entry)
        base = os.path.join(proc_root, entry)
        name = ""
        cmdline = ""
        ppid = 0
        try:
            with open(os.path.join(base, "comm"), encoding="utf-8", errors="ignore") as fh:
                name = fh.read().strip()
            with open(os.path.join(base, "cmdline"), "rb") as fh:
                cmdline = fh.read().replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
            with open(os.path.join(base, "stat"), encoding="utf-8", errors="ignore") as fh:
                parts = fh.read().split()
                if len(parts) > 3:
                    ppid = int(parts[3])
        except (OSError, ValueError):
            continue
        procs.append({"pid": pid, "name": name or f"pid-{pid}", "cmdline": cmdline, "ppid": ppid})
        if len(procs) >= limit:
            break
    return procs


def _windows_processes(limit: int) -> list[dict[str, Any]]:
    # tasklist CSV — Windows built-in, not a third-party security tool.
    try:
        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except (OSError, subprocess.CalledProcessError):
        return [{"pid": os.getpid(), "name": "kx", "cmdline": "kx", "ppid": 0}]
    procs: list[dict[str, Any]] = []
    for line in out.splitlines():
        cols = [c.strip().strip('"') for c in line.split('","')]
        if len(cols) < 2:
            continue
        name = cols[0]
        try:
            pid = int(cols[1])
        except ValueError:
            continue
        procs.append({"pid": pid, "name": name, "cmdline": name, "ppid": 0})
        if len(procs) >= limit:
            break
    return procs or [{"pid": os.getpid(), "name": "kx", "cmdline": "kx", "ppid": 0}]
