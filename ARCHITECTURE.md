# Kx-Defender System Architecture

## Overview

Kx-Defender is a comprehensive security lab platform with integrated attack simulation, defense mechanisms, web security testing, C2 infrastructure, and threat analytics. The system uses a command-centric architecture with KxLang (DEFCOM) as the primary interface language.

## Core Principles

1. **Self-Built Everything**: No external APIs or proprietary libraries for core protocols
   - Kerberos: ASN.1 direct implementation
   - NTLM: Protocol-level relay
   - OAuth: Device-code flow simulation
   - Web scanning: Custom crawler + payload detection
   - YARA-like: Self-built signature engine
   - Process monitoring: Windows API direct calls

2. **Layered Safety**
   - Simulation mode (--sim): Default, safe for all operations
   - Live mode (--live): Requires explicit scope authorization (lab/owned/pact/engagement)
   - Scope validation: Authorization layer prevents unauthorized access

3. **Modular Design**
   - Attack modules: 30+ implementations
   - Defense modules: 240+ implementations  
   - Catalog skills: Dynamic module factory for flexibility
   - Handler pattern: Family-based routing for specialization

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                           │
│  ┌──────────────┬──────────────┬──────────────┐              │
│  │  PowerShell  │  Web Browser │  CLI/Terminal│              │
│  └──────┬───────┴──────┬───────┴──────┬───────┘              │
└─────────┼──────────────┼──────────────┼──────────────────────┘
          │              │              │
┌─────────┼──────────────┼──────────────┼──────────────────────┐
│  Command Translation Layer                                   │
│  ┌────────────────────────────────────────────────┐          │
│  │  KxLang Parser (DEFCOM)                        │          │
│  │  - Tokenization: verb object --flags           │          │
│  │  - Lexicon resolution: verb→module mapping    │          │
│  │  - Parameter validation & defaults            │          │
│  └────────────────────────────────────────────────┘          │
└─────────────┬──────────────────────────────────────────────────┘
              │
┌─────────────┼──────────────────────────────────────────────────┐
│  Orchestration Layer                                           │
│  ┌────────────────────────────────────────────────┐           │
│  │  Orchestrator                                  │           │
│  │  - Module registry (build_registry)            │           │
│  │  - Execution routing                           │           │
│  │  - Authorization enforcement                  │           │
│  │  - Result persistence                         │           │
│  └────────────────────────────────────────────────┘           │
└─────────────┬──────────────────────────────────────────────────┘
              │
┌─────────────┴───────────────────────────────────────────────────┐
│  Module Layer (273 Modules Total)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Attack Modules (30)          Defense Modules (243)            │
│  ├─ Kerberoasting            ├─ Detecting (18)                │
│  ├─ NTLM Relay               ├─ Analyzing (70)                │
│  ├─ DPAPI Extraction         ├─ Auditing (12)                 │
│  ├─ OAuth Device Code        ├─ Securing (8)                  │
│  ├─ WiFi Cracking            ├─ Triaging (4)                  │
│  ├─ C2/Nexus                 ├─ Compliance (6)                │
│  ├─ Web Scanning             ├─ Building Defense (50+)        │
│  ├─ LLM Red-Team             └─ Specialized (65+)             │
│  └─ Graph Post-Exploit                                        │
│                                                                 │
└─────────────┬───────────────────────────────────────────────────┘
              │
┌─────────────┴───────────────────────────────────────────────────┐
│  Engine Layer                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ├─ KxWatch: Process monitoring & behavioral analysis         │
│  ├─ KxScore: Behavioral risk scoring                          │
│  ├─ KxAction: Process termination & Windows API calls        │
│  ├─ KxSig: Custom YARA-like signature scanning               │
│  ├─ KxSweep: Web crawler & vulnerability detection           │
│  ├─ KxNexus: C2 listener & session management                │
│  ├─ KxBreach: Entra/AAD reconnaissance                       │
│  ├─ KxGraph: Microsoft Graph post-exploitation               │
│  ├─ KxProbe: LLM attack probe vectors                        │
│  └─ KxReport: Finding/artifact reporting                     │
│                                                                 │
└─────────────┬───────────────────────────────────────────────────┘
              │
┌─────────────┴───────────────────────────────────────────────────┐
│  Persistence & Storage                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ├─ RunStore (SQLite): Execution results & findings           │
│  ├─ NexusStore: Session & listener management                 │
│  ├─ Fixtures: Lab data (AD, malware samples, etc)             │
│  └─ Artifacts: Generated data exports                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Command Flow

