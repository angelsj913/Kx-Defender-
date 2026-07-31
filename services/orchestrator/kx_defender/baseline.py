"""Local host baselines and deterministic drift comparison."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

MAX_FILES = 5000
MAX_HASH_BYTES = 50 * 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_HASH_BYTES:
            return None
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _node_version() -> str:
    reported = os.environ.get("KX_NODE_VERSION")
    if reported:
        return reported
    configured = os.environ.get("KX_NODE")
    executable = (
        configured if configured and Path(configured).is_file()
        else shutil.which("node") or shutil.which("node.exe")
    )
    if not executable:
        return "unavailable"
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
            shell=False,
        )
        return result.stdout.strip() if result.returncode == 0 else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def collect_processes() -> list[dict[str, Any]]:
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
            rows = csv.reader(result.stdout.splitlines())
            return [
                {
                    "pid": int(row[1]),
                    "name": row[0],
                    "ppid": 0,
                    "path": "",
                }
                for row in rows
                if len(row) >= 2 and row[1].isdigit()
            ]
        except (OSError, subprocess.TimeoutExpired, csv.Error):
            return []

    processes: list[dict[str, Any]] = []
    proc = Path("/proc")
    if not proc.is_dir():
        return processes
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        try:
            name = (item / "comm").read_text(encoding="utf-8", errors="replace").strip()
            stat_values = (item / "stat").read_text(encoding="utf-8").split()
            ppid = int(stat_values[3])
            executable = os.readlink(item / "exe")
            processes.append(
                {"pid": int(item.name), "name": name, "ppid": ppid, "path": executable}
            )
        except (OSError, ValueError, IndexError):
            continue
    return processes


class BaselineManager:
    def __init__(
        self,
        home: Path | str | None = None,
        process_collector: Callable[[], list[dict[str, Any]]] = collect_processes,
    ):
        self.home = Path(
            home or os.environ.get("KX_HOME") or (Path.home() / ".kx-defender")
        ).expanduser().resolve()
        self.directory = self.home / "baselines"
        self.process_collector = process_collector

    @staticmethod
    def _name(name: str) -> str:
        value = str(name or "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
            raise ValueError("baseline name must use letters, numbers, dot, dash, or underscore")
        return value

    def _path(self, name: str) -> Path:
        return self.directory / f"{self._name(name)}.json"

    def _files(self, watched_path: Path | str | None) -> dict[str, dict[str, Any]]:
        if watched_path is None:
            return {}
        root = Path(watched_path).expanduser().resolve()
        if not root.exists():
            raise ValueError(f"watched path does not exist: {root}")
        if root.is_symlink():
            raise ValueError("watched path cannot be a symbolic link")
        candidates = [root] if root.is_file() else sorted(root.rglob("*"))
        files: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            if len(files) >= MAX_FILES:
                raise ValueError(f"watched path exceeds {MAX_FILES} files")
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                metadata = candidate.stat()
            except OSError:
                continue
            key = candidate.name if root.is_file() else candidate.relative_to(root).as_posix()
            files[key] = {
                "size": metadata.st_size,
                "mtime_ns": metadata.st_mtime_ns,
                "sha256": _sha256(candidate),
            }
        return files

    def _kx_hashes(self) -> dict[str, dict[str, Any]]:
        candidates: list[tuple[str, Path]] = [
            ("config.json", self.home / "config.json"),
            ("users.json", self.home / "users.json"),
            ("favorites.json", self.home / "favorites.json"),
            ("rules/state.json", self.home / "rules" / "kxsig" / "state.json"),
        ]
        rules = self.home / "rules" / "kxsig" / "user"
        if rules.is_dir():
            candidates.extend(
                (f"rules/user/{path.name}", path) for path in sorted(rules.glob("*.json"))
            )
        result: dict[str, dict[str, Any]] = {}
        for label, path in candidates:
            if path.is_file() and not path.is_symlink():
                result[label] = {"size": path.stat().st_size, "sha256": _sha256(path)}
        return result

    def _snapshot(self, watched_path: Path | str | None) -> dict[str, Any]:
        try:
            kx_version = importlib.metadata.version("kx-defender")
        except importlib.metadata.PackageNotFoundError:
            kx_version = "development"
        return {
            "system": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "node": _node_version(),
                "kx": kx_version,
            },
            "processes": sorted(
                self.process_collector(),
                key=lambda item: (str(item.get("name")), int(item.get("pid") or 0)),
            ),
            "kx_files": self._kx_hashes(),
            "files": self._files(watched_path),
        }

    def create(self, name: str, watched_path: Path | str | None = None) -> dict[str, Any]:
        target = self._path(name)
        if target.exists():
            raise ValueError(f"baseline already exists: {name}")
        document = {
            "version": 1,
            "name": self._name(name),
            "created_at": _utc_now(),
            "watched_path": str(Path(watched_path).expanduser().resolve())
            if watched_path is not None
            else None,
            "snapshot": self._snapshot(watched_path),
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        temp.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, target)
        return document

    def show(self, name: str) -> dict[str, Any]:
        target = self._path(name)
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"baseline not found: {name}") from exc
        if document.get("version") != 1:
            raise ValueError(f"unsupported baseline version: {document.get('version')}")
        return document

    def list(self) -> list[dict[str, Any]]:
        if not self.directory.is_dir():
            return []
        result = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                result.append(
                    {
                        "name": document["name"],
                        "created_at": document["created_at"],
                        "watched_path": document.get("watched_path"),
                    }
                )
            except (OSError, KeyError, json.JSONDecodeError):
                continue
        return sorted(result, key=lambda item: item["created_at"], reverse=True)

    @staticmethod
    def _process_key(process: dict[str, Any]) -> str:
        return f"{process.get('name', '')}|{process.get('path', '')}"

    def compare(self, name: str) -> dict[str, Any]:
        baseline = self.show(name)
        current = self._snapshot(baseline.get("watched_path"))
        before = baseline["snapshot"]
        old_files = before.get("files") or {}
        new_files = current.get("files") or {}
        old_processes = {
            self._process_key(item): item for item in before.get("processes") or []
        }
        new_processes = {
            self._process_key(item): item for item in current.get("processes") or []
        }
        old_kx = before.get("kx_files") or {}
        new_kx = current.get("kx_files") or {}
        result = {
            "name": baseline["name"],
            "compared_at": _utc_now(),
            "added": sorted(set(new_files) - set(old_files)),
            "removed": sorted(set(old_files) - set(new_files)),
            "modified": sorted(
                key for key in set(old_files) & set(new_files) if old_files[key] != new_files[key]
            ),
            "kx_added": sorted(set(new_kx) - set(old_kx)),
            "kx_removed": sorted(set(old_kx) - set(new_kx)),
            "kx_modified": sorted(
                key for key in set(old_kx) & set(new_kx) if old_kx[key] != new_kx[key]
            ),
            "process_new": [
                new_processes[key] for key in sorted(set(new_processes) - set(old_processes))
            ],
            "process_missing": [
                old_processes[key] for key in sorted(set(old_processes) - set(new_processes))
            ],
            "system_changed": before.get("system") != current.get("system"),
        }
        result["drift"] = any(
            result[key]
            for key in (
                "added", "removed", "modified", "kx_added", "kx_removed",
                "kx_modified", "process_new", "process_missing", "system_changed",
            )
        )
        return result

    def delete(self, name: str) -> dict[str, Any]:
        target = self._path(name)
        if not target.is_file():
            raise ValueError(f"baseline not found: {name}")
        target.unlink()
        return {"deleted": self._name(name), "path": str(target)}
