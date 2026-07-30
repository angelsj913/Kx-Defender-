# Kx-Defender Implementation Guide for Cursor

This guide provides step-by-step implementation instructions for completing the Kx-Defender backend system. The work is organized by priority and dependencies.

## Project Overview

**Status**: Core infrastructure complete (273 modules registered), system operational
**Next**: Complete remaining attack modules, optimize performance, add advanced features
**Target Timeline**: 12 weeks from project start

---

## Phase 1: Core System Validation (Week 1-2)

### 1.1 Command Flow Validation

**Current State**: ✓ Complete
- KxLang parser working (20 verbs, 60+ objects)
- Orchestrator routing functional
- 273 modules registered and callable
- Base module infrastructure in place

**Action Items**:
- [ ] Run integration tests for all 20 verbs
- [ ] Verify scope enforcement on each module
- [ ] Test simulate mode vs execute mode behavior
- [ ] Validate error handling and edge cases
- [ ] Create comprehensive test suite

**Test Coverage Needed**:
```python
# tests/test_command_flow.py
def test_all_verbs_parse()
def test_all_objects_resolve()
def test_scope_enforcement()
def test_mode_switching()
def test_error_handling()
def test_result_persistence()
```

**Success Criteria**:
- [ ] All 20 verbs parse without errors
- [ ] All 60+ objects resolve to valid modules
- [ ] Scope enforcement prevents unauthorized access
- [ ] Execute mode requires explicit --live flag
- [ ] Results stored in SQLite correctly

### 1.2 Database & Persistence

**Current State**: ✓ Partially complete
- RunStore class exists
- SQLite schema defined
- Basic persistence working

**Action Items**:
- [ ] Review RunStore implementation
- [ ] Add database indexing for performance
- [ ] Implement result pagination
- [ ] Add query filtering (by status, date, module)
- [ ] Create backup/export functionality

**Database Optimization**:
```sql
-- Add indexes for common queries
CREATE INDEX idx_runs_created_at ON runs(created_at DESC);
CREATE INDEX idx_runs_module ON runs(module);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_scope ON runs(authorized_scope);

-- Add aggregate views
CREATE VIEW v_stats_by_module AS
SELECT module, status, COUNT(*) as count, 
       AVG(duration_ms) as avg_duration
FROM runs
GROUP BY module, status;
```

**Success Criteria**:
- [ ] Query latency < 100ms for last 100 runs
- [ ] Full-text search on findings
- [ ] Export to JSON/CSV in < 500ms
- [ ] Database file size < 100MB after 1000 runs

### 1.3 Error Handling & Logging

**Current State**: Basic error handling exists

**Action Items**:
- [ ] Implement structured logging (JSON format)
- [ ] Add audit trail for all operations
- [ ] Create error categorization system
- [ ] Implement retry logic for transient failures
- [ ] Add metric collection (success/error rates)

**Logging Structure**:
```python
# services/orchestrator/kx_defender/logging.py
class KxLogger:
    def command_executed(self, cmd, result, duration_ms)
    def module_error(self, module, error, params)
    def scope_denied(self, scope, required_scope, user)
    def performance_warning(self, operation, duration_ms)
```

**Metrics to Track**:
- Command success/error rate by verb
- Average execution time by module
- Scope authorization denials
- Most common errors
- Peak command throughput

---

## Phase 2: Attack Modules Implementation (Week 3-5)

### 2.1 Kerberoasting Module

**Current State**: ✓ Complete
- Module: `modules/attack/kerberoasting.py`
- Verb: `roast`, Object: `tickets` or `spn`
- Supports: Simulate and fixture-based execute

**Status**: READY FOR USE
- Mock SPN enumeration in simulate mode
- Fixture-based real SPN data when available
- TGS hash generation using SHA256

**Testing**:
```bash
kx roast tickets --scope lab --sim
kx roast spn --scope owned --live --realm internal.corp
```

### 2.2 NTLM Relay Module

**Current State**: ✓ Complete
- Module: `modules/attack/ntlm_relay.py`
- Verb: `relay`, Object: `esc8` or `ntlm`
- Simulates ADCS ESC8 exploitation

**Status**: READY FOR USE
- Protocol-level NTLM implementation
- ADCS ESC8 certificate request workflow
- No external Impacket dependency

**Testing**:
```bash
kx relay esc8 --scope lab --sim
kx relay ntlm --scope owned --live --url http://ca.corp
```

### 2.3 DPAPI Extraction Module

