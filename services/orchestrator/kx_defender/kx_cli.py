"""kx — KxLang (DEFCOM) front-end CLI (stdlib only)."""

from __future__ import annotations

import json
import os
import platform
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


def _emit_why(args: list[str]) -> int:
    """`kx why <pid> [--tree]` — explain a process's KxScore reasons.

    Runs the same scoring pipeline as `kx watch procs` but filters to a single
    PID and renders a focused evidence view. With --tree, also shows the
    ancestor chain and direct children.
    """
    rest = args[1:]
    show_tree = "--tree" in rest
    rest = [a for a in rest if a != "--tree"]
    if not rest:
        print("usage: kx why <pid> [--tree]", file=sys.stderr)
        return 2
    try:
        target_pid = int(rest[0])
    except ValueError:
        print(f"KxLang error: pid must be integer, got {rest[0]!r}", file=sys.stderr)
        return 2

    orch = Orchestrator()
    result = orch.run("process_monitor", {
        "authorized_scope": "lab",
        "mode": "execute" if platform.system() != "unknown" else "simulate",
        "limit": 1000,
    })
    procs = (result.artifacts or {}).get("processes", [])
    by_pid = {p.get("pid"): p for p in procs}
    match = by_pid.get(target_pid)
    if match is None:
        print(f"KxLang error: pid {target_pid} not found in current snapshot", file=sys.stderr)
        print(f"(scanned {len(procs)} processes; try `kx watch procs` first)", file=sys.stderr)
        return 2

    from kx_defender.render import _color_enabled, _c, render_process_tree  # noqa: PLC0415
    use_color = _color_enabled(None)
    reset = _c("reset", use_color)
    orange = _c("orange", use_color)
    accent = _c("accent", use_color)
    muted = _c("muted", use_color)
    red = _c("red", use_color)
    yellow = _c("yellow", use_color)

    score = match.get("score", 0)
    level = match.get("level", "low")
    reasons = match.get("reasons", []) or []
    score_c = red if score >= 70 else orange if score >= 45 else yellow if score >= 20 else muted

    print(f"{orange}WHY pid={reset}{accent}{target_pid}{reset}  "
          f"{muted}name={reset}{match.get('name','?')}  "
          f"{muted}score={reset}{score_c}{score}{reset}  "
          f"{muted}level={reset}{level}")
    print()
    cmdline = match.get("cmdline") or ""
    if cmdline:
        print(f"  {muted}cmdline:{reset} {cmdline}")
    ppid = match.get("ppid")
    if ppid:
        print(f"  {muted}ppid:{reset}    {ppid}")
    print()
    if reasons:
        print(f"  {orange}REASONS ({len(reasons)}){reset}")
        for r in reasons:
            print(f"    {red}·{reset} {r}")
    else:
        print(f"  {muted}(no elevated-risk reasons — process appears benign){reset}")

    if show_tree:
        # Ancestors: walk ppid up to root (bounded to avoid cycles).
        ancestors: list[dict] = []
        seen = {target_pid}
        cursor = match
        for _ in range(20):
            parent_pid = cursor.get("ppid")
            if not parent_pid or parent_pid in seen:
                break
            parent = by_pid.get(parent_pid)
            if parent is None:
                break
            ancestors.append(parent)
            seen.add(parent_pid)
            cursor = parent
        # Children: direct only.
        children = [p for p in procs if p.get("ppid") == target_pid]

        print()
        print(f"  {orange}ANCESTOR CHAIN{reset}  ({len(ancestors)})")
        for i, a in enumerate(reversed(ancestors), start=1):
            indent = "  " * (i - 1)
            print(f"    {indent}pid={accent}{a.get('pid')}{reset}  {a.get('name','?')}")
        # Show target itself as the last leaf of the chain
        indent = "  " * len(ancestors)
        print(f"    {indent}pid={red}{target_pid}{reset}  {match.get('name','?')}  {muted}(target){reset}")

        print()
        print(f"  {orange}DIRECT CHILDREN{reset}  ({len(children)})")
        if not children:
            print(f"    {muted}(none){reset}")
        else:
            focus_pids = {target_pid} | {c.get("pid") for c in children}
            focus_procs = [p for p in procs if p.get("pid") in focus_pids]
            # Reuse the widget: renders target as root, children indented.
            sub_text = render_process_tree(focus_procs, alert_count=0, color=use_color)
            for line in sub_text.splitlines()[1:]:  # skip the header line
                print(f"  {line}")
    return 0


