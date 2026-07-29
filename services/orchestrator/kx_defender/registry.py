"""Module registry (legacy short names + full catalog skill names)."""

from __future__ import annotations

from typing import Dict, Type

from kx_defender.base import AttackModule
from modules.attack.c2 import C2Module
from modules.attack.device_code import DeviceCodeModule
from modules.attack.dpapi import DpapiModule
from modules.attack.kerberoasting import KerberoastingModule
from modules.attack.llm_redteam import LlmRedteamModule
from modules.attack.ntlm_relay import NtlmRelayModule
from modules.attack.web_scanner import WebScannerModule
from modules.attack.wifi import WifiModule
from modules.catalog.factory import build_catalog_modules
from modules.defense.process_monitor import ProcessMonitorModule

# Short aliases kept for agent convenience / backward compatibility.
LEGACY_CLASSES: list[Type[AttackModule]] = [
    KerberoastingModule,
    NtlmRelayModule,
    DpapiModule,
    DeviceCodeModule,
    WifiModule,
    C2Module,
    WebScannerModule,
    LlmRedteamModule,
    ProcessMonitorModule,
]

ALIASES: dict[str, str] = {
    "kerberoasting": "performing-kerberoasting-attack",
    "ntlm_relay": "relaying-ntlm-for-adcs-esc8",
    "dpapi": "abusing-dpapi-for-credential-access",
    "device_code": "attacking-oauth-with-device-code-phishing",
    "wifi": "performing-wifi-password-cracking-with-aircrack",
    "llm_redteam": "red-teaming-llms-with-garak",
    "c2": "building-red-team-c2-infrastructure-with-havoc",
}


def build_registry() -> Dict[str, AttackModule]:
    registry: Dict[str, AttackModule] = {}

    for mod in build_catalog_modules():
        registry[mod.name] = mod

    # Legacy short names remain callable.
    for cls in LEGACY_CLASSES:
        instance = cls()
        registry[instance.name] = instance

    return registry


def resolve_module_name(name: str) -> str:
    return ALIASES.get(name, name)
