"""kxctl — agent-friendly CLI for Kx-Defender modules."""

from __future__ import annotations

import json
import sys
from typing import Any

import click

from kx_defender.orchestrator import Orchestrator


def _print_json(data: Any) -> None:
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _collect_params(
    authorized_scope: str,
    mode: str,
    target: str | None,
    domain: str | None,
    url: str | None,
    host: str | None,
    essid: str | None,
    port: int | None,
    action: str | None,
    engagement_file: str | None,
    param: tuple[str, ...],
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "authorized_scope": authorized_scope.lower(),
        "mode": mode.lower(),
    }
    for key, value in {
        "target": target,
        "domain": domain,
        "url": url,
        "host": host,
        "essid": essid,
        "port": port,
        "action": action,
        "engagement_file": engagement_file,
    }.items():
        if value is not None:
            params[key] = value
    for item in param:
        if "=" not in item:
            raise click.ClickException(f"invalid --param {item!r}, expected key=value")
        k, v = item.split("=", 1)
        params[k] = v
    return params


def _run_module(module_name: str, params: dict[str, Any]) -> None:
    orch = Orchestrator()
    try:
        result = orch.run(module_name, params)
    except KeyError as exc:
        raise click.ClickException(str(exc)) from exc
    _print_json(result.to_dict())
    if result.status in {"denied", "error"}:
        sys.exit(2)


@click.group()
@click.version_option(package_name="kx-defender")
def main() -> None:
    """Kx-Defender control plane (lab-authorized modules, no SaaS API keys)."""


@main.group()
def modules() -> None:
    """Module discovery."""


@modules.command("list")
@click.option("--category", type=click.Choice(["attack", "defense"], case_sensitive=False))
@click.option("--family", default=None, help="Catalog family (detecting, analyzing, attack_named, ...)")
@click.option("--prefix", default=None, help="Filter by skill name prefix")
@click.option("--names-only", is_flag=True, help="Print only module names")
def modules_list(category: str | None, family: str | None, prefix: str | None, names_only: bool) -> None:
    orch = Orchestrator()
    items = orch.list_modules(
        category=category.lower() if category else None,
        family=family,
        prefix=prefix,
    )
    if names_only:
        _print_json([i["name"] for i in items])
    else:
        _print_json(items)


@modules.command("families")
def modules_families() -> None:
    orch = Orchestrator()
    _print_json(orch.families())


@main.group()
def skill() -> None:
    """Run full catalog skill names (Anthropic-Cybersecurity style)."""


@skill.command("run")
@click.argument("skill_name")
@click.option(
    "--authorized-scope",
    type=click.Choice(["lab", "owned", "engagement"], case_sensitive=False),
    required=True,
)
@click.option("--mode", type=click.Choice(["simulate", "execute"], case_sensitive=False), default="simulate")
@click.option("--target", default=None)
@click.option("--domain", default=None)
@click.option("--url", default=None)
@click.option("--host", default=None)
@click.option("--essid", default=None)
@click.option("--port", default=None, type=int)
@click.option("--action", default=None)
@click.option("--engagement-file", default=None, type=click.Path())
@click.option("--param", multiple=True, help="Extra key=value params")
def skill_run(
    skill_name: str,
    authorized_scope: str,
    mode: str,
    target: str | None,
    domain: str | None,
    url: str | None,
    host: str | None,
    essid: str | None,
    port: int | None,
    action: str | None,
    engagement_file: str | None,
    param: tuple[str, ...],
) -> None:
    params = _collect_params(
        authorized_scope, mode, target, domain, url, host, essid, port, action, engagement_file, param
    )
    _run_module(skill_name, params)


@main.group()
def attack() -> None:
    """Run attack modules (short names or full skill names)."""


@attack.command("run")
@click.argument("module_name")
@click.option(
    "--authorized-scope",
    type=click.Choice(["lab", "owned", "engagement"], case_sensitive=False),
    required=True,
)
@click.option("--mode", type=click.Choice(["simulate", "execute"], case_sensitive=False), default="simulate")
@click.option("--target", default=None)
@click.option("--domain", default=None)
@click.option("--url", default=None)
@click.option("--host", default=None)
@click.option("--essid", default=None)
@click.option("--port", default=None, type=int)
@click.option("--action", default=None)
@click.option("--engagement-file", default=None, type=click.Path())
@click.option("--param", multiple=True, help="Extra key=value params")
def attack_run(
    module_name: str,
    authorized_scope: str,
    mode: str,
    target: str | None,
    domain: str | None,
    url: str | None,
    host: str | None,
    essid: str | None,
    port: int | None,
    action: str | None,
    engagement_file: str | None,
    param: tuple[str, ...],
) -> None:
    params = _collect_params(
        authorized_scope, mode, target, domain, url, host, essid, port, action, engagement_file, param
    )
    _run_module(module_name, params)


@main.group()
def defense() -> None:
    """Run defense modules (detecting/analyzing/auditing/securing/triaging/compliance/building)."""


@defense.command("run")
@click.argument("module_name")
@click.option(
    "--authorized-scope",
    type=click.Choice(["lab", "owned", "engagement"], case_sensitive=False),
    required=True,
)
@click.option("--mode", type=click.Choice(["simulate", "execute"], case_sensitive=False), default="simulate")
@click.option("--target", default=None)
@click.option("--url", default=None)
@click.option("--param", multiple=True, help="Extra key=value params")
def defense_run(
    module_name: str,
    authorized_scope: str,
    mode: str,
    target: str | None,
    url: str | None,
    param: tuple[str, ...],
) -> None:
    params = _collect_params(
        authorized_scope, mode, target, None, url, None, None, None, None, None, param
    )
    _run_module(module_name, params)


@main.group()
def result() -> None:
    """Inspect persisted runs."""


@result.command("show")
@click.argument("run_id")
def result_show(run_id: str) -> None:
    orch = Orchestrator()
    item = orch.get_result(run_id)
    if item is None:
        raise click.ClickException(f"run not found: {run_id}")
    _print_json(item.to_dict())


@result.command("list")
@click.option("--limit", default=20, show_default=True)
def result_list(limit: int) -> None:
    orch = Orchestrator()
    _print_json(orch.list_results(limit=limit))


if __name__ == "__main__":
    main()
