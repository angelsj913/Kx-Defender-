"""Portable, integrity-checked Kx evidence bundles (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from kx_defender.alert_store import AlertStore
from kx_defender.store import RunStore

BUNDLE_VERSION = 1
MAX_FILES = 1000
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
_SECRET_KEY = re.compile(
    r"(password|passwd|token|secret|cookie|authorization|private[_ -]?key|api[_ -]?key)",
    re.IGNORECASE,
)
_USER_KEY = re.compile(r"^(user(name)?|actor|account)$", re.IGNORECASE)
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_WINDOWS_HOME = re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\/\s]+")
_POSIX_HOME = re.compile(r"/(?:home|Users)/[^/\s]+")
_AUTHORIZATION = re.compile(r"(?i)(authorization\s*:\s*)[^\s,;]+(?:\s+[^\s,;]+)?")
_INLINE_SECRET = re.compile(
    r"(?i)\b(password|passwd|token|secret|cookie|api[_ -]?key)\b(\s*[:=]\s*)[^\s,;]+"
)
_TEXT_ARTIFACTS = {".txt", ".json", ".jsonl", ".log", ".md", ".html", ".csv", ".xml"}


class EvidenceError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return cleaned[:100] or "item"


def _redact(value: Any, profile: str, stats: dict[str, int], key: str = "") -> Any:
    if _SECRET_KEY.search(key):
        stats["secret_fields"] += 1
        return "<redacted>"
    if profile == "strict" and _USER_KEY.search(key):
        stats["identity_fields"] += 1
        return "<user>"
    if isinstance(value, dict):
        return {
            str(item_key): _redact(item_value, profile, stats, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, profile, stats, key) for item in value]
    if isinstance(value, tuple):
        return [_redact(item, profile, stats, key) for item in value]
    if not isinstance(value, str):
        return value

    result, auth_count = _AUTHORIZATION.subn(r"\1<redacted>", value)
    stats["secret_values"] += auth_count
    result, inline_count = _INLINE_SECRET.subn(r"\1\2<redacted>", result)
    stats["secret_values"] += inline_count
    if "-----BEGIN " in result and "PRIVATE KEY-----" in result:
        stats["secret_values"] += 1
        result = "<redacted>"
    if profile == "strict":
        result, windows_count = _WINDOWS_HOME.subn("<user-home>", result)
        result, posix_count = _POSIX_HOME.subn("<user-home>", result)
        result, ip_count = _IPV4.subn("<ip>", result)
        stats["paths"] += windows_count + posix_count
        stats["ip_addresses"] += ip_count
    return result


def _source_payload(
    source_type: str,
    source_id: str,
    alert_store: AlertStore | None,
    run_store: RunStore | None,
) -> tuple[dict[str, bytes], list[str]]:
    entries: dict[str, bytes] = {}
    exclusions: list[str] = []
    if source_type == "case":
        store = alert_store or AlertStore()
        case = store.get_case(source_id)
        alerts = case.pop("alerts", [])
        entries[f"cases/{_safe_component(source_id)}.json"] = _json_bytes(case)
        for alert in alerts:
            alert_id = str(alert.get("alert_id") or "alert")
            entries[f"alerts/{_safe_component(alert_id)}.json"] = _json_bytes(alert)
        return entries, exclusions
    if source_type == "run":
        store = run_store or RunStore()
        run = store.get(source_id)
        if run is None:
            raise EvidenceError(f"run not found: {source_id}")
        payload = run.to_dict()
        artifacts = payload.get("artifacts") or {}
        for name, artifact in artifacts.items():
            if not isinstance(artifact, str):
                continue
            candidate = Path(artifact).expanduser()
            if not candidate.is_file():
                continue
            try:
                size = candidate.stat().st_size
            except OSError:
                exclusions.append(f"artifact unreadable: {name}")
                continue
            if size > 20 * 1024 * 1024:
                exclusions.append(f"artifact over 20 MiB: {name}")
                continue
            if candidate.suffix.lower() not in _TEXT_ARTIFACTS:
                exclusions.append(f"binary artifact excluded from redacted bundle: {name}")
                continue
            entry_name = (
                f"artifacts/{_safe_component(name)}-"
                f"{hashlib.sha256(str(candidate).encode()).hexdigest()[:8]}-"
                f"{_safe_component(candidate.name)}"
            )
            try:
                entries[entry_name] = candidate.read_bytes()
            except OSError:
                exclusions.append(f"artifact unreadable: {name}")
        entries[f"runs/{_safe_component(source_id)}.json"] = _json_bytes(payload)
        return entries, exclusions
    raise EvidenceError("source type must be run or case")


def export_bundle(
    source_type: str,
    source_id: str,
    destination: Path | str,
    redact: str = "standard",
    *,
    alert_store: AlertStore | None = None,
    run_store: RunStore | None = None,
) -> dict[str, Any]:
    if redact not in {"standard", "strict"}:
        raise EvidenceError("redaction profile must be standard or strict")
    target = Path(destination).expanduser().resolve()
    if target.exists():
        raise EvidenceError(f"destination already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    raw_entries, exclusions = _source_payload(
        source_type, source_id, alert_store, run_store
    )
    stats = {
        "secret_fields": 0,
        "secret_values": 0,
        "identity_fields": 0,
        "paths": 0,
        "ip_addresses": 0,
    }
    entries: dict[str, bytes] = {}
    for name, raw in raw_entries.items():
        if name.endswith(".json"):
            value = json.loads(raw.decode("utf-8"))
            entries[name] = _json_bytes(_redact(value, redact, stats))
        elif name.startswith("artifacts/"):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                exclusions.append(f"non-UTF-8 artifact excluded: {name}")
                continue
            entries[name] = str(_redact(text, redact, stats)).encode("utf-8")
        else:
            entries[name] = raw

    bundle_id = f"KXEV-{uuid.uuid4().hex.upper()}"
    manifest = {
        "bundle_version": BUNDLE_VERSION,
        "bundle_id": bundle_id,
        "created_at": _utc_now(),
        "source": {"type": source_type, "id": source_id},
        "redaction": {"profile": redact, "counts": stats},
        "exclusions": exclusions,
    }
    entries["manifest.json"] = _json_bytes(manifest)
    hashes = [
        f"{hashlib.sha256(content).hexdigest()}  {name}"
        for name, content in sorted(entries.items())
    ]
    entries["hashes.sha256"] = ("\n".join(hashes) + "\n").encode("utf-8")

    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(entries.items()):
                archive.writestr(name, content)
        os.replace(temp, target)
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return {
        "bundle_id": bundle_id,
        "path": str(target),
        "files": len(entries),
        "redaction": manifest["redaction"],
    }


def _unsafe_name(name: str) -> bool:
    if "\\" in name or "\x00" in name:
        return True
    path = PurePosixPath(name)
    return path.is_absolute() or not name or any(part in {"", ".", ".."} for part in path.parts)


def _validate_archive(archive: zipfile.ZipFile) -> list[str]:
    errors: list[str] = []
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(infos) > MAX_FILES:
        errors.append(f"too many files: {len(infos)}")
    if len(names) != len(set(names)):
        errors.append("duplicate archive path")
    if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
        errors.append("uncompressed bundle size exceeds limit")
    for info in infos:
        if _unsafe_name(info.filename):
            errors.append(f"unsafe archive path: {info.filename}")
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            errors.append(f"symbolic links are not allowed: {info.filename}")
        if info.is_dir():
            errors.append(f"directory entries are not allowed: {info.filename}")
    return errors


def verify_bundle(path: Path | str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    errors: list[str] = []
    try:
        with zipfile.ZipFile(source, "r") as archive:
            errors.extend(_validate_archive(archive))
            names = set(archive.namelist())
            if "hashes.sha256" not in names:
                errors.append("hashes.sha256 is missing")
                expected: dict[str, str] = {}
            else:
                expected = {}
                for line in archive.read("hashes.sha256").decode("utf-8").splitlines():
                    match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
                    if not match:
                        errors.append("invalid hashes.sha256 line")
                        continue
                    digest, name = match.groups()
                    if name in expected:
                        errors.append(f"duplicate hash entry: {name}")
                    expected[name] = digest
                unhashed = names - set(expected) - {"hashes.sha256"}
                missing = set(expected) - names
                if unhashed:
                    errors.append(f"unhashed entries: {', '.join(sorted(unhashed))}")
                if missing:
                    errors.append(f"missing entries: {', '.join(sorted(missing))}")
                for name, digest in expected.items():
                    if name not in names:
                        continue
                    actual = hashlib.sha256(archive.read(name)).hexdigest()
                    if actual != digest:
                        errors.append(f"hash mismatch: {name}")
            if "manifest.json" not in names:
                errors.append("manifest.json is missing")
            else:
                try:
                    manifest = json.loads(archive.read("manifest.json"))
                    if manifest.get("bundle_version") != BUNDLE_VERSION:
                        errors.append("unsupported bundle version")
                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                    errors.append("invalid manifest.json")
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        errors.append(str(exc))
    return {"valid": not errors, "path": str(source), "errors": errors}


def inspect_bundle(path: Path | str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    verification = verify_bundle(source)
    if not verification["valid"]:
        raise EvidenceError(
            "bundle verification failed: " + "; ".join(verification["errors"])
        )
    with zipfile.ZipFile(source, "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        files = [
            {"path": info.filename, "size": info.file_size}
            for info in archive.infolist()
        ]
    return {"manifest": manifest, "files": files, "verification": verification}


def import_bundle(path: Path | str, root: Path | str | None = None) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    verification = verify_bundle(source)
    if not verification["valid"]:
        raise EvidenceError(
            "bundle verification failed: " + "; ".join(verification["errors"])
        )
    kx_home = Path(os.environ.get("KX_HOME") or (Path.home() / ".kx-defender"))
    base = Path(root or (kx_home / "evidence" / "imported"))
    base = base.expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        folder = _safe_component(str(manifest.get("bundle_id") or source.stem))
        destination = base / folder
        if destination.exists():
            raise EvidenceError(f"bundle is already imported: {destination}")
        staging = base / f".staging-{uuid.uuid4().hex}"
        staging.mkdir()
        try:
            for info in archive.infolist():
                target = staging.joinpath(*PurePosixPath(info.filename).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source_stream, target.open("wb") as output:
                    shutil.copyfileobj(source_stream, output)
            os.replace(staging, destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    for item in sorted(destination.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        try:
            item.chmod(0o555 if item.is_dir() else 0o444)
        except OSError:
            pass
    try:
        destination.chmod(0o555)
    except OSError:
        pass
    return {
        "bundle_id": manifest.get("bundle_id"),
        "path": str(destination),
        "read_only": True,
    }