```
User Input: kx roast tickets --scope lab --sim
    ↓
KxLang Parser
  - Extract: verb="roast", object="tickets", flags
  - Lexicon lookup: roast@tickets → "performing-kerberoasting-attack"
  - Resolve scope: "lab" → authorized_scope="lab"
  ↓
KxCommand Object
  {
    verb: "roast",
    obj: "tickets",
    module: "performing-kerberoasting-attack",
    params: {
      mode: "simulate",
      authorized_scope: "lab",
      domain: "lab.local"
    }
  }
  ↓
Orchestrator.run(module_name, params)
  - Lookup: registry["performing-kerberoasting-attack"] → KerberoastingModule
  - Execute: module.execute(params)
    - Validate params via auth layer
    - Call module.run(params)
  ↓
Module.run(params)
  - If mode="simulate": Generate mock data
  - If mode="execute": Real execution with Windows API
  - Return ModuleResult(findings, artifacts, status)
  ↓
Orchestrator.persist(result)
  - Save to RunStore (SQLite)
  ↓
Response JSON
  {
    status: "ok",
    module: "performing-kerberoasting-attack",
    findings: [...],
    artifacts: {...},
    kxlang: { verb, obj, module, raw }
  }
```

## Module Categories

### Attack Modules (30)
**Credential Access**
- `kerberoasting`: SPN enumeration + TGS collection
- `ntlm_relay`: NTLM relay to ADCS ESC8
- `dpapi`: DPAPI decryption via CryptUnprotectData
- `device_code`: OAuth device-code phishing
- `wifi`: WiFi password cracking (aircrack sim)

**C2 & Exploitation**
- `c2`: Nexus listener + session manager (no implants)
- `llm_redteam`: LLM prompt injection testing
- `graph`: Microsoft Graph token abuse
- `breach`: Entra ID reconnaissance

**Web Security**
- `web_scanner`: Custom crawler + SQLi/XSS/CSRF detection

### Defense Modules (243)
**Real-Time Detection**
- `process_monitor`: Process snapshot + KxScore behavioral analysis
- `sentry/*`: 18 specialized detection rules

**Post-Incident Analysis**
- `trace/*`: 70 threat analysis modules
- `triage/*`: 4 incident prioritization engines

**Compliance & Hardening**
- `audit/*`: 12 cloud/infrastructure audit rules
- `harden/*`: 8 security hardening playbooks
- `comply/*`: 6 compliance frameworks (CMMC, PCI, NERC)

**Defense Building**
- `forge/*`: 50+ detection/response rule builders

## Key Verbs & Objects

| Verb | Objects | Default | Engine | Category |
|------|---------|---------|--------|----------|
| `roast` | tickets, spn | tickets | KxKerberos | Attack |
| `relay` | esc8, ntlm | esc8 | KxRelay | Attack |
| `loot` | vault, dpapi | vault | KxDPAPI | Attack |
| `bait` | dcode, oauth | dcode | KxOAuth | Attack |
| `crack` | wifi, wpa | wifi | KxWiFi | Attack |
| `nexus` | listen, havoc, sliver, status | status | KxNexus | C2 |
| `watch` | procs, process | procs | KxWatch | Defense |
| `kill` | pid, proc | pid | KxAction | Defense |
| `sig` | scan, file | scan | KxSig | Defense |
| `sweep` | web, xss, sqli, jwt, xxe, redirect, bac | web | KxSweep | Web |
| `sentry` | detect, auth-anomalies, api-enum, cloudtrail | detect | KxDetect | Defense |
| `trace` | analyze, mitre-ttps, malware-net, cobalt-c2 | analyze | KxAnalyze | Defense |
| `audit` | check, s3, entra, k8s-rbac, tls-ct, terraform | check | KxAudit | Defense |
| `harden` | apply, iam, lambda, k8s, gha, agent-tools | apply | KxHarden | Defense |
| `forge` | build, sigma-rules, splunk-rule, siem, ir-playbook | build | KxForge | Defense |
| `triage` | sort, incident, splunk, ssvc, kape | sort | KxTriage | Defense |
| `comply` | map, cmmc, pci, nerc, aws-hub, aws-config | map | KxComply | Defense |
| `probe` | mind, llm, garak | mind | KxProbe | Attack |
| `graph` | pull, mail, drive | pull | KxGraph | Attack |
| `breach` | entra, aad | entra | KxBreach | Attack |

## Module Execution Modes

### Simulate Mode (Default)
- **Purpose**: Safe exploration, lab testing, CI/CD validation
- **Behavior**: Returns synthetic/templated data
- **Example**:
  ```bash
  kx roast tickets --scope lab --sim
  # Returns mock Kerberos SPNs without real network access
  ```

### Execute Mode
- **Purpose**: Real operations within authorized scope
- **Behavior**: Executes against real targets/systems
- **Authorization Check**: Scope must match target environment
- **Example**:
  ```bash
  kx roast tickets --scope owned --live --realm internal.corp
  # Real Kerberos enumeration against owned domain
  ```

## Scope Authorization Model

