"""kxctl — low-level module CLI (stdlib argparse)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from kx_defender.orchestrator import Orchestrator


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _params_from_ns(ns: argparse.Namespace) -> dict[str, Any]:
    params: dict[str, Any] = {
        "authorized_scope": ns.authorized_scope.lower(),
        "mode": ns.mode.lower(),
    }
    for key in ("target", "domain", "url", "host", "essid", "action", "engagement_file"):
        value = getattr(ns, key, None)
        if value is not None:
            params[key] = value
    if getattr(ns, "port", None) is not None:
        params["port"] = ns.port
    for item in getattr(ns, "param", []) or []:
        if "=" not in item:
            raise SystemExit(f"invalid --param {item!r}, expected key=value")
        k, v = item.split("=", 1)
        params[k] = v
    return params


def _run(module_name: str, params: dict[str, Any]) -> None:
    orch = Orchestrator()
    try:
        result = orch.run(module_name, params)
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    _print_json(result.to_dict())
    if result.status in {"denied", "error"}:
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kxctl", description="Kx-Defender low-level module control")
    sub = p.add_subparsers(dest="cmd", required=True)

    modules = sub.add_parser("modules", help="Module discovery")
    modules_sub = modules.add_subparsers(dest="modules_cmd", required=True)
    m_list = modules_sub.add_parser("list", help="List modules")
    m_list.add_argument("--category", choices=["attack", "defense"])
    m_list.add_argument("--family")
    m_list.add_argument("--prefix")
    m_list.add_argument("--names-only", action="store_true")
    modules_sub.add_parser("families", help="Count modules by family")

    skill = sub.add_parser("skill", help="Run catalog skill name")
    skill_sub = skill.add_subparsers(dest="skill_cmd", required=True)
    s_run = skill_sub.add_parser("run")
    _add_run_flags(s_run, require_scope=True)
    s_run.add_argument("skill_name")

    attack = sub.add_parser("attack", help="Run attack module")
    attack_sub = attack.add_subparsers(dest="attack_cmd", required=True)
    a_run = attack_sub.add_parser("run")
    _add_run_flags(a_run, require_scope=True)
    a_run.add_argument("module_name")

    defense = sub.add_parser("defense", help="Run defense module")
    defense_sub = defense.add_subparsers(dest="defense_cmd", required=True)
    d_run = defense_sub.add_parser("run")
    d_run.add_argument("module_name")
    d_run.add_argument("--authorized-scope", required=True, choices=["lab", "owned", "engagement"])
    d_run.add_argument("--mode", default="simulate", choices=["simulate", "execute"])
    d_run.add_argument("--target")
    d_run.add_argument("--url")
    d_run.add_argument("--param", action="append", default=[])

    result = sub.add_parser("result", help="Inspect runs")
    result_sub = result.add_subparsers(dest="result_cmd", required=True)
    r_show = result_sub.add_parser("show")
    r_show.add_argument("run_id")
    r_list = result_sub.add_parser("list")
    r_list.add_argument("--limit", type=int, default=20)
    return p


def _add_run_flags(parser: argparse.ArgumentParser, require_scope: bool) -> None:
    parser.add_argument("--authorized-scope", required=require_scope, choices=["lab", "owned", "engagement"])
    parser.add_argument("--mode", default="simulate", choices=["simulate", "execute"])
    parser.add_argument("--target")
    parser.add_argument("--domain")
    parser.add_argument("--url")
    parser.add_argument("--host")
    parser.add_argument("--essid")
    parser.add_argument("--port", type=int)
    parser.add_argument("--action")
    parser.add_argument("--engagement-file")
    parser.add_argument("--param", action="append", default=[])


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    ns = parser.parse_args(argv)
    orch = Orchestrator()

    if ns.cmd == "modules":
        if ns.modules_cmd == "list":
            items = orch.list_modules(category=ns.category, family=ns.family, prefix=ns.prefix)
            _print_json([i["name"] for i in items] if ns.names_only else items)
            return
        if ns.modules_cmd == "families":
            _print_json(orch.families())
            return

    if ns.cmd == "skill" and ns.skill_cmd == "run":
        _run(ns.skill_name, _params_from_ns(ns))
        return
    if ns.cmd == "attack" and ns.attack_cmd == "run":
        _run(ns.module_name, _params_from_ns(ns))
        return
    if ns.cmd == "defense" and ns.defense_cmd == "run":
        _run(ns.module_name, _params_from_ns(ns))
        return
    if ns.cmd == "result":
        if ns.result_cmd == "show":
            item = orch.get_result(ns.run_id)
            if item is None:
                raise SystemExit(f"run not found: {ns.run_id}")
            _print_json(item.to_dict())
            return
        if ns.result_cmd == "list":
            _print_json(orch.list_results(limit=ns.limit))
            return

    parser.error("unknown command")


if __name__ == "__main__":
    main()
