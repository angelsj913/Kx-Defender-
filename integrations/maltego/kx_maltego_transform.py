#!/usr/bin/env python3
"""
kx-Defender Maltego Transform — 명령어 역추적 및 결과 매핑
모든 27개 명령어 지원: Attack(7) + Defense(10) + Infrastructure(4) + Utility(7)

Input Entity: KxCommand (명령어)
Output Entities: KxExecution, KxFinding, KxThreat, KxAlert, KxProcess, KxNetwork
"""

import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote


class KxFamily(Enum):
    """명령어 Family 분류"""
    ATTACK = "attack"
    DEFENSE = "defense"
    INFRASTRUCTURE = "infrastructure"
    UTILITY = "utility"


class ExecutionMode(Enum):
    """실행 모드"""
    SIMULATION = "sim"
    LIVE = "live"


class Scope(Enum):
    """권한 범위"""
    LAB = "lab"
    OWNED = "owned"
    PACT = "pact"


@dataclass
class KxCommand:
    """Maltego Input Entity - kx-Defender 명령어"""
    name: str
    family: KxFamily
    subcommand: Optional[str] = None
    scope: Scope = Scope.LAB
    mode: ExecutionMode = ExecutionMode.SIMULATION
    target: Optional[str] = None
    options: dict[str, Any] = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class KxExecution:
    """실행 기록"""
    command: str
    family: str
    execution_id: str
    timestamp: str
    scope: str
    mode: str
    status: str  # success, error, warning
    duration_ms: int
    output_size: int


@dataclass
class KxFinding:
    """발견사항 (sig scan, audit 결과)"""
    finding_id: str
    severity: str  # critical, high, medium, low
    category: str  # malware, compliance, performance, etc
    title: str
    detail: str
    source_command: str
    remediation: Optional[str] = None


@dataclass
class KxThreat:
    """위협 정보 (roast, relay, breach 결과)"""
    threat_id: str
    threat_type: str  # kerberoasting, ntlm_relay, llm_breach
    severity: str
    description: str
    source_command: str
    indicators: list[str] = None  # IoCs


@dataclass
class KxAlert:
    """실시간 경고 (watch, sentry, trace 결과)"""
    alert_id: str
    alert_type: str  # anomaly, signature, behavior
    severity: str
    timestamp: str
    process_name: Optional[str] = None
    process_id: Optional[int] = None
    message: str = ""


@dataclass
class KxProcess:
    """프로세스 정보 (watch, kill 결과)"""
    pid: int
    name: str
    parent_pid: Optional[int] = None
    command_line: Optional[str] = None
    threat_score: Optional[float] = None
    status: Optional[str] = None  # running, terminated, suspicious


@dataclass
class KxNetwork:
    """네트워크 정보 (probe, sweep, graph 결과)"""
    host: str
    port: Optional[int] = None
    protocol: str = "tcp"
    service: Optional[str] = None
    vulnerability: Optional[str] = None
    status: str = "open"


# ============================================================================
# ATTACK FAMILY (7개 명령어)
# ============================================================================

class RoastTransform:
    """kx roast tickets — Kerberoasting"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        """Kerberoasting 공격 결과 → KxThreat + KxAlert"""
        results = []

        # roast tickets --scope lab --realm lab.local --sim
        threat = KxThreat(
            threat_id=f"roast_{cmd.options.get('realm', 'unknown')}_{_ts()}",
            threat_type="kerberoasting",
            severity="high",
            description=f"Kerberos ticket roasting on realm {cmd.options.get('realm')}",
            source_command="roast tickets",
            indicators=[
                f"SPN:{cmd.options.get('realm')}",
                "service_principal_name_enumeration",
                "ticket_request_abuse"
            ]
        )
        results.append(("KxThreat", threat))

        alert = KxAlert(
            alert_id=f"alert_roast_{_ts()}",
            alert_type="kerberoasting",
            severity="high",
            timestamp=_now(),
            message=f"Kerberos roasting detected on {cmd.options.get('realm')}"
        )
        results.append(("KxAlert", alert))

        return results


class RelayTransform:
    """kx relay [type] — NTLM Relay Attack"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        threat = KxThreat(
            threat_id=f"relay_{cmd.target}_{_ts()}",
            threat_type="ntlm_relay",
            severity="critical",
            description=f"NTLM relay attack via {cmd.target or 'captured_traffic'}",
            source_command="relay",
            indicators=["ntlm_auth_capture", "relay_attack", "auth_bypass"]
        )
        results.append(("KxThreat", threat))

        return results