**Current State**: ✓ Complete
- Module: `modules/attack/dpapi.py`
- Verb: `loot`, Object: `vault` or `dpapi`
- Simulates Windows credential extraction

**Status**: READY FOR USE
- Windows API calls for CryptUnprotectData
- DPAPI credential decryption
- Vault/Chrome password extraction simulation

**Testing**:
```bash
kx loot vault --scope lab --sim
kx loot dpapi --scope owned --live --target user@corp.local
```

### 2.4 OAuth Device Code Module

**Current State**: ✓ Complete
- Module: `modules/attack/device_code.py`
- Verb: `bait`, Object: `dcode` or `oauth`
- Mock OAuth device flow

**Status**: READY FOR USE
- Local mock IdP (no real cloud API keys)
- Device code generation
- User code flow simulation

**Testing**:
```bash
kx bait dcode --scope lab --sim
kx bait oauth --scope owned --live --target mock.idp.local
```

### 2.5 WiFi Cracking Module

**Current State**: ✓ Complete
- Module: `modules/attack/wifi.py`
- Verb: `crack`, Object: `wifi` or `wpa`
- Aircrack-ng simulation

**Status**: READY FOR USE
- WPA password cracking simulation
- Handshake collection mock
- Dictionary attack workflow

**Testing**:
```bash
kx crack wifi --scope lab --sim
kx crack wpa --scope lab --live --essid "TestNetwork"
```

### 2.6 Microsoft Graph Exploitation Module

**Current State**: ✓ Complete
- Module: `modules/attack/graph.py` (via handlers)
- Verb: `graph`, Object: `pull`, `mail`, or `drive`
- Post-exploitation via Graph API

**Status**: READY FOR USE
- Mock Graph token operations
- Mail/Drive/Teams data collection simulation
- No real cloud API keys used

**Testing**:
```bash
kx graph pull --scope lab --sim
kx graph mail --scope owned --live --url https://graph.microsoft.com
```

### 2.7 Entra ID Breach Module

**Current State**: ✓ Complete
- Module: Various (via handlers)
- Verb: `breach`, Object: `entra` or `aad`
- Entra ID reconnaissance

**Status**: READY FOR USE
- Directory user enumeration
- Application enumeration
- Token operation workflow

**Testing**:
```bash
kx breach entra --scope lab --sim
kx breach aad --scope owned --live --realm contoso.com
```

### 2.8 LLM Red-Team Module

**Current State**: ✓ Complete
- Module: `modules/attack/llm_redteam.py`
- Verb: `probe`, Object: `mind`, `llm`, or `garak`
- LLM prompt injection testing

**Status**: READY FOR USE
- Prompt injection payload generation
- Jailbreak attempt simulation
- Token stealing scenarios

**Testing**:
```bash
kx probe llm --scope lab --sim
kx probe mind --scope owned --live --url http://model-api:8000
```

### 2.9 C2 / Nexus Infrastructure

**Current State**: ✓ Complete
- Module: `modules/attack/c2.py`
- Verb: `nexus`, Objects: `listen`, `havoc`, `sliver`, `status`
- C2 listener and session management

**Status**: READY FOR USE
- Listener registration (loopback only for execute mode)
- Session bookkeeping
- Echo-only protocol (no implants generated)

**Testing**:
```bash
kx nexus listen --scope lab --sim
kx nexus havoc --scope owned --live --bind 127.0.0.1:4455
kx nexus status --scope lab --sim
```

**Incomplete Features** (Out of Scope):
- Actual implant generation
- Shellcode encoding/obfuscation
- AMSI bypass implementation
- Beacon communication protocol

---

## Phase 3: Defense Modules Enhancement (Week 6-8)

### 3.1 Process Monitoring (KxWatch)

**Current State**: ✓ Functional
- Module: `modules/defense/process_monitor.py`
- Verb: `watch`, Object: `procs` or `process`
- Engine: KxWatch + KxScore

**Enhancements Needed**:
- [ ] Real Windows process enumeration via psutil
- [ ] Parent-child process tree visualization
- [ ] Command-line argument capture
- [ ] Memory/CPU usage tracking
- [ ] Network connection association
- [ ] Code signing verification

**Code Structure**:
```python
# modules/engines/kxwatch.py
class KxWatch:
    def list_processes(limit=200) -> list[ProcessInfo]
    def get_process_tree() -> ProcessTree
    def get_network_connections(pid) -> list[Connection]
    def check_code_signing(pid) -> SigningInfo
```

