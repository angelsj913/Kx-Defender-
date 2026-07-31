"""KxSig — self-built signature / pattern matcher (no external YARA binary)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).resolve().parents[2] / "rules" / "kxsig"


def _user_rules_dir() -> Path:
    home = Path(os.environ.get("KX_HOME") or (Path.home() / ".kx-defender"))
    return home / "rules" / "kxsig" / "user"


def _disabled_ids() -> set[str]:
    state = _user_rules_dir().parent / "state.json"
    try:
        value = json.loads(state.read_text(encoding="utf-8"))
        return set((value.get("disabled") or {}).keys())
    except (OSError, json.JSONDecodeError, AttributeError):
        return set()


def load_rules(path: Path | None = None, include_user: bool = True) -> list[dict[str, Any]]:
    """Load all built-in rule JSONs, then merge user-imported rules.

    User rules under ``rules/kxsig/user/*.json`` are appended after built-ins,
    letting operators override or extend without editing shipped files.
    """
    root = path or RULES_DIR
    rules: list[dict[str, Any]] = []
    if root.is_dir():
        for fp in sorted(root.glob("*.json")):
            rules.extend(_read_rule_file(fp))
    if include_user:
        for user_dir in (RULES_DIR / "user", _user_rules_dir()):
            if user_dir.is_dir():
                for fp in sorted(user_dir.glob("*.json")):
                    rules.extend(_read_rule_file(fp))
    loaded = rules or _builtin_rules()
    disabled = _disabled_ids()
    return [rule for rule in loaded if str(rule.get("id") or "") not in disabled]


def _read_rule_file(fp: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict) and "rules" in data and isinstance(data["rules"], list):
        return [r for r in data["rules"] if isinstance(r, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def validate_rules(rules: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (valid_rules, error_messages). Rules missing required fields or
    with invalid regex patterns are excluded from the returned list."""
    ok: list[dict[str, Any]] = []
    errs: list[str] = []
    for i, r in enumerate(rules):
        rid = str(r.get("id") or f"unnamed[{i}]")
        if not isinstance(r, dict):
            errs.append(f"{rid}: not a dict")
            continue
        if not r.get("id") or not r.get("name"):
            errs.append(f"{rid}: missing 'id' or 'name'")
            continue
        patterns = r.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            errs.append(f"{rid}: 'patterns' must be a non-empty list")
            continue
        bad_pat = False
        for p in patterns:
            try:
                re.compile(str(p))
            except re.error as exc:
                errs.append(f"{rid}: invalid regex {p!r}: {exc}")
                bad_pat = True
                break
        if not bad_pat:
            ok.append(r)
    return ok, errs


def import_user_rules(src_path: Path, name: str | None = None) -> dict[str, Any]:
    """Copy a validated rule JSON into ``rules/kxsig/user/<name>.json``.

    Returns a summary dict. Fails safely if the source is missing or invalid.
    """
    try:
        from kx_defender.kxsig_workbench import RuleWorkbench

        result = RuleWorkbench().install(src_path, name=name)
        return {
            "imported": True,
            "destination": result["destination"],
            "count": result["rules"],
            "rejected": 0,
            "errors": [],
        }
    except Exception as exc:
        return {"imported": False, "error": str(exc)}


def list_user_rule_files() -> list[dict[str, Any]]:
    """Enumerate imported user rule files with their rule counts."""
    user_dir = _user_rules_dir()
    if not user_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for fp in sorted(user_dir.glob("*.json")):
        rules = _read_rule_file(fp)
        out.append({"file": str(fp), "count": len(rules)})
    return out


def summarize_rule_catalog() -> dict[str, Any]:
    """Aggregate counts by category and severity across builtin + user rules."""
    rules = load_rules()
    by_cat: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for r in rules:
        by_cat[r.get("category", "?")] = by_cat.get(r.get("category", "?"), 0) + 1
        by_sev[r.get("severity", "info")] = by_sev.get(r.get("severity", "info"), 0) + 1
    return {
        "total": len(rules),
        "by_category": dict(sorted(by_cat.items(), key=lambda x: -x[1])),
        "by_severity": dict(sorted(by_sev.items(), key=lambda x: -x[1])),
        "user_files": list_user_rule_files(),
    }


def _builtin_rules() -> list[dict[str, Any]]:
    return [
        {
            "id": "KXSIG-001",
            "name": "suspicious_powershell_enc",
            "severity": "high",
            "category": "execution",
            "patterns": [r"(?i)powershell.*-enc\s+", r"(?i)frombase64string"],
        },
        {
            "id": "KXSIG-002",
            "name": "mimikatz_strings",
            "severity": "critical",
            "category": "credential-access",
            "patterns": [r"(?i)sekurlsa::", r"(?i)mimikatz"],
        },
        {
            "id": "KXSIG-003",
            "name": "lab_marker",
            "severity": "medium",
            "category": "lab-marker",
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