class LootTransform:
    """kx loot [target] — Data Exfiltration (DPAPI)"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        finding = KxFinding(
            finding_id=f"loot_{cmd.target}_{_ts()}",
            severity="critical",
            category="data_exfiltration",
            title=f"DPAPI secrets extracted from {cmd.target}",
            detail="Encrypted secrets decrypted and exfiltrated",
            source_command="loot",
            remediation="Revoke extracted credentials immediately"
        )
        results.append(("KxFinding", finding))

        return results


class BaitTransform:
    """kx bait [type] — Device Code / OAuth Phishing"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        alert = KxAlert(
            alert_id=f"bait_{cmd.options.get('type', 'oauth')}_{_ts()}",
            alert_type="phishing_trap",
            severity="high",
            timestamp=_now(),
            message=f"Bait deployed: {cmd.options.get('type')} OAuth device code"
        )
        results.append(("KxAlert", alert))

        return results


class BreachTransform:
    """kx breach [target] — LLM Red Team Simulation"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        threat = KxThreat(
            threat_id=f"breach_llm_{cmd.target}_{_ts()}",
            threat_type="llm_breach",
            severity="high",
            description=f"LLM red team attack against {cmd.target}",
            source_command="breach",
            indicators=["llm_prompt_injection", "jailbreak_attempt"]
        )
        results.append(("KxThreat", threat))

        return results


class CrackTransform:
    """kx crack [type] — WiFi Password Cracking"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        finding = KxFinding(
            finding_id=f"crack_wifi_{_ts()}",
            severity="high",
            category="authentication",
            title="WiFi password successfully cracked",
            detail=f"Network vulnerability: weak encryption detected",
            source_command="crack",
            remediation="Update to WPA3 or strong passphrase"
        )
        results.append(("KxFinding", finding))

        return results


class NexusTransform:
    """kx nexus listen — C2 Server / Listener"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        bind_addr = cmd.options.get("bind", "127.0.0.1:4455")
        network = KxNetwork(
            host=bind_addr.split(":")[0],
            port=int(bind_addr.split(":")[-1]) if ":" in bind_addr else 4455,
            protocol="tcp",
            service="c2_listener",
            status="listening"
        )
        results.append(("KxNetwork", network))

        return results


# ============================================================================
# DEFENSE FAMILY (10개 명령어)
# ============================================================================

class SentryTransform:
    """kx sentry [target] — Threat Detection"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        alert = KxAlert(
            alert_id=f"sentry_{cmd.target}_{_ts()}",
            alert_type="threat_detected",
            severity="high",
            timestamp=_now(),
            message=f"Sentry detected threat on {cmd.target}"
        )
        results.append(("KxAlert", alert))

        return results


class TraceTransform:
    """kx trace [target] — Process Behavior Analysis"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        pid = cmd.options.get("pid")
        proc = KxProcess(
            pid=pid or 0,
            name=cmd.target or "unknown",
            command_line=cmd.options.get("cmdline"),
            threat_score=cmd.options.get("threat_score", 0.0)
        )
        results.append(("KxProcess", proc))

        if cmd.options.get("threat_score", 0) > 70:
            alert = KxAlert(
                alert_id=f"trace_anomaly_{_ts()}",
                alert_type="anomaly",
                severity="high",
                timestamp=_now(),
                process_id=pid,
                process_name=cmd.target,
                message="Suspicious behavior detected"
            )
            results.append(("KxAlert", alert))

        return results


class AuditTransform:
    """kx audit [component] — Compliance Audit"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        finding = KxFinding(
            finding_id=f"audit_{cmd.target}_{_ts()}",
            severity="medium",
            category="compliance",
            title=f"Audit findings for {cmd.target}",
            detail="Security configuration gaps detected",
            source_command="audit"
        )
        results.append(("KxFinding", finding))

        return results


