"""Human-readable KxLang help text (English)."""

from __future__ import annotations

from typing import Any

from kx_defender.kxlang import list_verbs, load_lexicon

HELP_TOKENS = {
    "/h",
    "/help",
    "-h",
    "--help",
    "help",
    "?",
}


EXAMPLES = [
    "kx roast tickets --scope lab --realm lab.local --sim",
    "kx watch procs --scope lab --live",
    "kx watch procs --continuous --interval 30 --min-severity high",
    "kx daemon start interval 30 min_severity high",
    "kx daemon status",
    "kx daemon stop",
    "kx daemon config",
    "kx doctor",
    "kx why 4242 --tree",
    "kx alert list --status new --severity high",
    "kx alert ack ALT-... --note investigating",
    "kx case create --from-alert ALT-... --title investigation",
    "kx evidence export --case CASE-... --to incident.kxev",
    "kx evidence verify incident.kxev",
    "kx history search sentry",
    "kx favorite run daily-check",
    "kx report daily",
    "kx report hours 3 --markdown",
    "kx sig scan --scope lab --sim",
    "kx sig import ./my-rules.json",
    "kx sig catalog",
    "kx sig validate ./my-rules.json",
    "kx sig test ./my-rules.json --sample ./sample.txt",
    "kx sig conflicts",
    "kx kill pid --scope lab --pid 4242 --sim",
    "kx nexus listen --scope lab --bind 127.0.0.1:4455 --live",
    "kx sweep web --scope owned --url http://127.0.0.1:8080/ --live",
    "kx ask sweep web",
    "kx --pretty roast tickets --scope lab --sim",
    "kx lang ko",
    "kx update",
]


def is_help_token(token: str | None) -> bool:
    if token is None:
        return False
    return token.lower() in HELP_TOKENS


def render_global_help(lang: str | None = None) -> str:
    # Help is always English (lang kept for API compat).
    _ = lang
    verbs = list_verbs()
    lines = [
        "KxLang / DEFCOM — Kx-Defender command language",
        "",
        "Usage:",
        "  kx <VERB> <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]",
        "  kx /h                 Show this help",
        "  kx /h <VERB>          Show help for one verb",
        "  kx update             Update install (no full reinstall)",
        "  kx lang [en|ko]       Get/set UI language",
        "  kx lexicon            Dump verb/object lexicon (JSON)",
        "",
        "Flags:",
        "  --scope lab|owned|pact   Authorization scope (default: lab)",
        "  --sim                    Simulate (default)",
        "  --live                   Execute (lab/private/pact only)",
        "  --at <target>            Target host/tenant/ESSID",
        "  --realm <domain>         AD/Entra domain",
        "  --url <url>              Web target URL",
        "  --bind <host:port>       Listener bind address",
        "  --pid <n>                Process id for kill",
        "  --path <file>            File path for sig scan",
        "  --pact-file <path>       Engagement allow-list file",
        "  --with key=value         Extra module parameter",
        "",
        "Verbs:",
    ]

    for verb in sorted(verbs):
        meta = verbs[verb]
        objs = ", ".join(meta.get("objects", [])[:6])
        more = ""
        if len(meta.get("objects", [])) > 6:
            more = ", ..."
        role = meta.get("role") or "-"
        lines.append(f"  {verb:<8} {role:<16} objects: {objs}{more}")

    lines.extend(
        [
            "",
            "Examples:",
            *[f"  {ex}" for ex in EXAMPLES],
            "",
            "Language: kx lang ko  |  kx lang en",
            "Docs: docs/kxlang.md",
        ]
    )
    return "\n".join(lines) + "\n"


def render_verb_help(verb: str, lang: str | None = None) -> str:
    _ = lang
    lex = load_lexicon()
    key = verb.lower()
    meta: dict[str, Any] | None = lex.get("verbs", {}).get(key)
    if meta is None:
        available = ", ".join(sorted(lex.get("verbs", {})))
        raise ValueError(f"unknown verb {verb!r}. available: {available}")

    objects = meta.get("objects", {})
    lines = [
        f"KxLang verb: {key}",
        f"Role:        {meta.get('role', '-')}",
        f"Family:      {meta.get('family', meta.get('module', '-'))}",
        f"Default obj: {meta.get('default_object', '-')}",
        "",
        "Objects → modules:",
    ]
    for obj, module in sorted(objects.items()):
        lines.append(f"  {obj:<16} → {module}")

    lines.extend(
        [
            "",
            "Usage:",
            f"  kx {key} <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]",
            "",
            "Examples:",
        ]
    )
    default_obj = meta.get("default_object") or next(iter(objects), "obj")
    if key in {"roast", "breach"}:
        lines.append(f"  kx {key} {default_obj} --scope lab --realm lab.local --sim")
    elif key == "nexus":
        lines.append(f"  kx {key} listen --scope lab --bind 127.0.0.1:4455 --live")
    elif key == "sweep":
        lines.append(f"  kx {key} web --scope owned --url http://127.0.0.1/ --live")
    elif key == "crack":
        lines.append(f"  kx {key} wifi --scope lab --at LabWiFi --live")
    else:
        lines.append(f"  kx {key} {default_obj} --scope lab --sim")

    lines.append("")
    lines.append("Also: kx /h  |  kx lang ko|en  |  kx lexicon")
    return "\n".join(lines) + "\n"
