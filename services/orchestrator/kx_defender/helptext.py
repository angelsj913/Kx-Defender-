"""KxLang 도움말 텍스트 렌더러 (한/영 다국어)."""

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
    "도움말",
    "도움",
}


EXAMPLES = [
    ("kx roast tickets --scope lab --realm lab.local --sim",
     "Kerberoasting 시뮬레이션"),
    ("kx watch procs --scope lab --live",
     "프로세스 스냅샷 스코어링"),
    ("kx watch procs --continuous --interval 30 --min-severity high",
     "상시 폴링 감시 (인터벌 30초)"),
    ("kx watch fs ~/Downloads --interval 20",
     "폴더 파일 변경 감시 + 자동 sig scan"),
    ("kx daemon start interval 30 min_severity high",
     "백그라운드 데몬 시작"),
    ("kx daemon status",
     "데몬 실행 상태 확인"),
    ("kx daemon stop",
     "데몬 안전 종료"),
    ("kx daemon restart",
     "데몬 재시작"),
    ("kx daemon install-unit systemd",
     "systemd --user 유닛 파일 출력"),
    ("kx why 4242 --tree",
     "PID 위험도 근거 + 조상/자식 트리"),
    ("kx alert list",
     "최근 알람 조회"),
    ("kx alert clear",
     "알람 로그 초기화"),
    ("kx report daily",
     "24시간 알람 요약 리포트"),
    ("kx report hours 3 --markdown",
     "임의 시간 창 리포트 (마크다운)"),
    ("kx sig scan --scope lab --sim",
     "시그니처 스캔 실행"),
    ("kx sig import ./my-rules.json",
     "사용자 룰 파일 등록"),
    ("kx sig catalog",
     "전체 룰 카테고리 집계"),
    ("kx sig test KXSIG-001 --sample \"powershell -enc AAAA\"",
     "특정 룰이 샘플에 매치되는지 확인"),
    ("kx ioc load ./ips.txt",
     "IOC blocklist 등록"),
    ("kx ioc check-file /tmp/sample.exe",
     "파일을 IOC로 검사"),
    ("kx export alerts --format csv",
     "알람 로그를 CSV로 export"),
    ("kx kill pid --scope lab --pid 4242 --sim",
     "프로세스 종료 요청"),
    ("kx nexus listen --scope lab --bind 127.0.0.1:4455 --live",
     "C2 리스너 실행 (loopback 전용)"),
    ("kx sweep web --scope owned --url http://127.0.0.1:8080/ --live",
     "웹 취약점 스캔"),
    ("kx ask sweep web",
     "대화형 파라미터 입력 후 실행"),
    ("kx --pretty roast tickets --scope lab --sim",
     "결과를 컬러 텍스트로 렌더"),
    ("kx lang ko",
     "UI 언어를 한국어로 설정"),
    ("kx update",
     "설치 갱신"),
]


def is_help_token(token: str | None) -> bool:
    if token is None:
        return False
    return token.lower() in HELP_TOKENS


