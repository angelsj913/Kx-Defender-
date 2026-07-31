"""KxDaemon — background watcher process (100% internal, no external services).

Layout::

    ~/.kx-defender/daemon.pid    # decimal PID of the running daemon
    ~/.kx-defender/daemon.json   # last-loaded config (audit trail)
    ~/.kx-defender/daemon.log    # combined stdout+stderr of the daemon
    ~/.kx-defender/alerts.jsonl  # (from alerts.py) alert stream

POSIX: uses os.fork()+setsid() double-fork to detach. Signals (SIGTERM/SIGINT)
trigger graceful shutdown via KxWatcher.request_stop().

Windows: uses subprocess.Popen with DETACHED_PROCESS/CREATE_NEW_PROCESS_GROUP.
Stop is delivered via CTRL_BREAK_EVENT.

All I/O is local files. No sockets, no HTTP, no external services.
"""

from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from kx_defender.alerts import _DEFAULT_HOME as KX_HOME

PID_PATH = KX_HOME / "daemon.pid"
CONFIG_PATH = KX_HOME / "daemon.json"
LOG_PATH = KX_HOME / "daemon.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "interval": 30,
    "limit": 500,
    "min_severity": "high",
    "scope": "lab",
    "mode": "execute",
}


def _ensure_home() -> None:
    try:
        KX_HOME.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def load_config(path: Path | None = None) -> dict[str, Any]:
    target = path or CONFIG_PATH
    if not target.is_file():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAULT_CONFIG)
        merged = dict(DEFAULT_CONFIG)
        merged.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)


def save_config(config: dict[str, Any], path: Path | None = None) -> None:
    target = path or CONFIG_PATH
    _ensure_home()
    try:
        target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def read_pid(path: Path | None = None) -> int | None:
    target = path or PID_PATH
    if not target.is_file():
        return None
    try:
        raw = target.read_text(encoding="utf-8").strip()
        pid = int(raw)
        if pid <= 0:
            return None
        return pid
    except (OSError, ValueError):
        return None


def write_pid(pid: int, path: Path | None = None) -> None:
    target = path or PID_PATH
    _ensure_home()
    try:
        target.write_text(f"{pid}\n", encoding="utf-8")
    except OSError:
        pass


def clear_pid(path: Path | None = None) -> None:
    target = path or PID_PATH
    try:
        target.unlink(missing_ok=True)
    except (OSError, TypeError):
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass


def is_running(pid: int) -> bool:
    """Best-effort liveness check for a PID. No process introspection beyond
    what the OS gives us via signals/openprocess."""
    if pid <= 0:
        return False
    system = platform.system()
    if system == "Windows":
        # Use tasklist filter — no third-party dependency, still just OS-built-in.
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="ignore",
                timeout=5,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
        return str(pid) in (out or "")
    # POSIX: signal 0 doesn't send anything, just checks permission.
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but owned by another user — still "running".
        return True
    except OSError:
        return False


def daemon_status(pid_path: Path | None = None) -> dict[str, Any]:
    pid = read_pid(pid_path)
    if pid is None:
        return {"running": False, "reason": "no pid file"}
    if not is_running(pid):
        return {"running": False, "pid": pid, "reason": "stale pid file"}
    return {"running": True, "pid": pid, "pid_path": str(pid_path or PID_PATH)}


def daemon_stop(pid_path: Path | None = None, timeout: float = 10.0) -> dict[str, Any]:
    pid = read_pid(pid_path)
    if pid is None:
        return {"stopped": False, "reason": "no pid file"}
    if not is_running(pid):
        clear_pid(pid_path)
        return {"stopped": True, "pid": pid, "note": "was not running; cleaned stale pid file"}
    system = platform.system()
    sig = signal.SIGBREAK if system == "Windows" and hasattr(signal, "SIGBREAK") else signal.SIGTERM
    try:
        os.kill(pid, sig)
    except (ProcessLookupError, PermissionError, OSError) as exc:
        return {"stopped": False, "pid": pid, "error": str(exc)}
    # Poll for exit.
    deadline = time.time() + max(1.0, float(timeout))
    while time.time() < deadline:
        if not is_running(pid):
            clear_pid(pid_path)
            return {"stopped": True, "pid": pid}
        time.sleep(0.2)
    return {"stopped": False, "pid": pid, "error": "timeout waiting for exit"}


