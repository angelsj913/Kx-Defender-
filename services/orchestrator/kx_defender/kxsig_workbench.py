"""Safe local workbench for KxSig JSON rules."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}
MAX_RULE_BYTES = 1024 * 1024
MAX_SAMPLE_BYTES = 5 * 1024 * 1024
MAX_PATTERN_LENGTH = 4096
_NESTED_QUANTIFIER = re.compile(r"\([^)]*(?:\+|\*)[^)]*\)(?:\+|\*|\{\d)")


class RuleWorkbenchError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_rules() -> Path:
    return Path(__file__).resolve().parents[3] / "rules" / "kxsig"


def _read_document(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not path.is_file():
        raise RuleWorkbenchError(f"rule file not found: {path}")
    if path.stat().st_size > MAX_RULE_BYTES:
        raise RuleWorkbenchError("rule file exceeds 1 MiB")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuleWorkbenchError(f"invalid rule JSON: {exc}") from exc
    metadata = document if isinstance(document, dict) else {}
    if isinstance(document, dict) and isinstance(document.get("rules"), list):
        values = document["rules"]
    elif isinstance(document, list):
        values = document
    elif isinstance(document, dict):
        values = [document]
    else:
        values = []
    return [value for value in values if isinstance(value, dict)], metadata


class RuleWorkbench:
    def __init__(self, home: Path | str | None = None):
        self.home = Path(
            home or os.environ.get("KX_HOME") or (Path.home() / ".kx-defender")
        ).expanduser().resolve()
        self.user_dir = self.home / "rules" / "kxsig" / "user"
        self.quarantine_dir = self.home / "rules" / "kxsig" / "quarantine"
        self.state_file = self.home / "rules" / "kxsig" / "state.json"

    def _categories(self) -> set[str]:
        try:
            _, metadata = _read_document(_repo_rules() / "core.json")
            values = metadata.get("_categories") or []
            return {str(value) for value in values}
        except RuleWorkbenchError:
            return {"execution", "credential-access", "lab-marker"}

    def validate_file(self, path: Path | str) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        try:
            rules, _ = _read_document(source)
        except RuleWorkbenchError as exc:
            return {"valid": False, "path": str(source), "rules": 0, "errors": [str(exc)]}
        errors: list[str] = []
        seen: set[str] = set()
        categories = self._categories()
        if not rules:
            errors.append("no rules found")
        for index, rule in enumerate(rules):
            rule_id = str(rule.get("id") or f"rule[{index}]")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", rule_id):
                errors.append(f"{rule_id}: invalid rule id")
            if rule_id in seen:
                errors.append(f"duplicate rule id: {rule_id}")
            seen.add(rule_id)
            if not str(rule.get("name") or "").strip():
                errors.append(f"{rule_id}: name is required")
            severity = str(rule.get("severity") or "").lower()
            if severity not in VALID_SEVERITIES:
                errors.append(f"{rule_id}: unsupported severity {severity!r}")
            category = str(rule.get("category") or "")
            if category not in categories:
                errors.append(f"{rule_id}: unsupported category {category!r}")
            patterns = rule.get("patterns")
            if not isinstance(patterns, list) or not patterns:
                errors.append(f"{rule_id}: patterns must be a non-empty list")
                continue
            for pattern in patterns:
                text = str(pattern)
                if not text:
                    errors.append(f"{rule_id}: empty pattern")
                    continue
                if len(text) > MAX_PATTERN_LENGTH:
                    errors.append(f"{rule_id}: pattern exceeds {MAX_PATTERN_LENGTH} characters")
                    continue
                if _NESTED_QUANTIFIER.search(text):
                    errors.append(f"{rule_id}: nested quantifier is not allowed")
                    continue
                try:
                    re.compile(text)
                except re.error as exc:
                    errors.append(f"{rule_id}: invalid regex {text!r}: {exc}")
        return {
            "valid": not errors,
            "path": str(source),
            "rules": len(rules),
            "errors": errors,
        }

    def install(self, path: Path | str, name: str | None = None) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        validation = self.validate_file(source)
        if not validation["valid"]:
            raise RuleWorkbenchError("; ".join(validation["errors"]))
        incoming, _ = _read_document(source)
        incoming_ids = {str(rule.get("id") or "") for rule in incoming}
        existing_ids: set[str] = set()
        for existing_file in self._rule_files():
            try:
                existing, _ = _read_document(existing_file)
            except RuleWorkbenchError:
                continue
            existing_ids.update(str(rule.get("id") or "") for rule in existing)
        conflicts = sorted((incoming_ids & existing_ids) - {""})
        if conflicts:
            raise RuleWorkbenchError(
                f"rule id already exists: {', '.join(conflicts)}"
            )
        filename = str(name or source.name)
        if not filename.lower().endswith(".json"):
            filename += ".json"
        filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
        self.user_dir.mkdir(parents=True, exist_ok=True)
        destination = self.user_dir / filename
        temp = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        shutil.copyfile(source, temp)
        os.replace(temp, destination)
        return {
            "installed": True,
            "destination": str(destination),
            "rules": validation["rules"],
        }

    def _state(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_file.read_text(encoding="utf-8"))
            if value.get("version") == 1 and isinstance(value.get("disabled"), dict):
                return value
        except (OSError, json.JSONDecodeError):
            pass
        return {"version": 1, "disabled": {}}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_file.with_name(f".{self.state_file.name}.{uuid.uuid4().hex}.tmp")
        temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, self.state_file)

    def disable(self, rule_id: str, reason: str) -> dict[str, Any]:
        if not str(reason).strip():
            raise RuleWorkbenchError("disable reason is required")
        state = self._state()
        state["disabled"][rule_id] = {"reason": str(reason).strip(), "ts": _utc_now()}
        self._save_state(state)
        return {"rule_id": rule_id, "enabled": False, **state["disabled"][rule_id]}

    def enable(self, rule_id: str) -> dict[str, Any]:
        state = self._state()
        state["disabled"].pop(rule_id, None)
        self._save_state(state)
        return {"rule_id": rule_id, "enabled": True}

    def _rule_files(self, extra_files: list[Path] | None = None) -> list[Path]:
        files = sorted(_repo_rules().glob("*.json"))
        if self.user_dir.is_dir():
            files.extend(sorted(self.user_dir.glob("*.json")))
        files.extend(extra_files or [])
        return files

    def show(
        self, rule_id: str, extra_files: list[Path] | None = None
    ) -> dict[str, Any]:
        disabled = self._state()["disabled"]
        for path in self._rule_files(extra_files):
            try:
                rules, _ = _read_document(path)
            except RuleWorkbenchError:
                continue
            for rule in rules:
                if str(rule.get("id")) == rule_id:
                    return {
                        **rule,
                        "enabled": rule_id not in disabled,
                        "disabled": disabled.get(rule_id),
                        "source": str(path),
                    }
        raise RuleWorkbenchError(f"rule not found: {rule_id}")

    def conflicts(self) -> dict[str, Any]:
        locations: dict[str, list[str]] = {}
        invalid_files: list[str] = []
        for path in self._rule_files():
            validation = self.validate_file(path)
            if not validation["valid"]:
                invalid_files.append(str(path))
            try:
                rules, _ = _read_document(path)
            except RuleWorkbenchError:
                continue
            for rule in rules:
                rule_id = str(rule.get("id") or "")
                locations.setdefault(rule_id, []).append(str(path))
        duplicates = [
            {"rule_id": rule_id, "files": files}
            for rule_id, files in sorted(locations.items())
            if rule_id and len(files) > 1
        ]
        return {
            "conflicts": duplicates,
            "invalid_files": invalid_files,
            "clean": not duplicates and not invalid_files,
        }

    def summary(self) -> dict[str, int]:
        """Return bounded catalog health counts without exposing rule contents."""
        files = self._rule_files()
        total = sum(int(self.validate_file(path).get("rules") or 0) for path in files)
        disabled = len(self._state()["disabled"])
        integrity = self.conflicts()
        quarantined = (
            len(list(self.quarantine_dir.glob("*")))
            if self.quarantine_dir.is_dir()
            else 0
        )
        return {
            "total": total,
            "enabled": max(0, total - disabled),
            "disabled": disabled,
            "quarantined": quarantined,
            "conflicts": len(integrity["conflicts"]),
            "invalid_files": len(integrity["invalid_files"]),
        }

    def test_file(
        self, rule_file: Path | str, sample_file: Path | str, timeout: float = 3.0
    ) -> dict[str, Any]:
        source = Path(rule_file).expanduser().resolve()
        sample = Path(sample_file).expanduser().resolve()
        validation = self.validate_file(source)
        if not validation["valid"]:
            raise RuleWorkbenchError("; ".join(validation["errors"]))
        if not sample.is_file():
            raise RuleWorkbenchError(f"sample not found: {sample}")
        if sample.stat().st_size > MAX_SAMPLE_BYTES:
            raise RuleWorkbenchError("sample exceeds 5 MiB")
        worker = (
            "import json,re,sys;"
            "d=json.load(open(sys.argv[1],encoding='utf-8'));"
            "r=d.get('rules',[d]) if isinstance(d,dict) else d;"
            "t=open(sys.argv[2],encoding='utf-8',errors='ignore').read();"
            "h=[{'rule_id':x['id'],'name':x['name'],'severity':x['severity']} "
            "for x in r if any(re.search(str(p),t) for p in x['patterns'])];"
            "print(json.dumps({'matched':bool(h),'hits':h}))"
        )
        try:
            completed = subprocess.run(
                [sys.executable, "-c", worker, str(source), str(sample)],
                check=False,
                capture_output=True,
                text=True,
                timeout=max(0.1, min(float(timeout), 10.0)),
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuleWorkbenchError("rule test exceeded time limit") from exc
        if completed.returncode != 0:
            raise RuleWorkbenchError(
                f"isolated rule test failed: {completed.stderr.strip() or completed.returncode}"
            )
        result = json.loads(completed.stdout)
        return {
            **result,
            "rule_file": str(source),
            "sample": str(sample),
            "timeout_seconds": timeout,
        }

    def quarantine(self, path: Path | str) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise RuleWorkbenchError(f"rule file not found: {source}")
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        destination = self.quarantine_dir / (
            f"{_utc_now().replace(':', '').replace('+', '_')}-"
            f"{re.sub(r'[^A-Za-z0-9._-]', '_', source.name)}"
        )
        shutil.copyfile(source, destination)
        return {
            "quarantined": True,
            "source_retained": True,
            "destination": str(destination),
        }