def render_global_help(lang: str | None = None) -> str:
    """전역 도움말을 렌더. 언어는 i18n.get_lang() 을 따르되 인자로도 강제 가능."""
    active = (lang or get_lang() or "en").lower()

    verbs = list_verbs()
    title = t("KxLang / DEFCOM — Kx-Defender command language",
              "KxLang / DEFCOM — Kx-Defender 명령 언어", active)
    lines = [
        title,
        "",
        t("Usage:", "사용법:", active),
        "  kx <VERB> <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]",
        "  kx /h                 " + t("Show this help", "이 도움말 표시", active),
        "  kx /h <VERB>          " + t("Show help for one verb", "특정 verb 도움말", active),
        "  kx update             " + t("Update install", "설치 갱신 (완전 재설치 아님)", active),
        "  kx lang [en|ko]       " + t("Get/set UI language", "UI 언어 조회/설정", active),
        "  kx lexicon            " + t("Dump verb/object lexicon (JSON)", "verb/object 사전을 JSON으로 출력", active),
        "",
        t("Meta commands (local SOC/EDR):",
          "메타 명령 (로컬 SOC/EDR):", active),
        "  kx daemon start|stop|restart|status|config|install-unit  "
        + t("Background watcher", "백그라운드 감시 데몬", active),
        "  kx watch procs --continuous [--interval N] [--min-severity S]  "
        + t("Poll processes", "프로세스 폴링 감시", active),
        "  kx watch fs <dir> [--interval N] [--include GLOB]  "
        + t("Poll filesystem", "파일시스템 폴링 감시", active),
        "  kx why <pid> [--tree]                       "
        + t("Explain a process score", "특정 PID의 위험도 근거", active),
        "  kx alert list|tail|clear|path              "
        + t("Local alert log (JSONL)", "로컬 알람 로그 (JSONL)", active),
        "  kx report daily|weekly|hours N [--json|--text|--markdown]  "
        + t("Alert summary", "알람 요약 리포트", active),
        "  kx sig import|list|catalog|test            "
        + t("Custom rules", "사용자 룰 관리", active),
        "  kx ioc load|list|catalog|check|check-file|clear  "
        + t("Local IOC blocklist", "로컬 IOC 목록", active),
        "  kx export alerts|runs|all [--format json|jsonl|csv] [--out PATH]  "
        + t("Export local data", "로컬 데이터 export", active),
        "  kx ask <verb> [obj]                        "
        + t("Interactive parameter prompt", "대화형 파라미터 입력", active),
        "  kx form <verb> [obj]                       "
        + t("Show parameter schema (JSON)", "파라미터 스키마 JSON 출력", active),
        "  kx suggest <tokens...>                     "
        + t("Context-aware completion candidates", "컨텍스트 자동완성 후보", active),
        "  kx --pretty <cmd>                          "
        + t("Render result as colored text", "결과를 컬러 텍스트로 렌더", active),
        "",
        t("Flags:", "플래그:", active),
        "  --scope lab|owned|pact   " + t("Authorization scope (default: lab)", "권한 범위 (기본: lab)", active),
        "  --sim                    " + t("Simulate (default)", "시뮬레이션 (기본)", active),
        "  --live                   " + t("Execute (lab/private/pact only)", "실제 실행 (lab/owned/pact 전용)", active),
        "  --at <target>            " + t("Target host/tenant/ESSID", "대상 호스트/테넌트/ESSID", active),
        "  --realm <domain>         " + t("AD/Entra domain", "AD/Entra 도메인", active),
        "  --url <url>              " + t("Web target URL", "웹 대상 URL", active),
        "  --bind <host:port>       " + t("Listener bind address", "리스너 bind 주소", active),
        "  --pid <n>                " + t("Process id for kill", "종료할 프로세스 ID", active),
        "  --path <file>            " + t("File path for sig scan", "시그니처 스캔 파일 경로", active),
        "  --pact-file <path>       " + t("Engagement allow-list file", "engagement 허용 목록 파일", active),
        "  --with key=value         " + t("Extra module parameter", "추가 모듈 파라미터", active),
        "",
        t("Verbs (KxLang core):", "Verb 목록 (KxLang 핵심):", active),
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
            t("Examples:", "예시:", active),
            *[f"  {ex[0]:<62}  # {ex[1]}" for ex in EXAMPLES],
            "",
            t("Language: kx lang ko  |  kx lang en",
              "언어 전환: kx lang ko  |  kx lang en", active),
            t("Docs: docs/kxlang.md", "문서: docs/kxlang.md", active),
        ]
    )
    return "\n".join(lines) + "\n"


def render_verb_help(verb: str, lang: str | None = None) -> str:
    """특정 verb의 도움말 렌더."""
    active = (lang or get_lang() or "en").lower()
    lex = load_lexicon()
    key = verb.lower()
    meta: dict[str, Any] | None = lex.get("verbs", {}).get(key)
    if meta is None:
        available = ", ".join(sorted(lex.get("verbs", {})))
        raise ValueError(
            t(f"unknown verb {verb!r}. available: {available}",
              f"알 수 없는 verb {verb!r}. 사용 가능: {available}", active)
        )

    objects = meta.get("objects", {})
    lines = [
        t(f"KxLang verb: {key}", f"KxLang verb: {key}", active),
        t(f"Role:        {meta.get('role', '-')}",
          f"역할:        {meta.get('role', '-')}", active),
        t(f"Family:      {meta.get('family', meta.get('module', '-'))}",
          f"패밀리:      {meta.get('family', meta.get('module', '-'))}", active),
        t(f"Default obj: {meta.get('default_object', '-')}",
          f"기본 object: {meta.get('default_object', '-')}", active),
        "",
        t("Objects → modules:", "Object → 모듈 매핑:", active),
    ]
    for obj, module in sorted(objects.items()):
        lines.append(f"  {obj:<16} → {module}")

    lines.extend(
        [
            "",
            t("Usage:", "사용법:", active),
            f"  kx {key} <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]",
            "",
            t("Examples:", "예시:", active),
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
    lines.append(t("Also: kx /h  |  kx lang ko|en  |  kx lexicon",
                   "관련: kx /h  |  kx lang ko|en  |  kx lexicon", active))
    return "\n".join(lines) + "\n"
