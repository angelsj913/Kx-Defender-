"""Structured module run results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Finding:
    title: str
    severity: str = "info"
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModuleResult:
    module: str
    status: str
    mode: str
    authorized_scope: str
    findings: list[Finding] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str | None = None) -> "ModuleResult":
        if status is not None:
            self.status = status
        self.finished_at = utc_now_iso()
        return self

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [f.to_dict() if isinstance(f, Finding) else f for f in self.findings]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModuleResult":
        findings = [Finding(**f) if isinstance(f, dict) else f for f in data.get("findings", [])]
        return cls(
            module=data["module"],
            status=data["status"],
            mode=data["mode"],
            authorized_scope=data["authorized_scope"],
            findings=findings,
            artifacts=data.get("artifacts", {}),
            errors=data.get("errors", []),
            run_id=data.get("run_id", str(uuid4())),
            started_at=data.get("started_at", utc_now_iso()),
            finished_at=data.get("finished_at"),
            meta=data.get("meta", {}),
        )
