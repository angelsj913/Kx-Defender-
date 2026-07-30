"""Self-built web vulnerability scanner (KxSweep)."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult
from modules.engines.report import findings_report

SQLI_PAYLOADS = ["'", "' OR '1'='1", "1; SELECT 1--"]
XSS_PAYLOADS = ['"><svg/onload=alert(1)>', "<script>alert(1)</script>"]
SQLI_ERRORS = re.compile(
    r"sql syntax|sqlite3\.OperationalError|mysql|odbc|postgres|unclosed quotation",
    re.I,
)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.forms: list[dict[str, Any]] = []
        self._current_form: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        if tag == "a" and ad.get("href"):
            self.links.append(ad["href"])
        if tag == "form":
            self._current_form = {
                "action": ad.get("action", ""),
                "method": ad.get("method", "get").lower(),
                "inputs": [],
            }
        if tag in {"input", "textarea"} and self._current_form is not None:
            self._current_form["inputs"].append(
                {"name": ad.get("name", ""), "type": ad.get("type", "text")}
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None


def _fetch(url: str, timeout: float = 3.0) -> tuple[int, str, dict[str, str]]:
    req = Request(url, headers={"User-Agent": "Kx-Defender-WebScanner/0.1"})
    with urlopen(req, timeout=timeout) as resp:  # nosec B310 - gated to lab targets
        body = resp.read().decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return resp.status, body, headers


class WebScannerModule(AttackModule):
    name = "web_scanner"
    description = "Custom crawler + SQLi/XSS/CSRF checks for authorized local targets."

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        url = params.get("url") or params.get("target") or "http://127.0.0.1:8080/"
        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"url": url},
        )

        if mode == "simulate":
            result.findings = [
                Finding(
                    title="Simulated reflected XSS",
                    severity="high",
                    detail="Parameter q reflects unsanitized input",
                    evidence={"param": "q", "payload": XSS_PAYLOADS[0]},
                ),
                Finding(
                    title="Simulated SQLi error signature",
                    severity="critical",
                    detail="SQL error reflected for id parameter",
                    evidence={"param": "id", "payload": SQLI_PAYLOADS[0]},
                ),
                Finding(
                    title="Simulated missing CSRF token",
                    severity="medium",
                    detail="POST form lacks csrf token field",
                    evidence={"form": "/login"},
                ),
            ]
            result.artifacts = {"pages_crawled": 3, "mode": "simulate"}
            result.finish("ok")
            result.artifacts["report_html"] = findings_report("KxSweep Report", result.to_dict())
            result.artifacts["engine"] = "KxSweep"
            result.artifacts["self_built"] = True
            return result

        findings: list[Finding] = []
        crawled: list[str] = []
        try:
            status, body, headers = _fetch(url)
        except (URLError, HTTPError, TimeoutError, ValueError) as exc:
            # Unreachable target: don't fail the whole command — surface a finding
            # so the operator sees WHY nothing was scanned. Status stays "ok"
            # because the scan attempt itself completed cleanly.
            result.findings.append(
                Finding(
                    title="Target unreachable",
                    severity="info",
                    detail="Seed URL could not be fetched — no web surface to scan.",
                    evidence={"url": url, "error": str(exc), "error_type": type(exc).__name__},
                )
            )
            result.artifacts = {
                "pages_crawled": 0,
                "reachable": False,
                "url": url,
                "engine": "KxSweep",
                "self_built": True,
            }
            result.finish("ok")
            result.artifacts["report_html"] = findings_report("KxSweep Report", result.to_dict())
            return result

        crawled.append(url)
        parser = _LinkParser()
        parser.feed(body)
        base = url
        for href in parser.links[:20]:
            absolute = urljoin(base, href)
            if urlparse(absolute).netloc != urlparse(base).netloc:
                continue
            if absolute not in crawled:
                crawled.append(absolute)

        # Query-param injection checks on seed URL
        parsed = urlparse(url)
        qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if not qs:
            qs = {"q": "test", "id": "1"}
        for param in list(qs.keys())[:5]:
            for payload in SQLI_PAYLOADS:
                test_qs = dict(qs)
                test_qs[param] = payload
                test_url = urlunparse(parsed._replace(query=urlencode(test_qs)))
                try:
                    _s, test_body, _h = _fetch(test_url)
                except (URLError, HTTPError, TimeoutError):
                    continue
                if SQLI_ERRORS.search(test_body):
                    findings.append(
                        Finding(
                            title="Possible SQL injection",
                            severity="critical",
                            detail=f"Error-based SQLi signature via {param}",
                            evidence={"param": param, "payload": payload, "url": test_url},
                        )
                    )
                    break
            for payload in XSS_PAYLOADS:
                test_qs = dict(qs)
                test_qs[param] = payload
                test_url = urlunparse(parsed._replace(query=urlencode(test_qs)))
                try:
                    _s, test_body, _h = _fetch(test_url)
                except (URLError, HTTPError, TimeoutError):
                    continue
                if payload in test_body:
                    findings.append(
                        Finding(
                            title="Possible reflected XSS",
                            severity="high",
                            detail=f"Payload reflected via {param}",
                            evidence={"param": param, "payload": payload, "url": test_url},
                        )
                    )
                    break

        for form in parser.forms:
            names = {i.get("name", "").lower() for i in form.get("inputs", [])}
            if form.get("method") == "post" and not any("csrf" in n for n in names):
                findings.append(
                    Finding(
                        title="Possible CSRF weakness",
                        severity="medium",
                        detail="POST form without csrf token field",
                        evidence={"action": form.get("action", ""), "cookie_samesite": headers.get("set-cookie", "")},
                    )
                )

        if not findings:
            findings.append(
                Finding(
                    title="No obvious OWASP issues in shallow scan",
                    severity="info",
                    detail="Shallow self-built scan completed",
                )
            )

        result.findings = findings
        result.artifacts = {
            "pages_crawled": len(crawled),
            "seed_status": status,
            "forms": len(parser.forms),
            "links": crawled,
            "engine": "KxSweep",
            "self_built": True,
        }
        result.finish("ok")
        result.artifacts["report_html"] = findings_report("KxSweep Report", result.to_dict())
        return result
