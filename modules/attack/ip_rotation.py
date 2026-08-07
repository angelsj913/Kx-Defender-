"""IP Rotation module — proxy-chain traffic routing for red team ops."""

from __future__ import annotations

import random
import socket
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.request import ProxyHandler, build_opener

from kx_defender.base import AttackModule
from kx_defender.result import Finding, ModuleResult
from modules.engines.report import findings_report

# Public IP echo services (ordered by preference)
_IP_CHECK_URLS = [
    "https://api.ipify.org",
    "https://icanhazip.com",
    "https://ifconfig.me/ip",
]

# Default proxy pool used in simulate mode
_SIMULATE_POOL = [
    {"addr": "10.0.0.1", "port": 8080, "proto": "http",  "latency_ms": 42,  "country": "US"},
    {"addr": "10.0.0.2", "port": 1080, "proto": "socks5", "latency_ms": 78,  "country": "DE"},
    {"addr": "10.0.0.3", "port": 3128, "proto": "http",  "latency_ms": 110, "country": "JP"},
    {"addr": "10.0.0.4", "port": 1080, "proto": "socks5", "latency_ms": 55,  "country": "NL"},
    {"addr": "10.0.0.5", "port": 8888, "proto": "http",  "latency_ms": 95,  "country": "SG"},
]


def _check_direct_ip(timeout: float = 4.0) -> str | None:
    for url in _IP_CHECK_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Kx-Defender/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode().strip()
        except Exception:
            continue
    return None


def _check_via_proxy(proxy_addr: str, proxy_port: int, proto: str, timeout: float = 6.0) -> str | None:
    proxy_url = f"{proto}://{proxy_addr}:{proxy_port}"
    handler = ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = build_opener(handler)
    for url in _IP_CHECK_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Kx-Defender/2.0"})
            with opener.open(req, timeout=timeout) as resp:
                return resp.read().decode().strip()
        except Exception:
            continue
    return None