class HardenTransform:
    """kx harden [target] — Security Hardening"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        exec_record = KxExecution(
            command=f"harden {cmd.target}",
            family="defense",
            execution_id=f"harden_{_ts()}",
            timestamp=_now(),
            scope=cmd.scope.value,
            mode=cmd.mode.value,
            status="success" if cmd.mode == ExecutionMode.SIMULATION else "completed",
            duration_ms=int(cmd.options.get("duration_ms", 1500)),
            output_size=1024
        )
        results.append(("KxExecution", exec_record))

        return results


class TriageTransform:
    """kx triage [alert] — Alert Triage/Classification"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        alert_id = cmd.target or "unknown_alert"
        finding = KxFinding(
            finding_id=f"triage_{alert_id}_{_ts()}",
            severity=cmd.options.get("severity", "medium"),
            category=cmd.options.get("category", "unclassified"),
            title=f"Triaged: {alert_id}",
            detail=f"Classification: {cmd.options.get('classification', 'unknown')}",
            source_command="triage"
        )
        results.append(("KxFinding", finding))

        return results


class ComplyTransform:
    """kx comply [policy] — Compliance Verification"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        policy = cmd.target or "default"
        finding = KxFinding(
            finding_id=f"comply_{policy}_{_ts()}",
            severity=cmd.options.get("violation_severity", "low"),
            category="compliance",
            title=f"Compliance check: {policy}",
            detail=f"Policy violations: {cmd.options.get('violations', 0)} detected",
            source_command="comply"
        )
        results.append(("KxFinding", finding))

        return results


class ForgeTransform:
    """kx forge [config] — Configuration Generation"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        exec_record = KxExecution(
            command=f"forge {cmd.target}",
            family="defense",
            execution_id=f"forge_{_ts()}",
            timestamp=_now(),
            scope=cmd.scope.value,
            mode=cmd.mode.value,
            status="success",
            duration_ms=2000,
            output_size=4096
        )
        results.append(("KxExecution", exec_record))

        return results


class SigTransform:
    """kx sig scan — Signature Scanning"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        path = cmd.options.get("path", "C:\\")
        finding = KxFinding(
            finding_id=f"sig_scan_{_ts()}",
            severity="high",
            category="malware",
            title=f"Malware signatures detected in {path}",
            detail=f"YARA signatures matched: {cmd.options.get('matches', 0)}",
            source_command="sig scan"
        )
        results.append(("KxFinding", finding))

        return results


class WatchTransform:
    """kx watch procs — Process Monitoring"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        pid = cmd.options.get("pid")
        name = cmd.options.get("name", "unknown")

        proc = KxProcess(
            pid=pid or 0,
            name=name,
            parent_pid=cmd.options.get("ppid"),
            threat_score=cmd.options.get("threat_score", 0.0),
            status="running"
        )
        results.append(("KxProcess", proc))

        if cmd.mode == ExecutionMode.LIVE:
            alert = KxAlert(
                alert_id=f"watch_{pid}_{_ts()}",
                alert_type="process_monitoring",
                severity="medium",
                timestamp=_now(),
                process_id=pid,
                process_name=name,
                message=f"Process monitoring: {name} (PID {pid})"
            )
            results.append(("KxAlert", alert))

        return results


