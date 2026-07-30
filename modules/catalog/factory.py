"""Build AttackModule instances from fixtures/catalog/skills.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kx_defender.base import AttackModule
from kx_defender.result import ModuleResult
from modules.catalog.handlers import HANDLERS

CATALOG_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "catalog" / "skills.json"


class CatalogSkillModule(AttackModule):
    def __init__(self, name: str, family: str, category: str, description: str | None = None) -> None:
        self.name = name
        self.family = family
        self.category = category
        self.description = description or f"Catalog skill '{name}' ({family})"

    def describe(self) -> dict[str, Any]:
        data = super().describe()
        data["family"] = self.family
        return data

    def run(self, params: dict[str, Any]) -> ModuleResult:
        handler = HANDLERS.get(self.family)
        if handler is None:
            result = ModuleResult(
                module=self.name,
                status="error",
                mode=params.get("mode", "simulate"),
                authorized_scope=params.get("authorized_scope", ""),
                errors=[f"unknown family: {self.family}"],
            )
            return result.finish("error")
        return handler(self.name, params)


def load_catalog() -> list[dict[str, str]]:
    if not CATALOG_PATH.is_file():
        return []
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return list(data.get("skills", []))


def build_catalog_modules() -> list[CatalogSkillModule]:
    modules: list[CatalogSkillModule] = []
    for item in load_catalog():
        modules.append(
            CatalogSkillModule(
                name=item["name"],
                family=item["family"],
                category=item["category"],
            )
        )
    return modules