def _emit_report(args: list[str]) -> int:
    """`kx report [daily|weekly|hours N] [--json|--text|--markdown]`

    Aggregates the local alerts.jsonl over a time window. All I/O local.
    """
    from kx_defender.report import (  # noqa: PLC0415
        load_alerts, render_markdown, render_text, summarize,
    )

    rest = args[1:]
    hours = 24.0
    fmt = "text"
    i = 0
    while i < len(rest):
        tok = rest[i].lower()
        if tok == "daily": hours = 24.0
        elif tok == "weekly": hours = 24.0 * 7
        elif tok == "hourly": hours = 1.0
        elif tok == "hours" and i + 1 < len(rest):
            try: hours = max(0.1, float(rest[i + 1]))
            except ValueError: pass
            i += 1
        elif tok == "--json": fmt = "json"
        elif tok == "--text": fmt = "text"
        elif tok in {"--markdown", "--md"}: fmt = "markdown"
        i += 1

    summary = summarize(load_alerts(), hours=hours)
    if fmt == "json":
        _print_json(summary)
    elif fmt == "markdown":
        print(render_markdown(summary))
    else:
        print(render_text(summary))
    return 0


def _format_daemon_result(subcommand: str, payload: dict[str, Any]) -> str:
    """Present daemon state without leaking the internal JSON transport."""
    ko = get_lang() == "ko"
    if subcommand == "status":
        running = bool(payload.get("running"))
        state = ("실행 중" if running else "중지됨") if ko else ("running" if running else "stopped")
        reason = payload.get("reason")
        detail = f"\nReason: {reason}" if reason and not ko else f"\n이유: {reason}" if reason else ""
        return (f"데몬 상태: {state}" if ko else f"Daemon is {state}") + detail
    if subcommand == "start":
        started = bool(payload.get("started"))
        return (
            "데몬을 시작했습니다." if started and ko else
            "데몬 시작에 실패했습니다." if ko else
            "Daemon started." if started else "Daemon did not start."
        )
    if subcommand == "stop":
        stopped = bool(payload.get("stopped"))
        return (
            "데몬을 중지했습니다." if stopped and ko else
            "데몬이 이미 중지되어 있습니다." if ko else
            "Daemon stopped." if stopped else "Daemon was already stopped."
        )
    if subcommand == "config":
        cfg = payload.get("config") or {}
        title = "데몬 설정" if ko else "Daemon configuration"
        rows = [title, *(f"  {key}: {value}" for key, value in sorted(cfg.items()))]
        if payload.get("path"):
            rows.append(f"  {'경로' if ko else 'Path'}: {payload['path']}")
        return "\n".join(rows)
    return str(payload)


def _emit_daemon(args: list[str], pretty: bool = False) -> int:
    """`kx daemon start|stop|status|config`

    Manages the background watcher process. All state local (~/.kx-defender).
    """
    from kx_defender.daemon import (  # noqa: PLC0415
        CONFIG_PATH, PID_PATH, daemon_start, daemon_status, daemon_stop,
        load_config, save_config,
    )

    rest = args[1:]
    if not rest:
        print("usage: kx daemon start|stop|status|config", file=sys.stderr)
        return 2
    sub = rest[0].lower()

    if sub == "status":
        result = daemon_status()
        print(_format_daemon_result(sub, result)) if pretty else _print_json(result)
        return 0

    if sub == "stop":
        result = daemon_stop()
        print(_format_daemon_result(sub, result)) if pretty else _print_json(result)
        return 0

    if sub == "config":
        # `kx daemon config` prints; `kx daemon config KEY VALUE ...` sets.
        cfg = load_config()
        if len(rest) == 1:
            result = {"path": str(CONFIG_PATH), "config": cfg}
            print(_format_daemon_result(sub, result)) if pretty else _print_json(result)
            return 0
        kv = rest[1:]
        if len(kv) % 2 != 0:
            print("usage: kx daemon config <key> <value> [<key> <value> ...]", file=sys.stderr)
            return 2
        for i in range(0, len(kv), 2):
            key, raw = kv[i], kv[i + 1]
            if key not in cfg:
                print(f"unknown config key: {key}", file=sys.stderr)
                return 2
            cfg[key] = _coerce_value(cfg[key], raw)
        save_config(cfg)
        result = {"path": str(CONFIG_PATH), "config": cfg}
        print(_format_daemon_result(sub, result)) if pretty else _print_json(result)
        return 0

    if sub == "start":
        # Optional inline overrides: `kx daemon start interval 60 min_severity high`
        overrides: dict[str, Any] = {}
        kv = rest[1:]
        if len(kv) % 2 == 0:
            base = load_config()
            for i in range(0, len(kv), 2):
                key, raw = kv[i], kv[i + 1]
                if key in base:
                    overrides[key] = _coerce_value(base[key], raw)
        cfg = load_config()
        cfg.update(overrides)
        result = daemon_start(cfg)
        print(_format_daemon_result(sub, result)) if pretty else _print_json(result)
        return 0 if result.get("started") else 2

    print(f"unknown daemon subcommand: {sub}", file=sys.stderr)
    return 2