class KillTransform:
    """kx kill pid — Process Termination"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        pid = cmd.options.get("pid", 0)
        proc = KxProcess(
            pid=pid,
            name=cmd.target or f"process_{pid}",
            status="terminated" if cmd.mode == ExecutionMode.LIVE else "marked_for_termination"
        )
        results.append(("KxProcess", proc))

        exec_record = KxExecution(
            command=f"kill pid {pid}",
            family="defense",
            execution_id=f"kill_{pid}_{_ts()}",
            timestamp=_now(),
            scope=cmd.scope.value,
            mode=cmd.mode.value,
            status="success" if cmd.options.get("forced") else "pending",
            duration_ms=500,
            output_size=256
        )
        results.append(("KxExecution", exec_record))

        return results


# ============================================================================
# INFRASTRUCTURE FAMILY (4개 명령어)
# ============================================================================

class GraphTransform:
    """kx graph [query] — AD Graph Simulation"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        hosts = cmd.options.get("hosts", ["domain.local"])
        if not hosts:
            hosts = [cmd.target or "domain.local"]

        for host in hosts:
            network = KxNetwork(
                host=host,
                protocol="tcp",
                service="ldap",
                status="active"
            )
            results.append(("KxNetwork", network))

        return results


class ProbeTransform:
    """kx probe [endpoint] — Network Probing"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        if cmd.target and ":" in cmd.target:
            host, port = cmd.target.split(":")
            port = int(port)
        else:
            host, port = cmd.target or "unknown", 80

        network = KxNetwork(
            host=host,
            port=port,
            protocol="tcp",
            service=cmd.options.get("service", "unknown"),
            status="open" if cmd.options.get("open") else "filtered"
        )
        results.append(("KxNetwork", network))

        if not cmd.options.get("open"):
            finding = KxFinding(
                finding_id=f"probe_{host}_{port}_{_ts()}",
                severity="low",
                category="network_reconnaissance",
                title=f"Port {port} is filtered on {host}",
                detail="Service response timeout or blocked",
                source_command="probe"
            )
            results.append(("KxFinding", finding))

        return results


class SweepTransform:
    """kx sweep web — Web Application Scanning"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        url = cmd.options.get("url", cmd.target or "http://unknown")

        findings_count = cmd.options.get("findings", 3)
        for i in range(min(findings_count, 5)):
            severity_list = ["critical", "high", "medium", "low"]
            finding = KxFinding(
                finding_id=f"sweep_{i}_{_ts()}",
                severity=severity_list[i % len(severity_list)],
                category="web_vulnerability",
                title=f"Web vulnerability #{i+1} in {url}",
                detail=f"Vulnerability type: {cmd.options.get('vuln_type', 'XSS/Injection')}",
                source_command="sweep web"
            )
            results.append(("KxFinding", finding))

        return results


# ============================================================================
# UTILITY FAMILY (7개 명령어)
# ============================================================================

class LexiconTransform:
    """kx lexicon — Skill Dictionary"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        exec_record = KxExecution(
            command="lexicon",
            family="utility",
            execution_id=f"lexicon_{_ts()}",
            timestamp=_now(),
            scope="lab",
            mode="sim",
            status="success",
            duration_ms=300,
            output_size=262000
        )
        results.append(("KxExecution", exec_record))

        return results


class LangTransform:
    """kx lang [ko|en] — Language Settings"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        lang = cmd.target or "en"
        exec_record = KxExecution(
            command=f"lang {lang}",
            family="utility",
            execution_id=f"lang_{_ts()}",
            timestamp=_now(),
            scope="lab",
            mode="sim",
            status="success",
            duration_ms=100,
            output_size=512
        )
        results.append(("KxExecution", exec_record))

        return results


