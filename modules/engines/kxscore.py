"""KxScore — self-built behavioral scoring."""

from __future__ import annotations

from typing import Any


def score_process(proc: dict[str, Any]) -> dict[str, Any]:
    """Return 0-100 suspicion score for a process snapshot row."""
    score = 0
    reasons: list[str] = []
    name = (proc.get("name") or "").lower()
    cmd = (proc.get("cmdline") or "").lower()
    blob = f"{name} {cmd}"

    checks = [
        (20, "powershell" in name or "pwsh" in name, "powershell_host"),
        (25, "-enc" in cmd or "frombase64string" in cmd, "encoded_command"),
        (15, "http://" in cmd or "https://" in cmd, "network_download_hint"),
        (30, "mimikatz" in blob or "sekurlsa" in blob, "credential_dump_hint"),
        (10, name.endswith(".tmp") or "appdata\\local\\temp" in cmd, "temp_path"),
        (15, "kx_lab_malicious_marker" in blob, "lab_marker"),
    ]
    for points, cond, reason in checks:
        if cond:
            score += points
            reasons.append(reason)
    score = min(score, 100)
    level = "low"
    if score >= 70:
        level = "critical"
    elif score >= 45:
        level = "high"
    elif score >= 25:
        level = "medium"
    return {"score": score, "level": level, "reasons": reasons}
