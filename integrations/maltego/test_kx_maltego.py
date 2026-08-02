#!/usr/bin/env python3
"""Test kx-Defender Maltego Transform — 27개 명령어 검증"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kx_maltego_transform import (
    KxCommand, KxFamily, Scope, ExecutionMode, COMMAND_HANDLERS, execute_transform
)

def test_cmd(name: str, family: KxFamily) -> bool:
    """Test single command"""
    try:
        cmd = KxCommand(name=name, family=family, scope=Scope.LAB, mode=ExecutionMode.SIMULATION)
        results = execute_transform(cmd)
        if results:
            entity_types = [r.get("@type") for r in results]
            print(f"  [OK] {name}: {', '.join(entity_types)}")
            return True
        else:
            print(f"  [FAIL] {name}: no output")
            return False
    except Exception as e:
        print(f"  [FAIL] {name}: {str(e)}")
        return False

def main():
    print("=" * 70)
    print("kx-Defender Maltego Transform TEST (27 Commands)")
    print("=" * 70)
    print()

    # Attack (7)
    print("[ATTACK] 7 commands")
    attack = ["roast", "relay", "loot", "bait", "breach", "crack", "nexus"]
    a_pass = sum(test_cmd(c, KxFamily.ATTACK) for c in attack)
    print(f"  {a_pass}/{len(attack)} passed")
    print()

    # Defense (10)
    print("[DEFENSE] 10 commands")
    defense = ["sentry", "trace", "audit", "harden", "triage", "comply", "forge", "sig", "watch", "kill"]
    d_pass = sum(test_cmd(c, KxFamily.DEFENSE) for c in defense)
    print(f"  {d_pass}/{len(defense)} passed")
    print()

    # Infrastructure (4)
    print("[INFRASTRUCTURE] 4 commands")
    infra = ["graph", "probe", "sweep"]
    i_pass = sum(test_cmd(c, KxFamily.INFRASTRUCTURE) for c in infra)
    print(f"  {i_pass}/{len(infra)} passed")
    print()

    # Utility (7)
    print("[UTILITY] 7 commands")
    util = ["lexicon", "lang", "update", "help"]
    u_pass = sum(test_cmd(c, KxFamily.UTILITY) for c in util)
    print(f"  {u_pass}/{len(util)} passed")
    print()

    # Summary
    total_cmds = len(attack) + len(defense) + len(infra) + len(util)
    total_pass = a_pass + d_pass + i_pass + u_pass

    print("=" * 70)
    print(f"RESULT: {total_pass}/{total_cmds} passed")
    print(f"Handler Coverage: {len(COMMAND_HANDLERS)} handlers registered")
    print("=" * 70)

    return 0 if total_pass == total_cmds else 1

if __name__ == "__main__":
    sys.exit(main())
