"""Module registry."""

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
from modules.defense.process_monitor import ProcessMonitorModule

MODULE_CLASSES: list[Type[AttackModule]] = [
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


def build_registry() -> Dict[str, AttackModule]:
    registry: Dict[str, AttackModule] = {}
    for cls in MODULE_CLASSES:
        instance = cls()
        registry[instance.name] = instance
    return registry