**Testing**:
```bash
kx watch procs --scope lab --sim
kx watch process --scope owned --live --limit 500
```

### 3.2 Process Termination (KxAction)

**Current State**: ✓ Functional
- Module: `modules/defense/process_kill.py`
- Verb: `kill`, Object: `pid` or `proc`
- Engine: KxAction

**Features**:
- Process termination by PID
- Cascade termination of child processes
- Force kill if graceful termination fails
- Result verification

**Code Structure**:
```python
# modules/engines/kxaction.py
class KxAction:
    def terminate(pid: int, force: bool = False) -> bool
    def terminate_tree(pid: int) -> TerminationResult
    def verify_terminated(pid: int) -> bool
```

**Safety Features**:
- Scope enforcement (owned/engagement only)
- System process protection (no kill on system processes)
- Dry-run mode (simulate without killing)

**Testing**:
```bash
kx kill pid --scope lab --sim --pid 1234
kx kill proc --scope owned --live --pid 5678 --with force=true
```

### 3.3 Signature Scanning (KxSig)

**Current State**: ✓ Functional
- Module: `modules/defense/sig_scan.py`
- Verb: `sig`, Object: `scan` or `file`
- Engine: KxSig

**Current Implementation**:
- YARA-like signature syntax
- File or text scanning
- Configurable rules

**Enhancements**:
- [ ] Add 1000+ default rules
- [ ] Support for Yara syntax compatibility
- [ ] Recursive directory scanning
- [ ] Performance optimization (< 100ms per MB)
- [ ] Multi-pattern matching
- [ ] Severity-based rule scoring

**Rule Definition Format**:
```json
{
  "name": "Suspicious PowerShell Encoding",
  "severity": "high",
  "pattern": "-enc\\s+[A-Za-z0-9+/=]{100,}",
  "category": "execution",
  "mitre_techniques": ["T1059", "T1027"]
}
```

**Testing**:
```bash
kx sig scan --scope lab --sim --with sample="powershell -enc AAAA"
kx sig file --scope owned --live --path /windows/temp/sample.exe
```

### 3.4 Detection Rules (Sentry)

**Current State**: Catalog skills available (18 detection modules)

**Enhancement Areas**:
- [ ] Real-time process monitoring for suspicious patterns
- [ ] Authentication anomaly detection
- [ ] API enumeration detection
- [ ] Cloud trail analysis
- [ ] Prompt injection detection
- [ ] ARP poisoning detection
- [ ] SCADA attack detection

**Rule Engine Architecture**:
```python
# modules/engines/kxdetect.py
class DetectionEngine:
    def detect_anomalous_auth(events) -> list[Finding]
    def detect_api_enumeration(requests) -> list[Finding]
    def detect_prompt_injection(prompts) -> list[Finding]
```

---

## Phase 4: Web Security & Advanced Features (Week 9-10)

### 4.1 Web Scanner Enhancement (KxSweep)

**Current State**: ✓ Functional
- Module: `modules/attack/web_scanner.py`
- Verb: `sweep`, Objects: `web`, `xss`, `sqli`, `jwt`, `xxe`, `redirect`, `bac`, `prompt-leak`
- Engine: KxSweep

**Current Capabilities**:
- Custom HTML crawler
- SQLi/XSS/CSRF payload injection
- Response analysis
- Form discovery

**Enhancements Needed**:
- [ ] Add JWT vulnerability testing
- [ ] XXE injection detection
- [ ] Open redirect testing
- [ ] Broken access control detection
- [ ] System prompt leakage detection
- [ ] Request deduplication
- [ ] Rate limiting / throttling
- [ ] Proxy/MITM mode support

**Payload Database**:
```python
# modules/attacks/web_payloads.py
XSS_PAYLOADS = [
    '"><svg/onload=alert(1)>',
    '<script>alert(1)</script>',
    'javascript:alert(1)',
    # ... 20+ more
]

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "1' UNION SELECT NULL--",
    "1; DROP TABLE users--",
    # ... 20+ more
]

XXIE_PAYLOADS = [
    '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
    # ... more
]
```

**Testing**:
```bash
kx sweep web --scope lab --sim --url http://target:8080
kx sweep xss --scope lab --live --url http://target/search
kx sweep sqli --scope lab --live --url http://target/api
```

### 4.2 Analytics & Threat Analysis

**Current State**: Catalog skills available (70+ analysis modules)

