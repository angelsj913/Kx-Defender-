"""kx — KxLang (DEFCOM) front-end CLI."""

from __future__ import annotations

import json
import sys

import click

from kx_defender.helptext import is_help_token, render_global_help, render_verb_help
from kx_defender.kxlang import KxLangError, list_verbs, parse_argv
from kx_defender.orchestrator import Orchestrator


def _print_json(data: object) -> None:
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))


def _emit_help(args: list[str]) -> int:
    """Render help for `kx /h`, `kx /h <verb>`, `kx <verb> /h`, etc."""
    # Forms:
    #   /h
    #   /h <verb>
    #   <verb> /h
    #   help [/h] [<verb>]
    tokens = [a for a in args if a]
    verb = None

    if tokens and is_help_token(tokens[0]):
        if len(tokens) >= 2 and not is_help_token(tokens[1]):
            verb = tokens[1]
    elif len(tokens) >= 2 and is_help_token(tokens[1]):
        verb = tokens[0]
    elif tokens and tokens[0].lower() == "help":
        if len(tokens) >= 2 and not is_help_token(tokens[1]):
            verb = tokens[1]

    try:
        text = render_verb_help(verb) if verb else render_global_help()
    except ValueError as exc:
        click.echo(f"KxLang error: {exc}", err=True)
        return 2
    click.echo(text, nl=False)
    return 0


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    # Global / positional help: kx /h, kx -h, kx help, kx roast /h, kx /h roast
    if (
        not args
        or is_help_token(args[0])
        or (len(args) >= 2 and is_help_token(args[1]))
        or args[0].lower() == "help"
    ):
        code = _emit_help(args)
        sys.exit(code)

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

    try:
        cmd = parse_argv(args)
    except KxLangError as exc:
        click.echo(f"KxLang error: {exc}", err=True)
        click.echo("Try: kx /h", err=True)
        sys.exit(2)

    orch = Orchestrator()
    try:
        result = orch.run(cmd.module, cmd.params)
    except KeyError as exc:
        click.echo(f"KxLang error: {exc}", err=True)
        click.echo("Try: kx /h", err=True)
        sys.exit(2)

    payload = result.to_dict()
    payload["kxlang"] = cmd.to_dict()
    _print_json(payload)
    if result.status in {"denied", "error"}:
        sys.exit(2)


if __name__ == "__main__":
    main()
