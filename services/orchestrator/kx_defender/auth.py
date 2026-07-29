"""Authorization gates for lab-only / owned-target execution."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED_SCOPES = {"lab", "owned", "engagement"}
ALLOWED_MODES = {"simulate", "execute"}

PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


class AuthorizationError(ValueError):
    """Raised when a run fails the authorization gate."""


def _host_from_target(target: str | None) -> str | None:
    if not target:
        return None
    value = target.strip()
    if "://" in value:
        return urlparse(value).hostname
    if "/" in value and not value.startswith("["):
        # path-like engagement file or domain/path — keep host part if looks like host/path
        maybe = value.split("/", 1)[0]
        if re.match(r"^[A-Za-z0-9._-]+$", maybe):
            return maybe
        return None
    if value.startswith("[") and "]" in value:
        return value[1 : value.index("]")]
    if ":" in value and value.count(":") == 1:
        host, _port = value.rsplit(":", 1)
        return host
    return value


def is_local_or_private_host(host: str | None) -> bool:
    if not host:
        return False
    lowered = host.lower()
    if lowered in {"localhost", "lab.local", "kx.lab", "mock.idp.local"}:
        return True
    if lowered.endswith(".lab") or lowered.endswith(".local") or lowered.endswith(".test"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Unresolved hostname: only allow clearly lab-ish suffixes (handled above)
        return False
    return any(ip in net for net in PRIVATE_NETWORKS)


def engagement_allows(target: str | None, engagement_file: str | None) -> bool:
    if not engagement_file:
        return False
    path = Path(engagement_file)
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if not target:
        return "authorized_targets:" in text or "AUTHORIZED" in text.upper()
    host = _host_from_target(target) or target
    return host in text or target in text


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    scope = params.get("authorized_scope")
    mode = params.get("mode", "simulate")

    if scope not in ALLOWED_SCOPES:
        raise AuthorizationError(
            f"authorized_scope must be one of {sorted(ALLOWED_SCOPES)}; got {scope!r}"
        )
    if mode not in ALLOWED_MODES:
        raise AuthorizationError(f"mode must be one of {sorted(ALLOWED_MODES)}; got {mode!r}")

    target = (
        params.get("target")
        or params.get("url")
        or params.get("domain")
        or params.get("host")
        or params.get("essid")
    )
    engagement_file = params.get("engagement_file")

    if mode == "execute":
        host = _host_from_target(str(target) if target else None)
        allowed = is_local_or_private_host(host) or engagement_allows(
            str(target) if target else None, engagement_file
        )
        # Lab scope may run against fixture tokens (ESSID, local-fixture) with no network host.
        if not allowed and scope == "lab":
            if host is None or ("." not in host and "://" not in str(target or "")):
                allowed = True
        if not allowed:
            raise AuthorizationError(
                "execute mode requires localhost/RFC1918/.lab/.local/.test target, "
                "a lab fixture token (lab scope), or an engagement_file allow-list"
            )

    cleaned = dict(params)
    cleaned["mode"] = mode
    cleaned["authorized_scope"] = scope
    return cleaned


def mask_secret(value: str, keep: int = 2) -> str:
    if not value:
        return value
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}{'*' * (len(value) - keep * 2)}{value[-keep:]}"
