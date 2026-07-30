"""KxAction — self-built process actions (terminate)."""

from __future__ import annotations

import os
import platform
import signal
import subprocess
from typing import Any


PROTECTED_NAMES = {"system", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "kx", "kxctl"}


def terminate(pid: int, force: bool = False) -> dict[str, Any]:
    if pid <= 0:
        return {"ok": False, "error": "invalid pid"}
    if pid == os.getpid():
        return {"ok": False, "error": "refusing to terminate self"}

    system = platform.system()
    try:
        if system == "Windows":
            flags = ["/F", "/PID", str(pid)] if force else ["/PID", str(pid)]
            subprocess.check_call(["taskkill", *flags], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        return {"ok": True, "pid": pid, "force": force}
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"ok": False, "pid": pid, "error": str(exc)}
