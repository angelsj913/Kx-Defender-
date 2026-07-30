"""Common module contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from kx_defender.auth import validate_params
from kx_defender.result import ModuleResult


class BaseModule(ABC):
    name: str = "base"
    category: str = "attack"
    description: str = ""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "modes": ["simulate", "execute"],
            "required": ["authorized_scope"],
        }

    def validate(self, params: dict[str, Any]) -> dict[str, Any]:
        return validate_params(params)

    @abstractmethod
    def run(self, params: dict[str, Any]) -> ModuleResult:
        raise NotImplementedError

    def execute(self, params: dict[str, Any]) -> ModuleResult:
        cleaned = self.validate(params)
        result = self.run(cleaned)
        if result.finished_at is None:
            result.finish()
        return result


class AttackModule(BaseModule):
    """Base class for offensive modules (kerberoasting, NTLM relay, etc.)."""
    category: str = "attack"


class DefenseModule(BaseModule):
    """Base class for defensive modules (watch procs, sig scan, kill pid, etc.).

    Semantically identical to ``AttackModule`` but subclasses no longer need to
    override ``category = "defense"`` on every module.
    """
    category: str = "defense"
