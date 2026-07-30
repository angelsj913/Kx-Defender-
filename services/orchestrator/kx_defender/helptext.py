"""Human-readable KxLang help text (en / ko)."""

from __future__ import annotations

from typing import Any

from kx_defender.i18n import get_lang, t
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
    "kx nexus listen --scope lab --bind 127.0.0.1:4455 --live",
    "kx sweep web --scope owned --url http://127.0.0.1:8080/ --live",
    "kx lang ko",
    "kx lang en",
    "kx serve --bind 127.0.0.1:8787",
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
            "  kx lang [en|ko]       UI 언어 조회/변경",
            "  kx lexicon            동사/목적어 사전 (JSON)",
            "  kx serve [--bind host:port]  콘솔 UI (선택)",
            "",
            "플래그:",
            "  --scope lab|owned|pact   인가 범위 (필수)",
            "  --sim                    시뮬레이션 (기본)",
            "  --live                   실행 (lab/사설/pact만)",
            "  --at <target>            대상 호스트/테넌트/ESSID",
            "  --realm <domain>         AD/Entra 도메인",
            "  --url <url>              웹 대상 URL",
            "  --bind <host:port>       리스너/콘솔 주소",
            "  --pid <n>                kill용 프로세스 ID",
            "  --path <file>            시그니처 스캔 파일",
            "  --pact-file <path>       교전(engagement) 허용 목록",
            "  --with key=value         추가 모듈 파라미터",
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
            "  kx lang [en|ko]       Get/set UI language",
            "  kx lexicon            Dump verb/object lexicon (JSON)",
            "  kx serve [--bind host:port]  Start Console UI (optional)",
            "",
            "Flags:",
            "  --scope lab|owned|pact   Authorization scope (required)",
            "  --sim                    Simulate (default)",
            "  --live                   Execute (lab/private/pact only)",
            "  --at <target>            Target host/tenant/ESSID",
            "  --realm <domain>         AD/Entra domain",
            "  --url <url>              Web target URL",
            "  --bind <host:port>       Listener / console bind address",
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

    if lang == "ko":
        lines.extend(
            [
                "",
                "예제:",
                *[f"  {ex}" for ex in EXAMPLES],
                "",
                "언어: kx lang ko  |  kx lang en",
                "문서: docs/kxlang.md · 정책: docs/policy-self-built.md",
                "참고: 자체 엔진만 사용. 인가된 환경에서만 사용하세요.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Examples:",
                *[f"  {ex}" for ex in EXAMPLES],
                "",
                "Language: kx lang ko  |  kx lang en",
                "Docs: docs/kxlang.md · Policy: docs/policy-self-built.md",
                "Note: Self-built engines only. Authorized use only.",
            ]
        )
    return "\n".join(lines) + "\n"


def render_verb_help(verb: str, lang: str | None = None) -> str:
    lang = lang or get_lang()
    lex = load_lexicon()
    key = verb.lower()
    meta: dict[str, Any] | None = lex.get("verbs", {}).get(key)
    if meta is None:
        available = ", ".join(sorted(lex.get("verbs", {})))
        raise ValueError(
            t(
                f"unknown verb {verb!r}. available: {available}",
                f"알 수 없는 동사 {verb!r}. 사용 가능: {available}",
                lang,
            )
        )

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

    if lang == "ko":
        lines.extend(
            [
                "",
                "사용법:",
                f"  kx {key} <목적어> --scope lab|owned|pact [--sim|--live] [플래그]",
                "",
                "예제:",
            ]
        )
    else:
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
    lines.append(
        t("Also: kx /h  |  kx lang ko|en  |  kx lexicon", "또한: kx /h  |  kx lang ko|en  |  kx lexicon", lang)
    )
    return "\n".join(lines) + "\n"
