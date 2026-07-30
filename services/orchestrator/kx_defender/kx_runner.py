"""KxLang command runner — execute parsed KxCommand against modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kx_defender.base import AttackModule, DefenseModule
from kx_defender.kxlang import KxCommand
from kx_defender.orchestrator import Orchestrator
from kx_defender.result import ModuleResult


class KxRunner:
    """Execute KxLang commands by routing to appropriate modules."""

    # 명령어 라우팅 맵
    VERB_ROUTING = {
        # 방어 (Defense)
        "watch": {
            "procs": "defense_process_monitor",
            "network": "defense_network_monitor",
            "files": "defense_file_monitor",
        },
        "kill": {
            "pid": "defense_process_kill",
            "proc": "defense_process_kill_by_name",
        },
        "sig": {
            "scan": "defense_yara_scan",
            "scan-mem": "defense_memory_scan",
            "list": "defense_list_rules",
        },
        "trace": {
            "behavior": "defense_trace_behavior",
            "anomaly": "defense_detect_anomaly",
            "network": "defense_trace_network",
        },
        "audit": {
            "rules": "defense_rule_management",
            "logs": "defense_audit_logs",
        },

        # 공격 (Attack)
        "roast": {
            "tickets": "attack_kerberoasting",
            "ldap": "attack_ldap_enum",
            "spray": "attack_password_spray",
        },
        "relay": {
            "ntlm": "attack_ntlm_relay",
            "cert": "attack_certificate_request",
        },
        "loot": {
            "credentials": "attack_dpapi_credentials",
            "browser": "attack_browser_passwords",
            "wifi": "attack_wifi_profiles",
            "rdp": "attack_rdp_cache",
        },
        "bait": {
            "device-code": "attack_device_code_phishing",
            "aad": "attack_entra_id_enum",
            "ca-test": "attack_ca_bypass_test",
        },
        "crack": {
            "wifi": "attack_wifi_scan",
            "handshake": "attack_handshake_capture",
            "password": "attack_wifi_crack",
            "wps": "attack_wps_attack",
        },

        # 웹 (Web)
        "sweep": {
            "web": "attack_web_scanner",
            "sqli": "attack_sqli_test",
            "xss": "attack_xss_test",
            "csrf": "attack_csrf_test",
            "owasp": "attack_owasp_scan",
        },
        "probe": {
            "api": "attack_api_test",
            "graphql": "attack_graphql_test",
        },

        # C2 & 포스트 익스플로잇 (C2)
        "nexus": {
            "listen": "attack_c2_listener",
            "havoc": "attack_c2_havoc",
            "sliver": "attack_c2_sliver",
            "forge": "attack_c2_payload_gen",
            "config": "attack_c2_config",
            "session": "attack_c2_session_list",
            "exec": "attack_c2_execute",
            "file": "attack_c2_file_transfer",
            "privesc": "attack_c2_privesc",
        },

        # 분석 (Analytics)
        "graph": {
            "threat": "defense_threat_graph",
            "process": "defense_process_graph",
            "network": "defense_network_graph",
        },
        "query": {
            "events": "defense_query_events",
            "stats": "defense_query_stats",
            "ioc": "defense_query_ioc",
        },

        # 관리 (Management)
        "config": {
            "get": "manage_config_get",
            "set": "manage_config_set",
            "policy": "manage_policy",
            "profile": "manage_profile",
        },
        "report": {
            "generate": "manage_report_generate",
            "export": "manage_report_export",
            "audit": "manage_audit_log",
        },
        "deploy": {
            "agent": "manage_deploy_agent",
            "status": "manage_deployment_status",
            "update": "manage_update_agents",
        },

        # 유틸리티 (Utility)
        "verify": {
            "command": "util_verify_command",
            "connect": "util_verify_connection",
            "access": "util_verify_access",
        },
    }

    def __init__(self):
        self.orch = Orchestrator()

    def execute(self, cmd: KxCommand, verbose: bool = False) -> ModuleResult:
        """
        Execute KxLang command.

        Args:
            cmd: Parsed KxCommand
            verbose: Verbose output

        Returns:
            ModuleResult with execution outcome
        """

        # 특수 명령어 처리
        if cmd.verb in {"help", "lexicon", "verbs"}:
            return self._handle_special_commands(cmd)

        # 모듈 라우팅
        module_name = self._route_to_module(cmd.verb, cmd.obj)

        if not module_name:
            return ModuleResult(
                module="kx_runner",
                status="error",
                meta={"error": f"Unknown command: {cmd.verb} {cmd.obj}"},
            )

        # 파라미터 전처리
        params = self._preprocess_params(cmd.params, cmd.verb, cmd.obj)

        # 모듈 실행
        if verbose:
            print(f"🎯 Executing: {cmd.verb} {cmd.obj} ({module_name})")
            print(f"📋 Parameters: {json.dumps(params, indent=2, ensure_ascii=False)}")

        try:
            result = self.orch.run(module_name, params)
        except Exception as e:
            return ModuleResult(
                module=module_name,
                status="error",
                meta={"error": str(e)},
            )

        return result

    def _route_to_module(self, verb: str, obj: str) -> str | None:
        """Route verb+object to module name."""
        verb_lower = verb.lower()
        obj_lower = obj.lower()

        if verb_lower not in self.VERB_ROUTING:
            return None

        routing = self.VERB_ROUTING[verb_lower]
        return routing.get(obj_lower)

    def _preprocess_params(self, params: dict[str, Any], verb: str, obj: str) -> dict[str, Any]:
        """Preprocess parameters based on verb/object type."""
        result = dict(params)

        # Verb별 기본 파라미터 설정
        if verb == "watch":
            result.setdefault("interval", 1)
            result.setdefault("format", "table")

        elif verb in {"kill", "loot", "roast"}:
            result.setdefault("format", "json")

        elif verb == "sweep":
            result.setdefault("headless", True)
            result.setdefault("timeout", 30)
            if obj == "web":
                result.setdefault("depth", 3)

        elif verb == "nexus":
            if obj in {"listen", "havoc", "sliver"}:
                result.setdefault("protocol", "http")
                result.setdefault("host", "127.0.0.1")
                result.setdefault("port", 4455)

        elif verb == "report":
            result.setdefault("format", "html")

        return result

    def _handle_special_commands(self, cmd: KxCommand) -> ModuleResult:
        """Handle help, lexicon, etc."""
        from kx_defender.kxlang import load_lexicon, list_verbs

        if cmd.verb == "lexicon":
            lexicon = load_lexicon()
            if cmd.obj:
                # 특정 동사의 렉시콘만
                verbs = {cmd.obj.lower(): lexicon["verbs"].get(cmd.obj.lower(), {})}
            else:
                verbs = lexicon.get("verbs", {})

            return ModuleResult(
                module="kxlang",
                status="success",
                meta={"lexicon": verbs},
            )

        elif cmd.verb == "verbs":
            verbs = list_verbs()
            return ModuleResult(
                module="kxlang",
                status="success",
                meta={"verbs": verbs},
            )

        elif cmd.verb == "help":
            help_text = self._generate_help(cmd.obj)
            return ModuleResult(
                module="kxlang",
                status="success",
                meta={"help": help_text},
            )

        return ModuleResult(module="kxlang", status="error")

    def _generate_help(self, topic: str = "") -> str:
        """Generate help text."""
        if not topic:
            return """