def _probe_proxy(entry: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
    addr = entry["addr"]
    port = entry["port"]
    t0 = time.monotonic()
    try:
        with socket.create_connection((addr, port), timeout=timeout):
            latency_ms = int((time.monotonic() - t0) * 1000)
            return {**entry, "reachable": True, "latency_ms": latency_ms}
    except OSError:
        return {**entry, "reachable": False, "latency_ms": None}


def _parse_proxy_list(raw: str) -> list[dict[str, Any]]:
    """Parse 'proto://addr:port' lines from a comma- or newline-separated string."""
    entries: list[dict[str, Any]] = []
    for token in raw.replace("\n", ",").split(","):
        token = token.strip()
        if not token:
            continue
        proto = "http"
        if "://" in token:
            proto, rest = token.split("://", 1)
        else:
            rest = token
        host_port = rest.split(":")
        if len(host_port) != 2:
            continue
        try:
            entries.append({"addr": host_port[0], "port": int(host_port[1]), "proto": proto})
        except ValueError:
            continue
    return entries


class IpRotationModule(AttackModule):
    name = "ip_rotation"
    description = (
        "Red team IP rotation via proxy chains — tests traffic routing across proxy pool, "
        "measures per-hop latency, and verifies effective IP masking. Lab/owned targets only."
    )

    def run(self, params: dict[str, Any]) -> ModuleResult:
        mode = params["mode"]
        scope = params["authorized_scope"]
        action = params.get("action", "status")
        proxy_list_raw = params.get("proxy_list", "")
        rotate_count = int(params.get("rotate_count", 3))
        check_ip = params.get("check_ip", "true").lower() not in {"false", "0", "no"}

        result = ModuleResult(
            module=self.name,
            status="running",
            mode=mode,
            authorized_scope=scope,
            meta={"action": action, "rotate_count": rotate_count, "engine": "KxRotate"},
        )

        if action == "status":
            return self._action_status(result, mode)

        if action == "probe":
            return self._action_probe(result, mode, proxy_list_raw)

        if action == "rotate":
            return self._action_rotate(result, mode, proxy_list_raw, rotate_count, check_ip)

        if action == "check_ip":
            return self._action_check_ip(result, mode)

        result.errors.append(f"unknown action: {action!r}. choices: status, probe, rotate, check_ip")
        return result.finish("error")

    # ------------------------------------------------------------------ actions

    def _action_status(self, result: ModuleResult, mode: str) -> ModuleResult:
        pool = _SIMULATE_POOL if mode == "simulate" else []
        result.findings.append(
            Finding(
                title="IP Rotation module ready",
                severity="info",
                detail=f"Pool contains {len(pool)} proxies ({mode} mode). "
                "Use action=probe to test reachability or action=rotate to begin rotation.",
            )
        )
        result.artifacts = {
            "pool_size": len(pool),
            "mode": mode,
            "engine": "KxRotate",
            "self_built": True,
            "actions": ["status", "probe", "rotate", "check_ip"],
        }
        result.artifacts["report_html"] = findings_report("KxRotate Status", result.to_dict())
        return result.finish("ok")

    def _action_check_ip(self, result: ModuleResult, mode: str) -> ModuleResult:
        if mode == "simulate":
            ip = "203.0.113.42"  # RFC 5737 documentation range
            result.findings.append(
                Finding(
                    title="Current external IP (simulated)",
                    severity="info",
                    detail=f"Simulated origin IP: {ip}",
                    evidence={"ip": ip, "source": "simulate"},
                )
            )
            result.artifacts = {"origin_ip": ip, "mode": "simulate", "engine": "KxRotate"}
            result.artifacts["report_html"] = findings_report("KxRotate IP Check", result.to_dict())
            return result.finish("ok")

        ip = _check_direct_ip()
        if ip:
            result.findings.append(
                Finding(
                    title="Current external IP",
                    severity="info",
                    detail=f"Detected origin IP: {ip}",
                    evidence={"ip": ip},
                )
            )
            result.artifacts = {"origin_ip": ip, "mode": mode, "engine": "KxRotate"}
        else:
            result.findings.append(
                Finding(
                    title="IP check failed",
                    severity="medium",
                    detail="Could not reach any IP-echo service. No outbound connectivity?",
                )
            )
            result.artifacts = {"origin_ip": None, "engine": "KxRotate"}
        result.artifacts["report_html"] = findings_report("KxRotate IP Check", result.to_dict())
        return result.finish("ok")

    def _action_probe(self, result: ModuleResult, mode: str, proxy_list_raw: str) -> ModuleResult:
        pool = self._resolve_pool(mode, proxy_list_raw)
        if not pool:
            result.errors.append("No proxies to probe. Pass proxy_list=proto://addr:port,... or use simulate mode.")
            return result.finish("error")

        probed: list[dict[str, Any]] = []
        reachable_count = 0

        for entry in pool:
            if mode == "simulate":
                r = {
                    **entry,
                    "reachable": True,
                    "latency_ms": entry.get("latency_ms", random.randint(30, 200)),
                }
            else:
                r = _probe_proxy(entry)

            probed.append(r)
            if r["reachable"]:
                reachable_count += 1
                result.findings.append(
                    Finding(
                        title="Proxy reachable",
                        severity="info",
                        detail=f"{r['proto']}://{r['addr']}:{r['port']} — {r['latency_ms']} ms",
                        evidence=r,
                    )
                )
            else:
                result.findings.append(
                    Finding(
                        title="Proxy unreachable",
                        severity="low",
                        detail=f"{r['proto']}://{r['addr']}:{r['port']} — connection refused/timeout",
                        evidence=r,
                    )
                )

        result.artifacts = {
            "proxies_probed": len(probed),
            "reachable": reachable_count,
            "unreachable": len(probed) - reachable_count,
            "pool": probed,
            "engine": "KxRotate",
            "self_built": True,
        }
        result.artifacts["report_html"] = findings_report("KxRotate Probe", result.to_dict())
        return result.finish("ok")

    def _action_rotate(
        self,
        result: ModuleResult,
        mode: str,
        proxy_list_raw: str,
        rotate_count: int,
        check_ip: bool,
    ) -> ModuleResult:
        pool = self._resolve_pool(mode, proxy_list_raw)
        if not pool:
            result.errors.append("No proxies available. Pass proxy_list= or use simulate mode.")
            return result.finish("error")

        rotate_count = min(rotate_count, len(pool), 10)
        selected = random.sample(pool, rotate_count)
        hops: list[dict[str, Any]] = []
        unique_ips: set[str] = set()

        for i, proxy in enumerate(selected):
            hop: dict[str, Any] = {
                "hop": i + 1,
                "proxy": f"{proxy['proto']}://{proxy['addr']}:{proxy['port']}",
                "country": proxy.get("country", "??"),
            }

            if mode == "simulate":
                sim_ip = f"198.51.100.{random.randint(1, 254)}"  # RFC 5737
                hop["effective_ip"] = sim_ip
                hop["latency_ms"] = proxy.get("latency_ms", random.randint(30, 200))
                hop["success"] = True
                unique_ips.add(sim_ip)
                result.findings.append(
                    Finding(
                        title=f"Hop {i+1}: IP rotated (simulated)",
                        severity="info",
                        detail=f"Via {hop['proxy']} → effective IP {sim_ip} [{hop['country']}]",
                        evidence=hop,
                    )
                )
            else:
                t0 = time.monotonic()
                effective_ip = _check_via_proxy(proxy["addr"], proxy["port"], proxy["proto"])
                hop["latency_ms"] = int((time.monotonic() - t0) * 1000)
                if effective_ip:
                    hop["effective_ip"] = effective_ip
                    hop["success"] = True
                    unique_ips.add(effective_ip)
                    result.findings.append(
                        Finding(
                            title=f"Hop {i+1}: IP rotated",
                            severity="info",
                            detail=f"Via {hop['proxy']} → effective IP {effective_ip}",
                            evidence=hop,
                        )
                    )
                else:
                    hop["effective_ip"] = None
                    hop["success"] = False
                    result.findings.append(
                        Finding(
                            title=f"Hop {i+1}: proxy did not relay",
                            severity="low",
                            detail=f"{hop['proxy']} connected but IP echo failed",
                            evidence=hop,
                        )
                    )
            hops.append(hop)

        origin_ip: str | None = None
        if check_ip:
            origin_ip = _check_direct_ip() if mode != "simulate" else "203.0.113.42"
            masked = origin_ip not in unique_ips if origin_ip else None
            result.findings.append(
                Finding(
                    title="Origin IP masking check",
                    severity="info" if masked else "medium",
                    detail=(
                        f"Origin {origin_ip} not present in effective IPs — masking effective."
                        if masked
                        else f"Origin {origin_ip} leaked or undetermined."
                    ),
                    evidence={"origin_ip": origin_ip, "effective_ips": list(unique_ips), "masked": masked},
                )
            )

        result.artifacts = {
            "hops": hops,
            "unique_effective_ips": len(unique_ips),
            "origin_ip": origin_ip,
            "rotate_count": rotate_count,
            "engine": "KxRotate",
            "self_built": True,
        }
        result.artifacts["report_html"] = findings_report("KxRotate Rotation", result.to_dict())
        return result.finish("ok")

    # ------------------------------------------------------------------ helpers

    def _resolve_pool(self, mode: str, proxy_list_raw: str) -> list[dict[str, Any]]:
        if mode == "simulate":
            if proxy_list_raw:
                parsed = _parse_proxy_list(proxy_list_raw)
                return parsed if parsed else _SIMULATE_POOL
            return list(_SIMULATE_POOL)
        if proxy_list_raw:
            return _parse_proxy_list(proxy_list_raw)
        return []
