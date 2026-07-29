"""kx — KxLang (DEFCOM) front-end CLI (stdlib only)."""

from __future__ import annotations

import json
import sys

from kx_defender.helptext import is_help_token, render_global_help, render_verb_help
from kx_defender.kxlang import KxLangError, list_verbs, parse_argv
from kx_defender.orchestrator import Orchestrator


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _emit_help(args: list[str]) -> int:
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
        print(f"KxLang error: {exc}", file=sys.stderr)
        return 2
    print(text, end="")
    return 0


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    if (
        not args
        or is_help_token(args[0])
        or (len(args) >= 2 and is_help_token(args[1]))
        or args[0].lower() == "help"
    ):
        raise SystemExit(_emit_help(args))

    head = args[0].lower()
    if head == "lexicon":
        _print_json({"language": "KxLang", "codename": "DEFCOM", "verbs": list_verbs()})
        return

    if head == "serve":
        host = "127.0.0.1"
        port = 8787
        i = 1
        while i < len(args):
            if args[i] == "--bind" and i + 1 < len(args):
                bind = args[i + 1]
                if ":" in bind:
                    host, port_s = bind.rsplit(":", 1)
                    port = int(port_s)
                else:
                    host = bind
                i += 2
                continue
            if args[i] == "--port" and i + 1 < len(args):
                port = int(args[i + 1])
                i += 2
                continue
            print(f"KxLang error: unknown serve flag {args[i]!r}", file=sys.stderr)
            raise SystemExit(2)
        from kx_defender.api import serve

        serve(host=host, port=port)
        return

    try:
        cmd = parse_argv(args)
    except KxLangError as exc:
        print(f"KxLang error: {exc}", file=sys.stderr)
        print("Try: kx /h", file=sys.stderr)
        raise SystemExit(2) from exc

    orch = Orchestrator()
    try:
        result = orch.run(cmd.module, cmd.params)
    except KeyError as exc:
        print(f"KxLang error: {exc}", file=sys.stderr)
        print("Try: kx /h", file=sys.stderr)
        raise SystemExit(2) from exc

    payload = result.to_dict()
    payload["kxlang"] = cmd.to_dict()
    _print_json(payload)
    if result.status in {"denied", "error"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
