"""stdlib JSON API helpers (no web UI / no static console)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from kx_defender.kxlang import KxLangError, parse_line
from kx_defender.orchestrator import Orchestrator


class KxAPIHandler(BaseHTTPRequestHandler):
    orchestrator = Orchestrator()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: Any) -> None:
        self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self._json(200, {"ok": True, "product": "Kx-Defender"})
        if path == "/api/modules":
            qs = parse_qs(parsed.query)
            family = qs.get("family", [None])[0]
            items = self.orchestrator.list_modules(family=family)
            return self._json(200, items)
        if path == "/api/families":
            return self._json(200, self.orchestrator.families())
        if path == "/api/results":
            return self._json(200, self.orchestrator.list_results(limit=50))
        if path.startswith("/api/results/"):
            run_id = path.rsplit("/", 1)[-1]
            item = self.orchestrator.get_result(run_id)
            if item is None:
                return self._json(404, {"error": "not found"})
            return self._json(200, item.to_dict())
        return self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "invalid json"})

        if parsed.path == "/api/kx":
            line = str(payload.get("command") or "").strip()
            if not line:
                return self._json(400, {"error": "command required"})
            if line.startswith("kx "):
                line = line[3:].strip()
            try:
                cmd = parse_line(line)
            except KxLangError as exc:
                return self._json(400, {"error": str(exc)})
            try:
                result = self.orchestrator.run(cmd.module, cmd.params)
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            data = result.to_dict()
            data["kxlang"] = cmd.to_dict()
            return self._json(200 if result.status == "ok" else 422, data)

        if parsed.path == "/api/run":
            module = payload.get("module")
            params = payload.get("params") or {}
            if not module:
                return self._json(400, {"error": "module required"})
            try:
                result = self.orchestrator.run(str(module), params)
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            return self._json(200 if result.status == "ok" else 422, result.to_dict())

        return self._json(404, {"error": "not found"})


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    raise SystemExit(
        "Web console removed. Use the native client: kx\n"
        f"(ignored bind {host}:{port})"
    )
