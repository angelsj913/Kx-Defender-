"""C2 / Nexus listener-session manager — self-built, no implants."""

from __future__ import annotations

import socket
import threading
import time
from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult
from modules.engines.nexus_store import NexusStore

_LISTENERS: dict[str, dict[str, Any]] = {}
_SESSIONS: dict[str, dict[str, Any]] = {}


class C2Module(AttackModule):
    name = "c2"
    description = "Lab Nexus listener and session table (echo only; self-built)."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        action = params.get("action", "status")
        host = params.get("host", "127.0.0.1")
        port = int(params.get("port", 4444))
        store = NexusStore()
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"action": action, "host": host, "port": port, "engine": "KxNexus"},
        )

        if action == "start_listener":
            if mode == "simulate":
                listener_id = f"sim-{host}:{port}"
                payload = {
                    "id": listener_id,
                    "host": host,
                    "port": port,
                    "protocol": params.get("protocol", "tcp"),
                    "status": "simulated",
                }
                _LISTENERS[listener_id] = payload
                store.upsert_listener(listener_id, payload)
            else:
                if host not in {"127.0.0.1", "localhost", "::1"}:
                    result.errors.append("execute listener bound to loopback only")
                    return result.finish("error")
                listener_id = self._start_echo_listener(host, port, store)
            result.findings.append(
                Finding(
                    title="Listener registered",
                    severity="info",
                    detail=f"Listener {listener_id} ready (echo/session manager only)",
                )
            )
            result.artifacts = {
                "listener_id": listener_id,
                "listeners": store.list_listeners() or list(_LISTENERS.values()),
                "engine": "KxNexus",
                "self_built": True,
            }
            return result.finish("ok")

        if action == "register_session":
            sid = params.get("session_id") or f"sess-{int(time.time())}"
            payload = {
                "id": sid,
                "agent": params.get("agent", "lab-echo"),
                "status": "active",
                "note": "No implant generation; session bookkeeping only",
            }
            _SESSIONS[sid] = payload
            store.upsert_session(sid, payload)
            result.artifacts = {
                "session": payload,
                "sessions": store.list_sessions() or list(_SESSIONS.values()),
                "engine": "KxNexus",
            }
            result.findings.append(Finding(title="Session registered", severity="info", detail=sid))
            return result.finish("ok")

        result.artifacts = {
            "listeners": store.list_listeners() or list(_LISTENERS.values()),
            "sessions": store.list_sessions() or list(_SESSIONS.values()),
            "engine": "KxNexus",
            "self_built": True,
        }
        result.findings.append(Finding(title="Nexus status", severity="info", detail="Listener/session snapshot"))
        return result.finish("ok")

    def _start_echo_listener(self, host: str, port: int, store: NexusStore) -> str:
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
                store.upsert_listener(listener_id, _LISTENERS[listener_id])
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
                        payload = {
                            "id": sid,
                            "agent": "echo-client",
                            "status": "closed",
                            "peer": f"{addr[0]}:{addr[1]}",
                        }
                        _SESSIONS[sid] = payload
                        store.upsert_session(sid, payload)
                _LISTENERS[listener_id]["status"] = "stopped"
                store.upsert_listener(listener_id, _LISTENERS[listener_id])

        _LISTENERS[listener_id] = {
            "id": listener_id,
            "host": host,
            "port": port,
            "protocol": "tcp",
            "status": "starting",
        }
        store.upsert_listener(listener_id, _LISTENERS[listener_id])
        threading.Thread(target=_serve, daemon=True).start()
        time.sleep(0.1)
        return listener_id
