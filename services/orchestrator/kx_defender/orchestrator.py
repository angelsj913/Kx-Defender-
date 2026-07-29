"""Run modules through auth + persistence."""

from __future__ import annotations

from typing import Any

from kx_defender.auth import AuthorizationError
from kx_defender.registry import build_registry
from kx_defender.result import ModuleResult
from kx_defender.store import RunStore


class Orchestrator:
    def __init__(self, store: RunStore | None = None) -> None:
        self.registry = build_registry()
        self.store = store or RunStore()

    def list_modules(
        self,
        category: str | None = None,
        family: str | None = None,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        items = [m.describe() for m in self.registry.values()]
        if category:
            items = [i for i in items if i.get("category") == category]
        if family:
            items = [i for i in items if i.get("family") == family]
        if prefix:
            items = [i for i in items if i.get("name", "").startswith(prefix)]
        return sorted(items, key=lambda i: i.get("name", ""))

    def families(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for mod in self.registry.values():
            family = getattr(mod, "family", None) or (
                "legacy_attack" if getattr(mod, "category", "") == "attack" else "legacy_defense"
            )
            counts[family] = counts.get(family, 0) + 1
        return dict(sorted(counts.items()))

    def run(self, module_name: str, params: dict[str, Any]) -> ModuleResult:
        module = self.registry.get(module_name)
        if module is None:
            raise KeyError(f"unknown module: {module_name}")
        try:
            result = module.execute(params)
        except AuthorizationError as exc:
            result = ModuleResult(
                module=module_name,
                status="denied",
                mode=str(params.get("mode", "simulate")),
                authorized_scope=str(params.get("authorized_scope", "")),
                errors=[str(exc)],
            ).finish("denied")
        self.store.save(result)
        return result

    def get_result(self, run_id: str) -> ModuleResult | None:
        return self.store.get(run_id)

    def list_results(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.list_runs(limit=limit)