def _coerce_value(existing: Any, raw: str) -> Any:
    """Coerce CLI string to the type of the existing config value."""
    if isinstance(existing, bool):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(existing, int) and not isinstance(existing, bool):
        try: return int(raw)
        except ValueError: return existing
    if isinstance(existing, float):
        try: return float(raw)
        except ValueError: return existing
    return raw


def _emit_sig_meta(args: list[str]) -> int:
    """`kx sig import <path>` / `kx sig list` / `kx sig catalog`."""
    from datetime import datetime, timezone  # noqa: PLC0415
    from pathlib import Path as _Path  # noqa: PLC0415
    from modules.engines.kxsig import (  # noqa: PLC0415
        import_user_rules, list_user_rule_files, summarize_rule_catalog,
    )

    rest = args[1:]
    if not rest:
        print("usage: kx sig import <path> | kx sig list | kx sig catalog", file=sys.stderr)
        return 2
    sub = rest[0].lower()

    if sub == "catalog":
        _print_json(summarize_rule_catalog())
        return 0
    if sub == "list":
        _print_json({"user_files": list_user_rule_files()})
        return 0
    if sub == "import":
        if len(rest) < 2:
            print("usage: kx sig import <path> [--name <basename>]", file=sys.stderr)
            return 2
        src = _Path(rest[1]).expanduser().resolve()
        name = None
        if len(rest) >= 4 and rest[2] == "--name":
            name = rest[3]
        os.environ["KX_IMPORT_TS"] = datetime.now(timezone.utc).isoformat()
        outcome = import_user_rules(src, name=name)
        _print_json(outcome)
        return 0 if outcome.get("imported") else 2

    print(f"unknown sig subcommand: {sub}", file=sys.stderr)
    return 2


def _option_value(args: list[str], option: str) -> str | None:
    if option not in args:
        return None
    index = args.index(option)
    if index + 1 >= len(args):
        raise ValueError(f"{option} requires a value")
    return args[index + 1]


