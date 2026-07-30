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


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

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

    if head == "serve":
        print("KxLang error: web console removed. Use native client: kx", file=sys.stderr)
        raise SystemExit(2)

    try:
        cmd = parse_argv(args)
    except KxLangError as exc:
        print(f"KxLang error: {exc}", file=sys.stderr)
        _print_next()
        raise SystemExit(2) from exc

    orch = Orchestrator()
    try:
        result = orch.run(cmd.module, cmd.params)
    except KeyError as exc:
        print(f"KxLang error: {exc}", file=sys.stderr)
        _print_next()
        raise SystemExit(2) from exc

    payload = result.to_dict()
    payload["kxlang"] = cmd.to_dict()
    _print_json(payload)
    if result.status in {"denied", "error"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
