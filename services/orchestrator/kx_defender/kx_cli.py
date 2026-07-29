"""kx — KxLang (DEFCOM) front-end CLI."""

from __future__ import annotations

import json
import sys

import click

from kx_defender.kxlang import KxLangError, list_verbs, load_lexicon, parse_argv
from kx_defender.orchestrator import Orchestrator


def _print_json(data: object) -> None:
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        click.echo(
            "KxLang/DEFCOM — Kx-Defender command language\n"
            "usage: kx <VERB> <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]\n"
            "meta:  kx lexicon | kx help [verb]\n"
            "docs:  docs/kxlang.md"
        )
        sys.exit(0)

    head = args[0].lower()
    if head == "lexicon":
        _print_json(
            {
                "language": "KxLang",
                "codename": "DEFCOM",
                "verbs": list_verbs(),
            }
        )
        return

    if head == "help":
        lex = load_lexicon()
        if len(args) == 1:
            _print_json({"verbs": sorted(lex.get("verbs", {})), "doc": "docs/kxlang.md"})
            return
        verb = args[1].lower()
        meta = lex.get("verbs", {}).get(verb)
        if not meta:
            raise SystemExit(f"unknown verb: {verb}")
        _print_json({"verb": verb, **meta})
        return

    try:
        cmd = parse_argv(args)
    except KxLangError as exc:
        click.echo(f"KxLang error: {exc}", err=True)
        sys.exit(2)

    orch = Orchestrator()
    try:
        result = orch.run(cmd.module, cmd.params)
    except KeyError as exc:
        click.echo(f"KxLang error: {exc}", err=True)
        sys.exit(2)

    payload = result.to_dict()
    payload["kxlang"] = cmd.to_dict()
    _print_json(payload)
    if result.status in {"denied", "error"}:
        sys.exit(2)


if __name__ == "__main__":
    main()
