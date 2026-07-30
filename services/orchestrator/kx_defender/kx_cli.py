"""kx — KxLang (DEFCOM) front-end CLI (stdlib only)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _force_utf8_stdio() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


_force_utf8_stdio()

from kx_defender.helptext import is_help_token, render_global_help, render_verb_help
from kx_defender.i18n import get_lang, set_lang, t
from kx_defender.kxlang import KxLangError, list_verbs, parse_argv
from kx_defender.orchestrator import Orchestrator
from kx_defender.paramform import (
    augment_argv,
    collect_from_prompts,
    parse_command_form,
    schema_for,
)
from kx_defender.render import render_result_text


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _print_next() -> None:
    print("next: kx /h", file=sys.stderr)


def _repo_root() -> Path:
    # services/orchestrator/kx_defender/kx_cli.py → repo root
    return Path(__file__).resolve().parents[3]


def _find_update_js() -> Path | None:
    home = Path.home() / ".kx-defender" / "app" / "scripts" / "kx-update.js"
    if home.is_file():
        return home
    local = _repo_root() / "scripts" / "kx-update.js"
    if local.is_file():
        return local
    return None


def _find_entry_js() -> Path | None:
    home = Path.home() / ".kx-defender" / "app" / "scripts" / "npx-entry.js"
    if home.is_file():
        return home
    local = _repo_root() / "scripts" / "npx-entry.js"
    if local.is_file():
        return local
    return None


def _node_bin() -> str:
    return shutil.which("node") or "node"


def _run_update() -> int:
    """kx update — refresh install without full reinstall (via Node updater)."""
    update_js = _find_update_js()
    node = _node_bin()
    if update_js is None:
        print("[Kx] Running: npx -y --prefer-online angelsj913/Kx-Defender- update", flush=True)
        res = subprocess.run(
            ["npx", "-y", "--prefer-online", "angelsj913/Kx-Defender-", "update"],
            check=False,
        )
        return int(res.returncode or 0)
    print(f"[Kx] Updating via {update_js} ...", flush=True)
    res = subprocess.run([node, str(update_js)], check=False)
    return int(res.returncode or 0)


def _run_hud() -> int:
    entry = _find_entry_js()
    node = _node_bin()
    if entry is None:
        print("[Kx] Starting via npx ...", flush=True)
        res = subprocess.run(
            ["npx", "-y", "--prefer-online", "angelsj913/Kx-Defender-"],
            check=False,
        )
        return int(res.returncode or 0)
    res = subprocess.run([node, str(entry)], check=False)
    return int(res.returncode or 0)


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


def _emit_lang(args: list[str]) -> int:
    rest = args[1:]
    if not rest:
        lang = get_lang()
        label = "한국어" if lang == "ko" else "English"
        print(t(f"language: {lang} ({label})", f"언어: {lang} ({label})"))
        print(t("set: kx lang en | kx lang ko", "변경: kx lang en | kx lang ko"))
        return 0
    try:
        lang = set_lang(rest[0])
    except ValueError as exc:
        print(f"KxLang error: {exc}", file=sys.stderr)
        return 2
    label = "한국어" if lang == "ko" else "English"
    print(t(f"language set to {lang} ({label})", f"언어가 {lang} ({label})(으)로 설정되었습니다."))
    return 0


def _emit_form(args: list[str]) -> int:
    """`kx form <verb> [obj]` — print parameter schema as JSON."""
    rest = args[1:]
    if not rest:
        print("usage: kx form <verb> [object]", file=sys.stderr)
        return 2
    verb = rest[0]
    obj = rest[1] if len(rest) > 1 else ""
    fields, key = schema_for(verb, obj, lexicon_verbs=list_verbs())
    _print_json({"verb": verb, "object": obj, "schema_key": key, "fields": fields})
    return 0


def _emit_suggest(args: list[str]) -> int:
    """`kx suggest [tokens...]` — return context-aware completion candidates.

    Emits a small JSON payload the Node client (or a future TUI) can render.
    """
    lex = list_verbs()
    verbs = sorted(lex.keys())
    tokens = args[1:]

    if not tokens:
        _print_json({"kind": "verb", "items": [{"token": v, "hint": (lex[v].get("family") or "")} for v in verbs]})
        return 0

    parsed = parse_command_form(tokens)
    verb_l = parsed["verb"].lower()
    obj_l = parsed["obj"].lower()
    last = tokens[-1]
    # Convention: caller sends the full raw line; last token is the completion prefix

    # If exactly one token → verb prefix
    if len(tokens) == 1 and not last.startswith("-"):
        prefix = last.lower()
        matches = [v for v in verbs if v.startswith(prefix)]
        _print_json({
            "kind": "verb",
            "prefix": prefix,
            "items": [{"token": v, "hint": (lex[v].get("family") or "")} for v in matches],
        })
        return 0

    # If two tokens, second isn't a flag → object prefix
    if len(tokens) == 2 and not tokens[1].startswith("-"):
        meta = lex.get(verb_l)
        prefix = tokens[1].lower()
        objs = sorted(list((meta or {}).get("objects") or []))
        matches = [o for o in objs if o.startswith(prefix)]
        _print_json({
            "kind": "object",
            "verb": verb_l,
            "prefix": prefix,
            "items": [{"token": o, "hint": f"object of {verb_l}"} for o in matches],
        })
        return 0

    # Otherwise → flag / scope value / any known flag
    prev = tokens[-2] if len(tokens) >= 2 else ""
    if prev == "--scope":
        scopes = ["lab", "owned", "pact", "engagement"]
        prefix = last.lower()
        _print_json({
            "kind": "scope",
            "items": [{"token": s, "hint": "authorization scope"} for s in scopes if s.startswith(prefix)],
        })
        return 0

    known_flags = [
        ("--scope", "lab|owned|pact|engagement"),
        ("--sim", "simulate mode (safe)"),
        ("--live", "execute mode"),
        ("--at", "target host/user/pid"),
        ("--realm", "AD/Entra realm"),
        ("--url", "http(s) URL"),
        ("--bind", "host:port"),
        ("--pid", "process id"),
        ("--path", "filesystem path"),
        ("--pact-file", "engagement pact json"),
        ("--with", "key=value"),
    ]
    prefix = last if last.startswith("-") else ""
    _print_json({
        "kind": "flag",
        "verb": verb_l,
        "object": obj_l,
        "items": [{"token": f, "hint": h} for f, h in known_flags if f.startswith(prefix)],
    })
    return 0


def _emit_ask(args: list[str]) -> int:
    """`kx ask <verb> [obj] [-- extra flags]` — interactive parameter prompt.

    After collecting missing parameters, executes the command and pretty-prints.
    """
    rest = args[1:]
    if not rest:
        print("usage: kx ask <verb> [object] [-- --scope lab --sim ...]", file=sys.stderr)
        return 2
    verb = rest[0]
    idx = 1
    obj = ""
    if len(rest) > 1 and not rest[1].startswith("-"):
        obj = rest[1]
        idx = 2
    extra = rest[idx:]

    print(f"[Kx] Interactive parameters for `{verb}{(' ' + obj) if obj else ''}`", file=sys.stderr)
    print(f"[Kx] Press Enter to accept default/placeholder; '*' marks required.\n", file=sys.stderr)

    argv_base: list[str] = [verb]
    if obj:
        argv_base.append(obj)
    argv_base.extend(extra)

    fields, key = schema_for(verb, obj, lexicon_verbs=list_verbs())
    parsed = parse_command_form(argv_base)
    is_live = "--live" in parsed["flags_set"]
    additions = collect_from_prompts(
        fields, parsed["flags_set"], sys.stdin, sys.stderr, is_live=is_live
    )
    augmented = augment_argv(argv_base, additions)

    # Ensure scope flag exists — required by the parser. Only add --sim if the
    # user hasn't already picked a mode (--sim / --live); otherwise their choice
    # would be silently overridden by a trailing --sim.
    if "--scope" not in augmented:
        print("[Kx] --scope not provided; defaulting to `lab`", file=sys.stderr)
        augmented.extend(["--scope", "lab"])
    if "--sim" not in augmented and "--live" not in augmented:
        print("[Kx] mode not specified; defaulting to `--sim`", file=sys.stderr)
        augmented.append("--sim")

    print(f"\n[Kx] Executing: kx {' '.join(augmented)}\n", file=sys.stderr)
    return _run_parsed(augmented, pretty=True)


def _run_parsed(argv: list[str], pretty: bool = False) -> int:
    """Parse and execute; render either as pretty text or JSON."""
    try:
        cmd = parse_argv(argv)
    except KxLangError as exc:
        print(f"KxLang error: {exc}", file=sys.stderr)
        _print_next()
        return 2
    orch = Orchestrator()
    try:
        result = orch.run(cmd.module, cmd.params)
    except KeyError as exc:
        print(f"KxLang error: {exc}", file=sys.stderr)
        _print_next()
        return 2
    payload = result.to_dict()
    payload["kxlang"] = cmd.to_dict()
    if pretty:
        print(render_result_text(payload))
    else:
        _print_json(payload)
    if result.status in {"denied", "error"}:
        return 2
    return 0


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    # Extract global flags before verb parsing
    pretty = False
    if "--pretty" in args:
        pretty = True
        args = [a for a in args if a != "--pretty"]

    # Meta commands (must not go through KxLang verb parser)
    if args and args[0].lower() in {"update", "upgrade"}:
        raise SystemExit(_run_update())
    if args and args[0].lower() in {"login", "hud", "edex"}:
        raise SystemExit(_run_hud())
    if not args:
        # Bare `kx` → interactive program
        raise SystemExit(_run_hud())

    if (
        is_help_token(args[0])
        or (len(args) >= 2 and is_help_token(args[1]))
        or args[0].lower() == "help"
    ):
        raise SystemExit(_emit_help(args))

    head = args[0].lower()
    if head in {"lang", "language", "locale", "언어"}:
        raise SystemExit(_emit_lang(args))

    if head == "lexicon":
        _print_json({"language": "KxLang", "codename": "DEFCOM", "verbs": list_verbs()})
        return

    if head == "form":
        raise SystemExit(_emit_form(args))
    if head == "suggest":
        raise SystemExit(_emit_suggest(args))
    if head == "ask":
        raise SystemExit(_emit_ask(args))

    if head == "serve":
        print("KxLang error: web console removed. Use native client: kx", file=sys.stderr)
        raise SystemExit(2)

    raise SystemExit(_run_parsed(args, pretty=pretty))


if __name__ == "__main__":
    main()
