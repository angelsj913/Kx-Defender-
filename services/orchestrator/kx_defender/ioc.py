"""KxIOC — local indicator-of-compromise blocklist store.

Strict constraint: NO external feeds. Users maintain their own indicator
files locally; kx loads and matches them. Supported input formats:

  - plain text: one indicator per line, optional ``#`` comments
  - JSON:       ``{"indicators": [{"type": "ip", "value": "1.2.3.4"}, ...]}``

Indicator types auto-detected when reading plain text:
  - ``sha256`` / ``sha1`` / ``md5`` (hex length matches)
  - ``ipv4``   (dotted quad)
  - ``ipv6``   (any string with ``:`` and hex only)
  - ``domain`` (contains a dot and only DNS-safe chars)
  - ``string`` (fallback — matched as literal substring)

Storage layout::

    ~/.kx-defender/ioc/*.json     # normalized indicator files (persisted)
    ~/.kx-defender/ioc/index.json # aggregate index (counts + source paths)

All I/O is local. No sockets, no HTTP, no DNS lookups.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from kx_defender.alerts import _DEFAULT_HOME as KX_HOME

IOC_DIR = KX_HOME / "ioc"
INDEX_PATH = IOC_DIR / "index.json"

# Detection helpers (compiled once)
_IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")
_DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$")
_HEX_RE = re.compile(r"^[a-fA-F0-9]+$")

VALID_TYPES = {"ip", "ipv4", "ipv6", "domain", "url", "sha256", "sha1", "md5", "string"}


def _ensure_dir() -> None:
    try:
        IOC_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def detect_type(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return "string"
    if _IPV4_RE.match(v):
        octets = v.split(".")
        if all(0 <= int(o) <= 255 for o in octets):
            return "ipv4"
    if ":" in v and _IPV6_RE.match(v) and v.count(":") >= 2:
        return "ipv6"
    if v.startswith("http://") or v.startswith("https://"):
        return "url"
    if _HEX_RE.match(v):
        if len(v) == 64: return "sha256"
        if len(v) == 40: return "sha1"
        if len(v) == 32: return "md5"
    if _DOMAIN_RE.match(v):
        return "domain"
    return "string"


def parse_indicator_file(path: Path) -> list[dict[str, Any]]:
    """Parse a source file into a list of ``{type, value, source}`` dicts.

    Accepts JSON (``{indicators:[...]}`` or plain list) or plain text.
    """
    if not path.is_file():
        return []
    raw = path.read_text(encoding="utf-8", errors="ignore")

    # Try JSON first.
    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            arr = data.get("indicators")
            if isinstance(arr, list):
                return _normalize_list(arr, source=str(path))
        elif isinstance(data, list):
            return _normalize_list(data, source=str(path))

    # Plain text fallback.
    out: list[dict[str, Any]] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        clean = line.split("#", 1)[0].strip()
        if not clean:
            continue
        out.append({
            "type": detect_type(clean),
            "value": clean.lower() if detect_type(clean) in {"ipv4", "ipv6", "domain"} else clean,
            "source": f"{path}:{lineno}",
        })
    return out


def _normalize_list(items: list, source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        if isinstance(it, str):
            out.append({"type": detect_type(it), "value": it.strip(), "source": source})
        elif isinstance(it, dict):
            t = str(it.get("type") or "").lower() or detect_type(str(it.get("value") or ""))
            v = str(it.get("value") or "").strip()
            if not v:
                continue
            if t not in VALID_TYPES:
                t = detect_type(v)
            note = it.get("note") or it.get("description") or ""
            entry = {"type": t, "value": v.lower() if t in {"ipv4","ipv6","domain"} else v, "source": source}
            if note:
                entry["note"] = str(note)
            out.append(entry)
    return out


def _slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "indicators"


def load_indicators(source_file: Path, name: str | None = None) -> dict[str, Any]:
    """Ingest an external file into the local IOC store."""
    indicators = parse_indicator_file(source_file)
    if not indicators:
        return {"loaded": False, "reason": "no indicators parsed", "source": str(source_file)}
    _ensure_dir()
    fname = _slugify(name or source_file.stem) + ".json"
    dest = IOC_DIR / fname
    payload = {
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source_file),
        "count": len(indicators),
        "indicators": indicators,
    }
    try:
        dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"loaded": False, "reason": f"write failed: {exc}"}
    _rebuild_index()
    return {"loaded": True, "destination": str(dest), "count": len(indicators)}


def list_indicator_files() -> list[dict[str, Any]]:
    if not IOC_DIR.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for fp in sorted(IOC_DIR.glob("*.json")):
        if fp.name == "index.json":
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append({
            "file": str(fp),
            "count": data.get("count", 0),
            "loaded_at": data.get("loaded_at"),
            "source": data.get("source"),
        })
    return out


def _load_all_indicators() -> list[dict[str, Any]]:
    if not IOC_DIR.is_dir():
        return []
    merged: list[dict[str, Any]] = []
    for fp in sorted(IOC_DIR.glob("*.json")):
        if fp.name == "index.json":
            continue
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        arr = data.get("indicators")
        if isinstance(arr, list):
            merged.extend(arr)
    return merged


def _rebuild_index() -> None:
    _ensure_dir()
    indicators = _load_all_indicators()
    by_type: dict[str, int] = {}
    for i in indicators:
        by_type[i.get("type", "string")] = by_type.get(i.get("type", "string"), 0) + 1
    try:
        INDEX_PATH.write_text(
            json.dumps({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total": len(indicators),
                "by_type": by_type,
                "files": list_indicator_files(),
            }, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def catalog() -> dict[str, Any]:
    """Return aggregate stats + file list."""
    if INDEX_PATH.is_file():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    _rebuild_index()
    if INDEX_PATH.is_file():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"total": 0, "by_type": {}, "files": []}


def clear_all() -> int:
    """Delete every IOC file. Returns number removed."""
    if not IOC_DIR.is_dir():
        return 0
    removed = 0
    for fp in IOC_DIR.glob("*.json"):
        try:
            fp.unlink()
            removed += 1
        except OSError:
            pass
    return removed


# ============================================================
# Matching
# ============================================================
def _hash_bytes(data: bytes) -> dict[str, str]:
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha1":   hashlib.sha1(data).hexdigest(),
        "md5":    hashlib.md5(data).hexdigest(),
    }


def check_text(text: str, indicators: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Find indicators appearing in ``text`` (case-insensitive for hosts).

    Returns list of ``{type, value, source, match}`` dicts.
    """
    inds = indicators if indicators is not None else _load_all_indicators()
    if not inds or not text:
        return []
    lower = text.lower()
    hits: list[dict[str, Any]] = []
    for ind in inds:
        t = ind.get("type", "string")
        v = str(ind.get("value") or "")
        if not v:
            continue
        needle = v.lower() if t in {"ipv4", "ipv6", "domain", "url"} else v
        haystack = lower if t in {"ipv4", "ipv6", "domain", "url"} else text
        # For domain/IP, require token boundary to reduce false positives.
        if t in {"domain", "ipv4", "ipv6"}:
            if _boundary_match(haystack, needle):
                hits.append({**ind, "match": "boundary"})
        else:
            if needle in haystack:
                hits.append({**ind, "match": "substring"})
    return hits


