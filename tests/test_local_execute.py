import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from kx_defender.orchestrator import Orchestrator


class _VulnHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path
        body = "<html><body><a href='/'>home</a>"
        body += "<form method='post' action='/login'><input name='user'><input name='pass'></form>"
        if "q=" in path and "<script>" in path:
            body += path
        if "id=" in path and "'" in path:
            body += "sqlite3.OperationalError: near syntax"
        body += "</body></html>"
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):  # noqa: A003
        return


def test_web_scanner_execute_local():
    server = HTTPServer(("127.0.0.1", 0), _VulnHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        orch = Orchestrator()
        result = orch.run(
            "web_scanner",
            {
                "authorized_scope": "owned",
                "mode": "execute",
                "url": f"http://127.0.0.1:{port}/?q=test&id=1",
            },
        )
        assert result.status == "ok"
        titles = {f.title for f in result.findings}
        assert "Possible SQL injection" in titles or "Possible reflected XSS" in titles or "Possible CSRF weakness" in titles
    finally:
        server.shutdown()


def test_llm_redteam_execute_fixture_no_api_keys():
    orch = Orchestrator()
    result = orch.run(
        "llm_redteam",
        {"authorized_scope": "lab", "mode": "execute", "target": "local-fixture"},
    )
    assert result.status == "ok"
    assert result.artifacts.get("api_keys_used") == 0
    assert any(f.severity in {"high", "medium"} for f in result.findings)