**Trace Verb Enhancements**:
- [ ] MITRE ATT&CK mapping
- [ ] Malware network analysis
- [ ] CobaltStrike profile analysis
- [ ] Registry artifact analysis
- [ ] Heap spray analysis

**Graph Verb Enhancements**:
- [ ] Mail threading analysis
- [ ] Drive access pattern analysis
- [ ] Teams communication mapping

---

## Phase 5: Performance & Optimization (Week 11)

### 5.1 Caching Strategy

**Implement Module-Level Caching**:
```python
# services/orchestrator/kx_defender/cache.py
class ModuleCache:
    def get_cached_result(module, params_hash) -> ModuleResult | None
    def cache_result(module, params_hash, result, ttl_seconds)
    def invalidate(module)
```

**Cache Targets**:
- Kerberoasting SPN enumeration (cache 5 minutes)
- Process lists (cache 30 seconds)
- Signature rules (cache duration of session)
- Lexicon parsing (cache permanently until restart)

### 5.2 Async Execution

**Long-Running Operations**:
- Web scanner on large sites (> 1000 pages)
- Signature scanning on large files
- Graph data collection

**Implementation**:
```python
# Use asyncio for I/O-bound operations
async def scan_large_site(url, max_pages=1000):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_page(session, page_url) for page_url in pages]
        results = await asyncio.gather(*tasks)
```

### 5.3 Memory Optimization

**Targets**:
- Stream large result sets instead of loading in memory
- Use generators for artifact enumeration
- Implement memory pooling for frequently-used objects

---

## Phase 6: Testing & Validation (Week 12)

### 6.1 Unit Tests

```python
# tests/test_modules/
# - test_attack_modules.py
# - test_defense_modules.py
# - test_engines.py
# - test_orchestrator.py

# Target: 80% code coverage
```

### 6.2 Integration Tests

```python
# tests/test_integration/
# - test_command_flow.py
# - test_scope_enforcement.py
# - test_result_persistence.py
# - test_error_handling.py
```

### 6.3 Performance Benchmarks

```bash
# Benchmark command execution speed
# pytest tests/benchmarks/test_performance.py --benchmark-only

# Test suite execution time
# pytest tests/ --timeout=60
```

---

## Implementation Priority Matrix

| Component | Priority | Effort | Impact | Status |
|-----------|----------|--------|--------|--------|
| Core command flow | P0 | Small | Critical | ✓ Done |
| Attack modules (all) | P0 | Medium | Critical | ✓ Done |
| Defense modules (core) | P0 | Medium | Critical | ✓ Done |
| Web scanner enhance | P1 | Medium | High | In Progress |
| Performance optimization | P1 | Medium | High | Planned |
| Testing & CI/CD | P1 | Large | High | Planned |
| Async execution | P2 | Large | Medium | Planned |
| Batch playbooks | P2 | Large | Medium | Planned |
| Dashboard/UI | P3 | Large | Medium | Planned |
| Advanced analytics | P3 | Large | Low | Planned |

---

## Code Organization