def _emit_alert(args: list[str]) -> int:
    """Manage local alerts while retaining the JSONL compatibility log."""
    from kx_defender.alert_store import AlertStore  # noqa: PLC0415
    from kx_defender.alerts import ALERT_LOG_PATH, clear_alerts  # noqa: PLC0415

    rest = args[1:]
    sub = rest[0].lower() if rest else "list"
    as_json = "--json" in rest
    rest = [item for item in rest if item != "--json"]
    store = AlertStore()

    if sub == "path":
        payload = {"database": str(store.path), "compatibility_log": str(ALERT_LOG_PATH)}
        if as_json:
            _print_json(payload)
        else:
            print(f"database: {store.path}\ncompatibility log: {ALERT_LOG_PATH}")
        return 0
    if sub == "clear":
        n = clear_alerts()
        print(
            f"cleared {n} compatibility log record(s); lifecycle database was retained",
            file=sys.stderr,
        )
        return 0
    if sub == "migrate":
        outcome = store.migrate_jsonl(ALERT_LOG_PATH)
        if as_json:
            _print_json(outcome)
        else:
            print(
                f"imported={outcome['imported']} skipped={outcome['skipped']} "
                f"invalid={outcome['invalid']}"
            )
        return 0 if outcome["invalid"] == 0 else 2

    try:
        if sub == "show":
            if len(rest) < 2:
                raise ValueError("usage: kx alert show <alert-id>")
            alert = store.get_alert(rest[1], include_events=True)
            if as_json:
                _print_json(alert)
            else:
                print(
                    f"{alert['alert_id']} [{alert['severity'].upper()}] {alert['status']} "
                    f"{alert['module']} - {alert['title']}\n"
                    f"seen: {alert['first_seen']} .. {alert['last_seen']}  count={alert['count']}"
                )
                for event in alert["events"]:
                    suffix = f" - {event['note']}" if event["note"] else ""
                    print(f"  {event['ts']} {event['actor']} {event['action']}{suffix}")
            return 0

        if sub in {"ack", "resolve", "reopen"}:
            if len(rest) < 2:
                raise ValueError(f"usage: kx alert {sub} <alert-id>")
            option = "--reason" if sub == "resolve" else "--note"
            note = _option_value(rest, option) or ""
            target = {"ack": "acknowledged", "resolve": "resolved", "reopen": "new"}[sub]
            alert = store.transition(
                rest[1],
                target,
                actor=os.environ.get("KX_ACTOR") or "admin",
                note=note,
            )
            if as_json:
                _print_json(alert)
            else:
                print(f"{alert['alert_id']} -> {alert['status']}")
            return 0

        if sub not in {"list", "tail"}:
            raise ValueError("use: kx alert list|show|ack|resolve|reopen|migrate|path")
        status = _option_value(rest, "--status")
        severity = _option_value(rest, "--severity")
        raw_limit = _option_value(rest, "--limit")
        if raw_limit is None and len(rest) >= 2 and rest[1].isdigit():
            raw_limit = rest[1]
        alerts = store.list_alerts(
            status=status,
            severity=severity,
            limit=int(raw_limit or 25),
        )
    except (KeyError, ValueError) as exc:
        print(f"Kx alert error: {exc}", file=sys.stderr)
        return 2

    if not alerts:
        if as_json:
            _print_json({"alerts": []})
        else:
            print("(no alerts)", file=sys.stderr)
        return 0
    if as_json:
        _print_json({"alerts": alerts})
        return 0

    from kx_defender.render import _color_enabled, _c, _SEV_COLOR  # noqa: PLC0415

    use_color = _color_enabled(None)
    reset = _c("reset", use_color)
    muted = _c("muted", use_color)
    accent = _c("accent", use_color)
    for alert in alerts:
        sev = str(alert.get("severity", "info")).lower()
        sev_c = _SEV_COLOR.get(sev, "") if use_color else ""
        print(
            f"{muted}{alert['last_seen']}{reset}  {sev_c}[{sev.upper():^8}]{reset}  "
            f"{accent}{alert['alert_id']}{reset}  {alert['status']:<12} "
            f"{alert['module']}  {alert['title']}  x{alert['count']}"
        )
    return 0


def _emit_case(args: list[str]) -> int:
    """Manage local incident cases linked to lifecycle alerts."""
    from kx_defender.alert_store import AlertStore  # noqa: PLC0415

    rest = args[1:]
    sub = rest[0].lower() if rest else "list"
    as_json = "--json" in rest
    rest = [item for item in rest if item != "--json"]
    store = AlertStore()
    actor = os.environ.get("KX_ACTOR") or "admin"
    try:
        if sub == "list":
            payload: object = {
                "cases": store.list_cases(status=_option_value(rest, "--status"))
            }
        elif sub == "show":
            if len(rest) < 2:
                raise ValueError("usage: kx case show <case-id>")
            payload = store.get_case(rest[1])
        elif sub == "create":
            title = _option_value(rest, "--title")
            if not title:
                raise ValueError(
                    "usage: kx case create --title <title> [--from-alert <alert-id>]"
                )
            payload = store.create_case(
                title,
                from_alert=_option_value(rest, "--from-alert"),
                severity=_option_value(rest, "--severity"),
            )
        elif sub == "add":
            if len(rest) < 3:
                raise ValueError("usage: kx case add <case-id> <alert-id>")
            payload = store.add_case_alert(rest[1], rest[2])
        elif sub == "note":
            if len(rest) < 3:
                raise ValueError('usage: kx case note <case-id> "<note>"')
            payload = store.add_case_note(rest[1], actor, " ".join(rest[2:]))
        elif sub == "close":
            if len(rest) < 2:
                raise ValueError(
                    "usage: kx case close <case-id> --resolution <resolution>"
                )
            resolution = _option_value(rest, "--resolution")
            if not resolution:
                raise ValueError("--resolution is required")
            payload = store.close_case(rest[1], resolution)
        else:
            raise ValueError("use: kx case list|show|create|add|note|close")
    except (KeyError, ValueError) as exc:
        print(f"Kx case error: {exc}", file=sys.stderr)
        return 2

    if as_json:
        _print_json(payload)
    elif isinstance(payload, dict) and "cases" in payload:
        for case in payload["cases"]:
            print(
                f"{case['case_id']} [{case['severity'].upper()}] "
                f"{case['status']:<6} {case['title']}"
            )
    elif isinstance(payload, dict):
        print(
            f"{payload['case_id']} [{payload['severity'].upper()}] "
            f"{payload['status']} {payload['title']}"
        )
    return 0


