# kx-Defender → Maltego Graph 통합

kx-Defender 27개 모든 명령어 → Maltego entity 변환 + 역추적 그래프

---

## 📋 파일 구성

| 파일 | 용도 |
|------|------|
| `kx_maltego_transform.py` | Transform 실행 |
| `kx_maltego_graph.mmd` | 실행 흐름 diagram |
| `kx_command_mapping.csv` | 명령어 메타데이터 |

---

## 🛠️ 빠른 시작

### Python 실행

```bash
python kx_maltego_transform.py roast
python kx_maltego_transform.py sig
python kx_maltego_transform.py watch
```

### Maltego Import

1. Menu → Import → CSV
2. `kx_command_mapping.csv` 선택
3. `command_name` → Input entity mapping

---

## 🔴 ATTACK (7)

| # | 명령어 | 출력 |
|---|--------|------|
| 1 | roast tickets | KxThreat, KxAlert |
| 2 | relay | KxThreat |
| 3 | loot | KxFinding |
| 4 | bait | KxAlert |
| 5 | breach | KxThreat |
| 6 | crack | KxFinding |
| 7 | nexus listen | KxNetwork |

## 🟢 DEFENSE (10)

| # | 명령어 | 출력 |
|---|--------|------|
| 8 | sentry | KxAlert |
| 9 | trace | KxProcess, KxAlert |
| 10 | audit | KxFinding |
| 11 | harden | KxExecution |
| 12 | triage | KxFinding |
| 13 | comply | KxFinding |
| 14 | forge | KxExecution |
| 15 | sig scan | KxFinding |
| 16 | watch procs | KxProcess, KxAlert |
| 17 | kill pid | KxProcess, KxExecution |

## 🌐 INFRASTRUCTURE (4)

| # | 명령어 | 출력 |
|---|--------|------|
| 18 | graph | KxNetwork |
| 19 | probe | KxNetwork, KxFinding |
| 20 | sweep web | KxFinding |

## ⚙️ UTILITY (7)

| # | 명령어 | 출력 |
|---|--------|------|
| 21 | lexicon | KxExecution |
| 22 | lang | KxExecution |
| 23 | update | KxExecution |
| 24 | help | KxExecution |
| 25 | exit | none |

---

## 📊 Entity 타입

### KxExecution
```json
{
  "execution_id": "roast_lab.local_ms",
  "timestamp": "2026-08-02T18:25:23Z",
  "command": "roast tickets",
  "scope": "lab",
  "mode": "sim",
  "status": "success",
  "duration_ms": 1500
}
```

### KxThreat
```json
{
  "threat_id": "roast_lab.local_ms",
  "threat_type": "kerberoasting",
  "severity": "high",
  "description": "Kerberos roasting detected",
  "indicators": ["SPN:lab.local", "ticket_request_abuse"]
}
```

### KxFinding
```json
{
  "finding_id": "sig_scan_ms",
  "severity": "high",
  "category": "malware",
  "title": "Malware detected",
  "remediation": "Quarantine immediately"
}
```

### KxAlert
```json
{
  "alert_id": "watch_1234_ms",
  "alert_type": "process_monitoring",
  "severity": "medium",
  "process_name": "powershell.exe",
  "message": "Anomaly detected"
}
```

### KxProcess
```json
{
  "pid": 1234,
  "name": "powershell.exe",
  "threat_score": 78.5,
  "status": "running"
}
```

### KxNetwork
```json
{
  "host": "192.168.1.100",
  "port": 445,
  "service": "smb",
  "status": "open"
}
```

---

## 💻 사용 예시

### Python

```python
from kx_maltego_transform import KxCommand, KxFamily, Scope, ExecutionMode, execute_transform

cmd = KxCommand(
    name="roast",
    family=KxFamily.ATTACK,
    scope=Scope.LAB,
    mode=ExecutionMode.SIMULATION,
    options={"realm": "lab.local"}
)

results = execute_transform(cmd)
# → [KxThreat, KxAlert] entities
```

### Batch

```python
commands = ["roast", "trace", "sweep"]
for cmd_name in commands:
    cmd = KxCommand(name=cmd_name, family=KxFamily.ATTACK)
    results = execute_transform(cmd)
    print(results)
```

---

## 🎯 역추적 체인

### Attack Chain
```
roast → relay → loot → nexus
```

**Maltego:**
```
KxCommand:roast 
  → KxThreat:kerberoasting
    → KxCommand:relay 
      → KxThreat:ntlm_relay
        → KxCommand:loot
          → KxFinding:secrets_extracted
            → KxCommand:nexus
              → KxNetwork:c2_listening
```

### Detection Chain
```
watch → trace → triage → harden
```

**Maltego:**
```
KxCommand:watch 
  → KxAlert:process_anomaly
    → KxCommand:trace
      → KxAlert:behavior_suspicious
        → KxCommand:triage
          → KxFinding:classified
            → KxCommand:harden
              → KxExecution:success
```

---

## 🔒 권한 검증

```
1. Scope:  lab|owned|pact
2. Mode:   sim|live
3. Host:   localhost|RFC1918|.local/.test/.lab
```

---

## 📖 상세 문서

- kx-Defender: https://github.com/angelsj913/kx-Defender-
- Maltego: https://docs.maltego.com/
- Mermaid: https://mermaid.js.org/

**버전**: 1.0 | **작성**: 2026-08-02
