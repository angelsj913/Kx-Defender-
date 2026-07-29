"""KxSig — self-built signature / pattern matcher (no external YARA binary)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).resolve().parents[2] / "rules" / "kxsig"


def load_rules(path: Path | None = None) -> list[dict[str, Any]]:
    root = path or RULES_DIR
    rules: list[dict[str, Any]] = []
    if not root.is_dir():
        return _builtin_rules()
    for fp in sorted(root.glob("*.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(data, list):
            rules.extend(data)
        elif isinstance(data, dict) and "rules" in data:
            rules.extend(data["rules"])
        elif isinstance(data, dict):
            rules.append(data)
    return rules or _builtin_rules()


def _builtin_rules() -> list[dict[str, Any]]:
    return [
        {
            "id": "KXSIG-001",
            "name": "suspicious_powershell_enc",
            "severity": "high",
            "patterns": [r"(?i)powershell.*-enc\s+", r"(?i)frombase64string"],
        },
        {
            "id": "KXSIG-002",
            "name": "mimikatz_strings",
            "severity": "critical",
            "patterns": [r"(?i)sekurlsa::", r"(?i)mimikatz"],
        },
        {
            "id": "KXSIG-003",
            "name": "lab_marker",
            "severity": "medium",
            "patterns": [r"KX_LAB_MALICIOUS_MARKER"],
        },
    ]


def scan_text(text: str, rules: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    active = rules if rules is not None else load_rules()
    hits: list[dict[str, Any]] = []
    for rule in active:
        for pat in rule.get("patterns", []):
            if re.search(pat, text):
                hits.append(
                    {
                        "rule_id": rule.get("id"),
                        "name": rule.get("name"),
                        "severity": rule.get("severity", "medium"),
                        "pattern": pat,
                    }
                )
                break
    return hits


def scan_file(path: Path, rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="ignore")
    digest = hashlib.sha256(raw).hexdigest()
    return {
        "path": str(path),
        "sha256": digest,
        "hits": scan_text(text, rules=rules),
        "size": len(raw),
    }