Kx-Defender - Windows Attack + Defense Platform
사용법: kx <VERB> <OBJECT> [--flags]

주요 명령어:
  방어:    kx watch procs    kx kill pid       kx sig scan      kx trace behavior
  공격:    kx roast tickets  kx relay ntlm     kx loot creds    kx bait device-code
  웹:      kx sweep web      kx probe api
  C2:      kx nexus listen   kx nexus forge    kx nexus exec
  관리:    kx config set     kx report gen     kx deploy agent

더 알아보기:
  kx lexicon          - 모든 명령어 목록
  kx help <verb>      - 특정 동사 도움말
  kx help <verb> <obj> - 구체적인 도움말
"""

        return f"Help for: {topic}"

    def list_commands(self, category: str = None) -> dict[str, list[str]]:
        """List all available commands."""
        result = {}

        for verb, objects in self.VERB_ROUTING.items():
            if category and not self._is_category(verb, category):
                continue
            result[verb] = list(objects.keys())

        return result

    def _is_category(self, verb: str, category: str) -> bool:
        """Check if verb belongs to category."""
        categories = {
            "defense": ["watch", "kill", "sig", "trace", "audit"],
            "attack": ["roast", "relay", "loot", "bait", "crack"],
            "web": ["sweep", "probe"],
            "c2": ["nexus"],
            "analytics": ["graph", "query"],
            "manage": ["config", "report", "deploy"],
            "util": ["verify"],
        }
        return verb in categories.get(category, [])


def main_kx(argv: list[str]) -> None:
    """Main entry point for 'kx' command."""
    from kx_defender.kxlang import parse_argv, KxLangError

    if not argv:
        print("kx: no command specified. try: kx help")
        return

    verbose = "--verbose" in argv

    try:
        cmd = parse_argv(argv)
    except KxLangError as e:
        print(f"❌ Error: {e}")
        return

    runner = KxRunner()
    result = runner.execute(cmd, verbose=verbose)

    # 결과 출력
    if result.status == "success":
        if "--json" in argv:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            _print_result_table(result)
    else:
        print(f"❌ {result.status.upper()}: {result.meta.get('error', 'Unknown error')}")


def _print_result_table(result: ModuleResult) -> None:
    """Print result in table format."""
    print(f"\n📊 {result.module} - {result.status.upper()}")
    print(f"⏱️  {result.meta.get('timestamp', 'N/A')}")

    if "findings" in result.meta:
        print(f"\n🎯 Findings: {len(result.meta['findings'])}")
        for finding in result.meta["findings"][:5]:
            print(f"  - {finding}")

    if "data" in result.meta:
        print(f"\n📋 Data: {len(result.meta['data'])} items")


if __name__ == "__main__":
    import sys
    main_kx(sys.argv[1:])