```
Scope Levels:
  lab         - Fully isolated lab (loopback, fixtures)
  owned       - Organization-owned assets (internal networks, test domains)
  engagement  - Third-party authorized penetration tests
  pact        - Engagement scope (alias for engagement)
```

Module Enforcement:
- Every module validates `authorized_scope` before execution
- Some operations (e.g., process termination) only allowed in `owned`/`engagement`
- Cross-scope execution returns `status="denied"`

## Result Structure

```python
ModuleResult {
  run_id: str                    # UUID
  module: str                    # Module name
  status: "ok"|"error"|"denied"  # Execution status
  mode: "simulate"|"execute"     # Execution mode
  authorized_scope: str          # Scope authorization
  created_at: datetime           # Timestamp
  finished_at: datetime | None   # Completion time
  findings: list[Finding]        # Security findings
  artifacts: dict                # Generated data
  errors: list[str]              # Error messages
  meta: dict                     # Module metadata
}

Finding {
  title: str                     # Finding name
  severity: "info"|"medium"|"high"|"critical"
  detail: str                    # Description
  evidence: dict                 # Supporting data
}
```

## Database Schema (SQLite)

```sql
runs
  ├─ run_id (PK)
  ├─ module
  ├─ status
  ├─ mode
  ├─ authorized_scope
  ├─ created_at
  ├─ finished_at
  └─ data (JSON: findings, artifacts, errors)

listeners
  ├─ listener_id (PK)
  ├─ host
  ├─ port
  ├─ protocol
  ├─ status
  └─ created_at

sessions
  ├─ session_id (PK)
  ├─ listener_id (FK)
  ├─ agent
  ├─ status
  └─ created_at
```

## Extension Points

### Adding a New Command

1. **Add to Lexicon** (fixtures/catalog/kxlang_lexicon.json)
   ```json
   "mynew": {
     "role": "custom",
     "objects": { "action": "my-module-name" },
     "default_object": "action"
   }
   ```

2. **Implement Module** (modules/attack/my_module.py or modules/defense/my_module.py)
   ```python
   class MyModule(AttackModule):
       name = "my-module-name"
       description = "..."
       
       def run(self, params: dict) -> ModuleResult:
           # Simulation & execution logic
           pass
   ```

3. **Register Module** (services/orchestrator/kx_defender/registry.py)
   ```python
   from modules.attack.my_module import MyModule
   LEGACY_CLASSES.append(MyModule)
   ```

4. **Test**
   ```bash
   kx mynew action --scope lab --sim
   ```

### Adding a New Engine

1. Create `modules/engines/kxmyengine.py`
2. Implement specialized functionality
3. Import in relevant modules
4. Example: KxWatch (process monitoring), KxSig (signature scanning)

## Implementation Timeline

**Week 1-2: Foundation**
- ✓ Environment setup (Python 3.12+, SQLite)
- ✓ KxLang parser and lexicon
- ✓ Orchestrator and registry
- ✓ Base module classes

**Week 3-6: Defense Modules**
- ✓ Process monitor (KxWatch)
- ✓ Signature scanner (KxSig)
- ✓ Audit engines (CIS, PCI, etc)
- ✓ Detection playbooks (MITRE TTPs)

**Week 7-9: Attack Modules**
- ✓ Kerberoasting
- ✓ NTLM relay
- ✓ DPAPI extraction
- ✓ OAuth device-code
- WiFi cracking (in progress)

**Week 10-11: Web & C2**
- ✓ Web scanner (KxSweep)
- ✓ C2 listener (KxNexus)
- LLM red-team (KxProbe)
- Graph exploitation

**Week 12: Polish**
- Testing & validation
- Documentation
- UI responsiveness
- Performance optimization

## Performance Targets

- Command parsing: <50ms
- Module execution (simulate): <200ms
- Module execution (execute): varies by operation, <5s typical
- Memory overhead: <200MB for orchestrator
- Concurrent sessions: 50+ simultaneous

## Security Considerations

1. **Input Validation**: All parameters validated at module boundary
2. **Scope Enforcement**: Authorization checked before execution
3. **Resource Limits**: Timeout for long operations, memory caps
4. **Audit Trail**: Every execution logged to SQLite with timestamps
5. **Isolation**: Simulate mode never affects real systems
6. **Credentials**: Sensitive data masked in results/logs

## Testing Strategy

1. **Unit Tests**: Module-specific functionality
2. **Integration Tests**: Command flow (parse → route → execute)
3. **Scope Tests**: Authorization enforcement
4. **Mode Tests**: Simulate vs execute behavior
5. **Performance Tests**: Throughput and latency

---

## Next Steps for Implementation

1. Complete attack module implementations (WiFi, LLM probing)
2. Implement interactive shell with persistent state
3. Add batch operation support (playbooks)
4. Implement export formats (JSON, CSV, YARA rules)
5. Build reactive UI that updates results without regeneration