def _run_watcher_forever(config: dict[str, Any]) -> None:
    """Entry point executed inside the daemon process. Blocks until stopped."""
    from kx_defender.alerts import emit_alert  # noqa: PLC0415
    from kx_defender.watcher import KxWatcher  # noqa: PLC0415

    emit_alert(
        module="daemon",
        title="kx daemon started",
        severity="info",
        evidence={"pid": os.getpid(), **config},
        also_stderr=False,
    )
    try:
        def run_schedules() -> None:
            from kx_defender.scheduler import ScheduleStore  # noqa: PLC0415

            for outcome in ScheduleStore().run_due():
                emit_alert(
                    module="scheduler",
                    title=f"scheduled playbook {outcome['name']}: {outcome['status']}",
                    severity="high" if outcome["status"] == "failed" else "info",
                    evidence=outcome,
                    also_stderr=False,
                )

        watcher = KxWatcher(
            interval=float(config.get("interval", DEFAULT_CONFIG["interval"])),
            limit=int(config.get("limit", DEFAULT_CONFIG["limit"])),
            min_severity=str(config.get("min_severity", DEFAULT_CONFIG["min_severity"])),
            scope=str(config.get("scope", DEFAULT_CONFIG["scope"])),
            mode=str(config.get("mode", DEFAULT_CONFIG["mode"])),
            tick_callback=run_schedules,
        )
        watcher.run()
    except Exception as exc:  # noqa: BLE001 - never crash silently
        emit_alert(
            module="daemon",
            title="kx daemon crashed",
            severity="critical",
            evidence={"error": str(exc), "error_type": type(exc).__name__},
            also_stderr=False,
        )
    finally:
        emit_alert(
            module="daemon",
            title="kx daemon exited",
            severity="info",
            evidence={"pid": os.getpid()},
            also_stderr=False,
        )
        clear_pid()


def daemon_start(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Spawn the daemon as a detached background process.

    On POSIX: double-fork + setsid.
    On Windows: subprocess.Popen with DETACHED_PROCESS.

    Refuses to start if a live daemon already holds the PID file.
    """
    existing = read_pid()
    if existing is not None and is_running(existing):
        return {"started": False, "pid": existing, "reason": "already running"}
    if existing is not None:
        # Stale pid file — clean it before starting fresh.
        clear_pid()

    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update({k: v for k, v in config.items() if k in DEFAULT_CONFIG})
    save_config(cfg)
    _ensure_home()

    system = platform.system()
    if system == "Windows":
        return _start_windows(cfg)
    return _start_posix(cfg)


def _start_posix(config: dict[str, Any]) -> dict[str, Any]:
    # First fork.
    try:
        pid = os.fork()
    except OSError as exc:
        return {"started": False, "error": f"fork failed: {exc}"}
    if pid > 0:
        # Parent — wait briefly for the pid file to appear.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            recorded = read_pid()
            if recorded and is_running(recorded):
                return {"started": True, "pid": recorded, "config": config}
            time.sleep(0.1)
        return {"started": True, "pid": None, "config": config,
                "note": "detached but pid not yet observed"}

    # First child.
    try:
        os.setsid()
    except OSError:
        pass
    try:
        pid2 = os.fork()
    except OSError:
        os._exit(1)
    if pid2 > 0:
        os._exit(0)

    # Second child (the daemon).
    _redirect_std_streams()
    write_pid(os.getpid())
    _run_watcher_forever(config)
    os._exit(0)


def _start_windows(config: dict[str, Any]) -> dict[str, Any]:
    """Re-invoke Python with a private entry point in a detached process."""
    python = sys.executable or "python"
    cmd = [
        python, "-c",
        "from kx_defender.daemon import _windows_child_entry; _windows_child_entry()",
    ]
    creation_flags = 0
    try:
        creation_flags |= subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
        creation_flags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    except AttributeError:
        pass
    _ensure_home()
    log = open(LOG_PATH, "a", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log, stderr=log, stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creation_flags,
        )
    except OSError as exc:
        log.close()
        return {"started": False, "error": f"popen failed: {exc}"}

    # Watchdog wait for the child to record its own pid.
    deadline = time.time() + 5.0
    while time.time() < deadline:
        recorded = read_pid()
        if recorded and is_running(recorded):
            return {"started": True, "pid": recorded, "config": config}
        time.sleep(0.1)
    return {"started": True, "pid": proc.pid, "config": config,
            "note": "detached but pid not yet observed"}


def _windows_child_entry() -> None:
    """Entry the Windows child launches. Just records its pid and runs."""
    _redirect_std_streams()
    write_pid(os.getpid())
    cfg = load_config()
    _run_watcher_forever(cfg)


def _redirect_std_streams() -> None:
    """Point stdin/stdout/stderr at the daemon log so the watcher never blocks
    on a closed console handle."""
    try:
        _ensure_home()
        log = open(LOG_PATH, "a", encoding="utf-8")
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())
        devnull = open(os.devnull, "r")
        os.dup2(devnull.fileno(), sys.stdin.fileno())
    except (OSError, ValueError):
        pass