```
/home/user/Kx-Defender-/
├── services/orchestrator/kx_defender/
│   ├── __init__.py
│   ├── base.py                 # BaseModule, AttackModule, DefenseModule
│   ├── orchestrator.py         # Main execution engine
│   ├── registry.py             # Module registration
│   ├── kxlang.py              # Command parser
│   ├── kx_cli.py              # CLI entry point
│   ├── cli.py                 # Argparse-based CLI
│   ├── result.py              # ModuleResult, Finding
│   ├── auth.py                # Authorization/scope checking
│   ├── store.py               # SQLite persistence
│   ├── i18n.py                # Internationalization
│   └── logging.py             # Audit logging (NEW)
│
├── modules/
│   ├── attack/
│   │   ├── kerberoasting.py   # ✓ Complete
│   │   ├── ntlm_relay.py      # ✓ Complete
│   │   ├── dpapi.py           # ✓ Complete
│   │   ├── device_code.py     # ✓ Complete
│   │   ├── wifi.py            # ✓ Complete
│   │   ├── web_scanner.py     # ✓ Complete (enhancing)
│   │   ├── c2.py              # ✓ Complete
│   │   ├── llm_redteam.py     # ✓ Complete
│   │   └── __init__.py
│   │
│   ├── defense/
│   │   ├── process_monitor.py # ✓ Complete
│   │   ├── process_kill.py    # ✓ Complete
│   │   ├── sig_scan.py        # ✓ Complete
│   │   └── __init__.py
│   │
│   ├── engines/
│   │   ├── kxwatch.py         # Process monitoring
│   │   ├── kxscore.py         # Behavioral scoring
│   │   ├── kxaction.py        # Process termination
│   │   ├── kxsig.py           # Signature scanning
│   │   ├── kxsweep.py         # Web scanning
│   │   ├── kxnexus.py         # C2 management
│   │   ├── kxdetect.py        # Detection rules (NEW)
│   │   ├── cache.py           # Caching layer (NEW)
│   │   └── report.py          # Finding reporting
│   │
│   ├── catalog/
│   │   ├── factory.py         # Dynamic module factory
│   │   ├── handlers.py        # Handler functions by family
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── fixtures/
│   ├── catalog/
│   │   ├── kxlang_lexicon.json      # Verb/object definitions
│   │   └── skills.json               # Skill catalog
│   ├── ad/                           # Active Directory test data
│   ├── web/                          # Web testing fixtures
│   └── malware/                      # Sample signatures
│
├── tests/
│   ├── test_command_flow.py         # Integration tests
│   ├── test_modules.py              # Module unit tests
│   ├── test_scope.py                # Authorization tests
│   ├── test_persistence.py          # Database tests
│   └── benchmarks/
│       └── test_performance.py      # Performance tests
│
└── docs/
    ├── ARCHITECTURE.md              # System design
    ├── UI-DESIGN.md                 # Frontend specification
    └── IMPLEMENTATION-GUIDE.md      # This file
```

---

## Git Workflow

### Branch Strategy
```
main                    (production, stable)
  ↓
dev/kx-implementation   (integration branch)
  ├─ feature/attack-*   (attack modules)
  ├─ feature/defense-*  (defense modules)
  ├─ feature/web-*      (web scanner)
  ├─ feature/perf-*     (performance)
  └─ feature/testing-*  (test suite)
```

### Commit Message Format
```
type: subject (50 chars max)

body: Detailed explanation (wrap at 72 chars)

Fixes #123
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `perf`: Performance improvement
- `test`: Test additions
- `docs`: Documentation
- `refactor`: Code restructuring

---

## Success Criteria

### MVP (Weeks 1-6)
- [ ] All 20 verbs working end-to-end
- [ ] 273 modules registered and callable
- [ ] Scope enforcement functional
- [ ] Simulate/execute modes working
- [ ] Results persisted correctly
- [ ] 80% test coverage

### Phase 2 (Weeks 7-10)
- [ ] Web scanner enhancements complete
- [ ] Performance optimizations (< 200ms avg)
- [ ] Async execution for long operations
- [ ] Caching implemented (20% faster)

### Polish (Week 11-12)
- [ ] Full test suite passing
- [ ] Performance benchmarks green
- [ ] Documentation complete
- [ ] CI/CD pipeline configured

---

## Debugging Tips

### Common Issues

**Module not found**:
```bash
# Check registry
python3 -c "from kx_defender.orchestrator import Orchestrator; \
o = Orchestrator(); print([m['name'] for m in o.list_modules()])" | grep module_name
```

**Command parsing fails**:
```bash
python3 -c "from kx_defender.kxlang import parse_argv; \
cmd = parse_argv(['verb', 'obj', '--scope', 'lab']); \
print(f'Module: {cmd.module}, Params: {cmd.params}')"
```

**Scope enforcement not working**:
```bash
# Check auth layer
python3 -c "from kx_defender.auth import validate_params; \
validate_params({'authorized_scope': 'invalid'})"  # Should error
```

**Slow performance**:
```bash
# Profile module execution
python3 -m cProfile -s cumtime services/orchestrator/kx_defender/cli.py attack run test_module
```

---

## Questions & Escalations

For unclear specifications or blockers:
1. Check ARCHITECTURE.md for design decisions
2. Review existing module implementations for patterns
3. Check UI-DESIGN.md for expected behavior
4. Refer to KX-COMMANDS.md for command specifications
5. Ask in pull request review comments

---

## Resources

- **KxLang Lexicon**: fixtures/catalog/kxlang_lexicon.json
- **Skills Catalog**: fixtures/catalog/skills.json
- **Example Modules**: modules/attack/kerberoasting.py
- **Test Fixtures**: fixtures/ad/, fixtures/web/
- **Architecture**: ARCHITECTURE.md
- **Commands**: KX-COMMANDS.md
- **PRD**: PRD-KX-DEFENDER-V2.md