def _emit_watch_continuous(args: list[str]) -> int:
    """`kx watch procs --continuous [--interval N] [--min-severity S] [--iter N]`

    Runs the local polling loop. Zero external I/O — process reads + JSONL
    alert log only.
    """
    from kx_defender.watcher import KxWatcher, DEFAULT_INTERVAL, DEFAULT_MIN_SEV  # noqa: PLC0415

    interval = DEFAULT_INTERVAL
    min_sev = DEFAULT_MIN_SEV
    scope = "lab"
    mode = "execute"
    limit = 200
    max_iter: int | None = None

    it = iter(range(len(args)))
    tokens = list(args)
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--continuous":
            i += 1; continue
        if tok == "--interval" and i + 1 < len(tokens):
            try: interval = float(tokens[i + 1])
            except ValueError: pass
            i += 2; continue
        if tok == "--min-severity" and i + 1 < len(tokens):
            min_sev = tokens[i + 1]
            i += 2; continue
        if tok == "--iter" and i + 1 < len(tokens):
            try: max_iter = max(1, int(tokens[i + 1]))
            except ValueError: pass
            i += 2; continue
        if tok == "--scope" and i + 1 < len(tokens):
            scope = tokens[i + 1].lower()
            # normalize pact→engagement like KxLang does
            if scope in {"pact"}: scope = "engagement"
            i += 2; continue
        if tok == "--sim":
            mode = "simulate"; i += 1; continue
        if tok == "--live":
            mode = "execute"; i += 1; continue
        if tok == "--limit" and i + 1 < len(tokens):
            try: limit = max(1, int(tokens[i + 1]))
            except ValueError: pass
            i += 2; continue
        i += 1

    watcher = KxWatcher(
        interval=interval,
        limit=limit,
        min_severity=min_sev,
        scope=scope,
        mode=mode,
        max_iterations=max_iter,
    )
    try:
        stats = watcher.run()
    except KeyboardInterrupt:
        stats = {"iterations": 0, "alerts": 0, "procs_scanned": 0, "interrupted": True}
    _print_json(stats)
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
    if args and args[0].lower() in {"login", "hud"}:
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
    if head == "why":
        raise SystemExit(_emit_why(args))
    if head == "alert" or head == "alerts":
        raise SystemExit(_emit_alert(args))
    if head == "case" or head == "cases":
        raise SystemExit(_emit_case(args))
    if head == "report":
        raise SystemExit(_emit_report(args))
    if head == "daemon":
        raise SystemExit(_emit_daemon(args, pretty=pretty))

    # `kx sig import|list|catalog` are meta commands. `kx sig scan|file` are
    # KxLang verb.object invocations and must fall through to parse_argv.
    if head == "sig" and len(args) >= 2 and args[1].lower() in {"import", "list", "catalog"}:
        raise SystemExit(_emit_sig_meta(args))

    # `kx watch procs --continuous [--interval N] [--min-severity high]`
    # runs the polling loop in-process. All other `kx watch` invocations fall
    # through to the normal parser (single snapshot).
    if head == "watch" and "--continuous" in args:
        raise SystemExit(_emit_watch_continuous(args))

    if head == "serve":
        print("KxLang error: web console removed. Use native client: kx", file=sys.stderr)
        raise SystemExit(2)

    # `--json` is an explicit machine-output escape hatch for commands that
    # otherwise flow through the interactive client's human-readable default.
    args = [arg for arg in args if arg != "--json"]
    raise SystemExit(_run_parsed(args, pretty=pretty))


if __name__ == "__main__":
    main()
