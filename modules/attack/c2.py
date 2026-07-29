"""C2 listener/session manager only — no implant, shellcode, or bypass."""

from __future__ import annotations

import socket
import threading
import time
from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult

_SESSIONS: dict[str, dict[str, Any]] = {}
_LISTENERS: dict[str, dict[str, Any]] = {}


class C2Module(AttackModule):
    name = "c2"
    description = "Lab C2 listener and session table (echo only; no implants/AMSI bypass)."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        action = params.get("action", "status")
        host = params.get("host", "127.0.0.1")
        port = int(params.get("port", 4444))
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"action": action, "host": host, "port": port},
        )

        if action == "start_listener":
            if mode == "simulate":
                listener_id = f"sim-{host}:{port}"
                _LISTENERS[listener_id] = {
                    "host": host,
                    "port": port,
                    "protocol": params.get("protocol", "tcp"),
                    "status": "simulated",
                }
            else:
                if host not in {"127.0.0.1", "localhost", "::1"}:
                    result.errors.append("execute listener bound to loopback only")
                    return result.finish("error")
                listener_id = self._start_echo_listener(host, port)
            result.findings.append(
                Finding(
                    title="Listener registered",
                    severity="info",
                    detail=f"Listener {listener_id} ready (echo/session manager only)",
                )
            )
            result.artifacts = {"listener_id": listener_id, "listeners": dict(_LISTENERS)}
            return result.finish("ok")

        if action == "register_session":
            sid = params.get("session_id") or f"sess-{int(time.time())}"
            _SESSIONS[sid] = {
                "id": sid,
                "agent": params.get("agent", "lab-echo"),
                "status": "active",
                "note": "No implant generation; session bookkeeping only",
            }
            result.artifacts = {"session": _SESSIONS[sid], "sessions": dict(_SESSIONS)}
            result.findings.append(Finding(title="Session registered", severity="info", detail=sid))
            return result.finish("ok")

        result.artifacts = {"listeners": dict(_LISTENERS), "sessions": dict(_SESSIONS)}
        result.findings.append(
            Finding(title="C2 status", severity="info", detail="Listener/session snapshot")
        )
        return result.finish("ok")

    def _start_echo_listener(self, host: str, port: int) -> str:
        listener_id = f"tcp-{host}:{port}"
        if listener_id in _LISTENERS and _LISTENERS[listener_id].get("status") == "listening":
            return listener_id

        def _serve() -> None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                sock.listen(5)
                sock.settimeout(0.5)
                _LISTENERS[listener_id]["status"] = "listening"
                end = time.time() + 2.0
                while time.time() < end:
                    try:
                        conn, addr = sock.accept()
                    except socket.timeout:
                        continue
                    with conn:
                        data = conn.recv(1024)
                        conn.sendall(data or b"kx-echo")
                        sid = f"sess-{addr[0]}-{addr[1]}"
                        _SESSIONS[sid] = {
                            "id": sid,
                            "agent": "echo-client",
                            "status": "closed",
                            "peer": f"{addr[0]}:{addr[1]}",
                        }
                _LISTENERS[listener_id]["status"] = "stopped"

        _LISTENERS[listener_id] = {
            "host": host,
            "port": port,
            "protocol": "tcp",
            "status": "starting",
        }
        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        time.sleep(0.1)
        return listener_id