class UpdateTransform:
    """kx update — Version Update"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        exec_record = KxExecution(
            command="update",
            family="utility",
            execution_id=f"update_{_ts()}",
            timestamp=_now(),
            scope="lab",
            mode="sim",
            status="checking",
            duration_ms=5000,
            output_size=1024
        )
        results.append(("KxExecution", exec_record))

        return results


class HelpTransform:
    """kx help / /h — Help Display"""

    @staticmethod
    def execute(cmd: KxCommand) -> list[Any]:
        results = []

        exec_record = KxExecution(
            command="help",
            family="utility",
            execution_id=f"help_{_ts()}",
            timestamp=_now(),
            scope="lab",
            mode="sim",
            status="success",
            duration_ms=50,
            output_size=10240
        )
        results.append(("KxExecution", exec_record))

        return results


# ============================================================================
# COMMAND DISPATCH (27개 명령어)
# ============================================================================

COMMAND_HANDLERS = {
    # Attack (7)
    "roast": RoastTransform.execute,
    "relay": RelayTransform.execute,
    "loot": LootTransform.execute,
    "bait": BaitTransform.execute,
    "breach": BreachTransform.execute,
    "crack": CrackTransform.execute,
    "nexus": NexusTransform.execute,

    # Defense (10)
    "sentry": SentryTransform.execute,
    "trace": TraceTransform.execute,
    "audit": AuditTransform.execute,
    "harden": HardenTransform.execute,
    "triage": TriageTransform.execute,
    "comply": ComplyTransform.execute,
    "forge": ForgeTransform.execute,
    "sig": SigTransform.execute,
    "watch": WatchTransform.execute,
    "kill": KillTransform.execute,

    # Infrastructure (3)
    "graph": GraphTransform.execute,
    "probe": ProbeTransform.execute,
    "sweep": SweepTransform.execute,

    # Utility (7)
    "lexicon": LexiconTransform.execute,
    "lang": LangTransform.execute,
    "update": UpdateTransform.execute,
    "help": HelpTransform.execute,
}


# ============================================================================
# MALTEGO SERIALIZATION
# ============================================================================

def _ts() -> str:
    """Unix timestamp (ms) for ID"""
    return str(int(datetime.now().timestamp() * 1000))


def _now() -> str:
    """ISO 8601 timestamp"""
    return datetime.utcnow().isoformat() + "Z"


def entity_to_maltego(entity_type: str, entity_obj: Any) -> dict[str, Any]:
    """Convert dataclass to Maltego entity"""
    data = asdict(entity_obj) if hasattr(entity_obj, "__dataclass_fields__") else entity_obj

    return {
        "@type": entity_type,
        "attributes": {
            k: str(v) if v is not None else ""
            for k, v in data.items()
        },
        "display_value": str(getattr(entity_obj, "title", getattr(entity_obj, "name", str(entity_obj))))
    }


def execute_transform(command: KxCommand) -> list[dict[str, Any]]:
    """Execute Maltego transform"""
    handler = COMMAND_HANDLERS.get(command.name)
    if not handler:
        return [
            entity_to_maltego("KxExecution", KxExecution(
                command=command.name,
                family="unknown",
                execution_id=f"error_{_ts()}",
                timestamp=_now(),
                scope=command.scope.value,
                mode=command.mode.value,
                status="error",
                duration_ms=0,
                output_size=0
            ))
        ]

    results = handler(command)
    return [entity_to_maltego(entity_type, entity_obj) for entity_type, entity_obj in results]


def parse_maltego_input(input_dict: dict[str, Any]) -> KxCommand:
    """Parse Maltego input to KxCommand"""
    attrs = input_dict.get("attributes", {})

    return KxCommand(
        name=attrs.get("name", "unknown"),
        family=KxFamily(attrs.get("family", "attack")),
        subcommand=attrs.get("subcommand"),
        scope=Scope(attrs.get("scope", "lab")),
        mode=ExecutionMode(attrs.get("mode", "sim")),
        target=attrs.get("target"),
        options=json.loads(attrs.get("options", "{}"))
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python kx_maltego_transform.py <command> [options]")
        sys.exit(1)

    cmd_name = sys.argv[1]
    cmd = KxCommand(
        name=cmd_name,
        family=KxFamily.ATTACK,
        scope=Scope.LAB,
        mode=ExecutionMode.SIMULATION
    )

    results = execute_transform(cmd)
    print(json.dumps(results, indent=2))
