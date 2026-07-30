"""Human-readable KxLang help text (en / ko)."""

from __future__ import annotations

from typing import Any

from kx_defender.i18n import get_lang
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
    "kx sig scan --scope lab --sim",
    "kx kill pid --scope lab --pid 4242 --sim",
    "kx daemon status",
    "kx lang ko",
    "kx update",
]


def is_help_token(token: str | None) -> bool:
    if token is None:
        return False
    return token.lower() in HELP_TOKENS


def render_global_help(lang: str | None = None) -> str:
    lang = lang or get_lang()
    verbs = list_verbs()
    if lang == "ko":
        lines = [
            "KxLang / DEFCOM — Kx-Defender 명령어",
            "",
            "사용법:",
            "  kx <동사> <목적어> --scope lab|owned|pact [--sim|--live] [플래그]",
            "  kx /h                 전체 도움말",
            "  kx /h <동사>          동사별 도움말",
            "  kx update             재설치 없이 업데이트",
            "  kx lang [en|ko]       UI 언어",
            "  kx lexicon            동사 사전 (JSON)",
            "",
            "플래그:",
            "  --scope lab|owned|pact   인가 범위 (기본: lab)",
            "  --sim                    시뮬레이션 (기본)",
            "  --live                   실실행",
            "  --pretty                 읽기 쉬운 텍스트 출력",
            "",
            "동사:",
        ]
    else:
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
            "  --live                   Execute",
            "  --pretty                 Human-readable text output",
            "",
            "Verbs:",
        ]

    for verb in sorted(verbs):
        meta = verbs[verb]
        objs = ", ".join(meta.get("objects", [])[:6])
        more = ", ..." if len(meta.get("objects", [])) > 6 else ""
        role = meta.get("role") or "-"
        lines.append(f"  {verb:<8} {role:<16} objects: {objs}{more}")

    if lang == "ko":
        lines.extend(["", "예제:", *[f"  {ex}" for ex in EXAMPLES], "", "언어: kx lang ko | kx lang en"])
    else:
        lines.extend(["", "Examples:", *[f"  {ex}" for ex in EXAMPLES], "", "Language: kx lang ko | kx lang en"])
    return "\n".join(lines) + "\n"


def render_verb_help(verb: str, lang: str | None = None) -> str:
    lang = lang or get_lang()
    lex = load_lexicon()
    key = verb.lower()
    meta: dict[str, Any] | None = lex.get("verbs", {}).get(key)
    if meta is None:
        available = ", ".join(sorted(lex.get("verbs", {})))
        if lang == "ko":
            raise ValueError(f"알 수 없는 동사 {verb!r}. 사용 가능: {available}")
        raise ValueError(f"unknown verb {verb!r}. available: {available}")

    objects = meta.get("objects", {})
    if lang == "ko":
        lines = [
            f"KxLang 동사: {key}",
            f"역할:        {meta.get('role', '-')}",
            f"패밀리:      {meta.get('family', meta.get('module', '-'))}",
            f"기본 목적어: {meta.get('default_object', '-')}",
            "",
            "목적어 → 모듈:",
        ]
    else:
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

    default_obj = meta.get("default_object") or next(iter(objects), "obj")
    if lang == "ko":
        lines.extend(["", "사용법:", f"  kx {key} <목적어> --scope lab [--sim|--live]", "", "예제:"])
    else:
        lines.extend(["", "Usage:", f"  kx {key} <OBJECT> --scope lab [--sim|--live]", "", "Examples:"])
    lines.append(f"  kx {key} {default_obj} --scope lab --sim")
    return "\n".join(lines) + "\n"