def _boundary_match(haystack: str, needle: str) -> bool:
    """Match needle only when surrounded by non-alphanumeric-or-dot chars."""
    if not needle:
        return False
    i = 0
    n = len(needle)
    while True:
        idx = haystack.find(needle, i)
        if idx < 0:
            return False
        before_ok = idx == 0 or not (haystack[idx - 1].isalnum() or haystack[idx - 1] in "._-")
        after = idx + n
        after_ok = after >= len(haystack) or not (haystack[after].isalnum() or haystack[after] in "._-")
        if before_ok and after_ok:
            return True
        i = idx + 1


def check_file(path: Path, indicators: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Scan a file's bytes/text and hashes against the indicator store."""
    if not path.is_file():
        return {"file": str(path), "error": "not a file", "hits": []}
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"file": str(path), "error": str(exc), "hits": []}
    text_view = data.decode("utf-8", errors="ignore")
    hashes = _hash_bytes(data)

    inds = indicators if indicators is not None else _load_all_indicators()
    hits: list[dict[str, Any]] = check_text(text_view, indicators=inds)

    # Direct hash comparison (fast: build lookup once)
    hash_lookup: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for ind in inds:
        t = ind.get("type")
        if t in {"sha256", "sha1", "md5"}:
            key = (t, str(ind.get("value") or "").lower())
            hash_lookup.setdefault(key, []).append(ind)
    for algo, digest in hashes.items():
        for ind in hash_lookup.get((algo, digest.lower()), []):
            hits.append({**ind, "match": "hash"})

    return {"file": str(path), "size": len(data), "sha256": hashes["sha256"], "hits": hits}
