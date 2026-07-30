# Kx-Defender 구현 계획 (12주 로드맵)

**최종 목표**: 방어+공격 통합 보안 플랫폼 MVP 완성 (주차 1-12)

---

## Phase 1: 기초 구축 (주차 1-2)

### Week 1: 환경 설정 & 아키텍처

#### Task 1.1: 저장소 구조 확정 ✅ 완료
```
Kx-Defender/
├── src/
│   ├── core/
│   │   ├── defense/           # 방어 모듈
│   │   │   ├── process_monitor.ps1      # WMI 모니터링
│   │   │   ├── process_terminator.py    # 프로세스 차단
│   │   │   ├── behavior_analyzer.py     # 행동 분석
│   │   │   └── yara_engine.py          # 악성코드 탐지
│   │   ├── attack/            # 공격 모듈
│   │   │   ├── kerberoasting.py        # Kerberoasting
│   │   │   ├── ntlm_relay.py          # NTLM Relaying
│   │   │   ├── dpapi.py               # DPAPI 악용
│   │   │   └── oauth_phishing.py      # Device Code 피싱
│   │   ├── scanner/           # 웹 스캐너
│   │   │   └── web_scanner.py         # 커스텀 웹 취약점 스캐너
│   │   └── c2/                # C2 서버
│   │       └── server.go              # C2 Command & Control
│   ├── ui/
│   │   ├── main.ts                    # Electron 메인
│   │   ├── preload.ts                 # IPC 프리로드
│   │   └── app/
│   │       ├── dashboard.tsx          # 메인 대시보드
│   │       ├── defense/               # 방어 UI
│   │       ├── attack/                # 공격 UI
│   │       └── scanner/               # 웹 스캔 UI
│   └── utils/
│       ├── logger.py
│       ├── config.py
│       └── database.py
├── docs/
│   ├── PRD-KX-DEFENDER-V2.md
│   ├── TECHNICAL-APPROACH.md
│   ├── IMPLEMENTATION-PLAN.md
│   ├── API.md
│   ├── CONTRIBUTING.md
│   └── SETUP.md
├── tests/
│   ├── test_defense.py
│   ├── test_attack.py
│   └── test_scanner.py
├── .github/workflows/
│   ├── ci.yml
│   └── security-scan.yml
├── requirements.txt
├── go.mod
├── package.json
├── .gitignore
└── README.md
```

#### Task 1.2: PowerShell ↔ Python 통신 설계 (선택: Named Pipe)

**선택 이유**: 
- ✅ 로컬 통신 (보안)
- ✅ 빠른 응답 (<100ms)
- ✅ Windows 기본 기능 (의존성 없음)

**구현**:
```python
# src/utils/ipc.py

class NamedPipeServer:
    """Named Pipe를 통한 PowerShell ↔ Python 통신"""
    
    def __init__(self, pipe_name=r'\\.\pipe\kxdefender'):
        self.pipe_name = pipe_name
    
    def listen(self):
        """파이프 수신 대기"""
        # Windows Named Pipe 구현
        pass
    
    def send_event(self, event: dict):
        """PowerShell으로부터 받은 이벤트 처리"""
        pass

class ProcessEvent:
    """프로세스 이벤트 모델"""
    event_type: str  # 'created', 'terminated', 'suspended'
    pid: int
    name: str
    command_line: str
    parent_pid: int
    timestamp: datetime
```

#### Task 1.3: SQLite 데이터베이스 스키마 설계

```sql
-- 로그 및 분석 결과 저장

CREATE TABLE processes (
    pid INTEGER PRIMARY KEY,
    name TEXT,
    command_line TEXT,
    parent_pid INTEGER,
    created_at TIMESTAMP,
    terminated_at TIMESTAMP
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    event_type TEXT,  -- 'process_created', 'malware_detected', 'behavior_detected'
    pid INTEGER,
    details TEXT,     -- JSON
    severity TEXT,    -- 'critical', 'high', 'medium', 'low'
    timestamp TIMESTAMP
);

CREATE TABLE detections (
    id INTEGER PRIMARY KEY,
    detection_type TEXT,  -- 'yara', 'behavior', 'block'
    pid INTEGER,
    rule_name TEXT,
    payload TEXT,
    timestamp TIMESTAMP
);

CREATE TABLE c2_sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT,
    remote_ip TEXT,
    last_checkin TIMESTAMP,
    status TEXT  -- 'active', 'inactive', 'dead'
);

CREATE TABLE vulnerabilities (
    id INTEGER PRIMARY KEY,
    scan_id TEXT,
    url TEXT,
    vuln_type TEXT,  -- 'SQLi', 'XSS', 'CSRF'
    parameter TEXT,
    payload TEXT,
    severity TEXT,
    timestamp TIMESTAMP
);
```

### Week 2: 프로세스 모니터링 PoC

#### Task 2.1: PowerShell 프로세스 모니터링 모듈

```powershell
# src/core/defense/process_monitor.ps1

# 목표: 프로세스 생성/종료 이벤트를 JSON으로 직렬화하여 Named Pipe로 전송

# 1. WMI Event 구독
$ProcessCreated = Get-CimClass -Namespace root\cimv2 -ClassName Win32_ProcessStartTrace
$ProcessTerminated = Get-CimClass -Namespace root\cimv2 -ClassName Win32_ProcessStopTrace

# 2. 이벤트 핸들러 등록
Register-CimIndicationEvent -Query "SELECT * FROM Win32_ProcessStartTrace" -Action {
    $event = $Event.SourceEventArgs.NewEvent
    
    # 이벤트 객체 생성
    $processEvent = @{
        event_type = "created"
        pid = $event.ProcessID
        name = $event.ProcessName
        parent_pid = $event.ParentProcessID
        command_line = $event.CommandLine
        timestamp = Get-Date -AsUTC
    }
    
    # JSON 직렬화
    $json = $processEvent | ConvertTo-Json -Compress
    
    # Named Pipe로 전송
    Send-NamedPipeMessage -Message $json
}

# 3. 종료 이벤트도 동일하게 처리
```

#### Task 2.2: Python 이벤트 핸들러

```python
# src/core/defense/event_handler.py

import json
from datetime import datetime

class ProcessEventHandler:
    """PowerShell 이벤트 수신 및 처리"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def handle_process_created(self, event: dict):
        """프로세스 생성 이벤트"""
        pid = event['pid']
        
        # DB에 저장
        self.db.execute("""
            INSERT INTO processes (pid, name, command_line, parent_pid, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (pid, event['name'], event['command_line'], event['parent_pid'], 
              event['timestamp']))
        
        # 이벤트 로깅
        self._log_event('process_created', pid, event)
        
        # 즉시 분석 시작
        self.analyze_process(pid)
    
    def handle_process_terminated(self, event: dict):
        """프로세스 종료 이벤트"""
        pid = event['pid']
        
        # DB에 update
        self.db.execute("""
            UPDATE processes SET terminated_at = ? WHERE pid = ?
        """, (event['timestamp'], pid))
        
        self._log_event('process_terminated', pid, event)
    
    def analyze_process(self, pid: int):
        """
        새 프로세스 분석:
        1. 행동 분석 엔진 실행
        2. YARA 스캔
        3. 위험도 계산
        """
        pass
```

---

## Phase 2: 방어 엔진 (주차 3-6)

### Week 3-4: 행동 분석 엔진

#### Task 3.1: 의심 행동 패턴 정의 (100+ 패턴)

```python
# src/core/defense/behavior_analyzer.py

class BehaviorPatterns:
    """100+ 의심 행동 패턴 정의"""
    
    PATTERNS = {
        'code_injection': {
            'score': 100,
            'description': '코드 인젝션 탐지',
            'indicators': [
                'parent_child_anomaly',      # 부모-자식 관계 비정상
                'memory_allocation',         # VirtualAlloc + CreateRemoteThread
                'image_mismatch',           # 이미지와 메모리 불일치
            ]
        },
        'dll_from_temp': {
            'score': 80,
            'description': '임시 폴더에서 DLL 로드',
            'indicators': [
                'dll_path_startswith_temp',
                'dll_unsigned',              # 서명되지 않은 DLL
            ]
        },
        'parent_process_spoofing': {
            'score': 75,
            'description': '부모 프로세스 스푸핑',
            'indicators': [
                'mismatch_ppid_peb',
                'process_hollowing',         # 프로세스 호로잉
            ]
        },
        'suspicious_network': {
            'score': 70,
            'description': '의심 네트워크 활동',
            'indicators': [
                'connection_to_c2_ip',
                'dns_beaconing',             # DNS 비콘
                'port_scanning',             # 포트 스캔
            ]
        },
        # ... 100+ 더 많은 패턴
    }
    
    @staticmethod
    def detect(process: dict, patterns: list) -> int:
        """
        프로세스 행동 점수 계산
        
        반환: 0-100 (높을수록 악성)
        """
        score = 0
        for pattern in patterns:
            if pattern in BehaviorPatterns.PATTERNS:
                score += BehaviorPatterns.PATTERNS[pattern]['score']
        
        return min(score, 100)
```

#### Task 3.2: 실시간 행동 모니터링

```python
# src/core/defense/runtime_behavior_monitor.py

class RuntimeBehaviorMonitor:
    """프로세스 실행 중 행동 모니터링"""
    
    def monitor_process(self, pid: int):
        """
        특정 PID의 실시간 행동 모니터링
        
        감시 항목:
        1. 메모리 할당 (VirtualAlloc)
        2. 파일 접근 (CreateFileA/W)
        3. 레지스트리 접근 (RegOpenKeyEx)
        4. 네트워크 연결 (WSAConnect)
        5. DLL 로드 (LoadLibraryA/W)
        """
        
        # Windows API 후킹 또는 ETW 사용
        while True:
            # 행동 감지
            behavior = self._detect_behavior(pid)
            
            if behavior:
                # 행동 점수 업데이트
                self._update_behavior_score(pid, behavior)
                
                # 임계값 초과 시 알림
                if self._get_behavior_score(pid) > 80:
                    self._alert_threat(pid)
```

### Week 5: YARA 악성코드 탐지

#### Task 5.1: 커스텀 YARA 규칙 엔진

```python
# src/core/defense/yara_engine.py

class YARAEngine:
    """커스텀 YARA 스캐너"""
    
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> list:
        """기본 1000+ 규칙 로드"""
        return [
            {
                'name': 'Emotet',
                'strings': [b'EMOTET', b'emotet'],
                'severity': 'critical',
            },
            {
                'name': 'TrickBot',
                'patterns': [
                    r'trick.*bot',
                    r'Trick\w+Bot',
                ],
                'severity': 'critical',
            },
            # ... 1000+ 더 많은 규칙
        ]
    
    def scan_process_memory(self, pid: int) -> list:
        """
        프로세스 메모리 스캔
        
        단계:
        1. 프로세스 핸들 획득
        2. 메모리 영역 열거
        3. 각 영역에서 규칙 매칭
        """
        import ctypes
        
        detections = []
        
        # 프로세스 핸들 획득
        handle = ctypes.windll.kernel32.OpenProcess(0x0010, False, pid)  # PROCESS_VM_READ
        
        # 메모리 영역 열거
        address = 0
        while address < 0x7FFFFFFF:
            # VirtualQueryEx로 메모리 영역 조회
            # ReadProcessMemory로 메모리 읽기
            # 규칙 매칭
            pass
        
        return detections
    
    def scan_file(self, file_path: str) -> list:
        """파일 스캔"""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        detections = []
        
        for rule in self.rules:
            for string in rule.get('strings', []):
                if string in data:
                    detections.append({
                        'rule': rule['name'],
                        'severity': rule['severity'],
                        'offset': data.find(string),
                    })
        
        return detections
```

### Week 6: 프로세스 차단 및 제어

#### Task 6.1: 프로세스 강제 종료

```python
# src/core/defense/process_terminator.py

import ctypes

class ProcessTerminator:
    """프로세스 직접 종료"""
    
    @staticmethod
    def terminate(pid: int, timeout: int = 5) -> bool:
        """
        프로세스 정상 종료 시도 → 강제 종료
        
        반환: 성공 여부
        """
        kernel32 = ctypes.windll.kernel32
        
        # 1. 정상 종료 시도
        handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if handle:
            result = kernel32.TerminateProcess(handle, 1)
            kernel32.CloseHandle(handle)
            return bool(result)
        
        return False
    
    @staticmethod
    def kill_protected_process(pid: int) -> bool:
        """
        보호된 프로세스 강제 종료
        
        방법:
        1. 프로세스 메모리 읽기 권한 확인
        2. 메모리 손상 (EntryPoint 무효화)
        3. 프로세스 무효화
        """
        # 고급 기법 (필요시만)
        pass
```

---

## Phase 3: 공격 도구 (주차 7-9)

### Week 7: Kerberoasting

#### Task 7.1: Kerberos 프로토콜 구현

```python
# src/core/attack/kerberoasting.py

from socket import socket, AF_INET, SOCK_DGRAM
import struct

class KerberosClient:
    """Kerberos 프로토콜 직접 구현"""
    
    def __init__(self, domain: str, kdc: str):
        self.domain = domain
        self.kdc = kdc
    
    def enumerate_spns(self) -> list:
        """
        LDAP를 통해 도메인의 모든 SPN 열거
        
        LDAP 쿼리: (servicePrincipalName=*)
        """
        spns = []
        
        # LDAP 연결
        # (socket으로 LDAP 프로토콜 직접 구현)
        
        return spns
    
    def request_tgs(self, spn: str) -> bytes:
        """
        TGS(Ticket Granting Service) 요청
        
        Kerberos 메시지 흐름:
        1. AS-REQ → TGT 획득
        2. TGS-REQ → 서비스 티켓 요청
        3. TGS-REP → 암호화된 티켓 (크래킹용)
        """
        
        # 1. TGT 획득
        tgt = self._get_tgt()
        
        # 2. TGS-REQ 생성
        tgs_req = self._build_tgs_request(spn, tgt)
        
        # 3. KDC로 전송
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.sendto(tgs_req, (self.kdc, 88))
        
        # 4. TGS-REP 수신
        tgs_rep, _ = sock.recvfrom(4096)
        
        # 5. 크래킹 가능 부분 추출
        crackable_part = self._extract_crackable_part(tgs_rep)
        
        return crackable_part
```

### Week 8: NTLM Relaying & DPAPI

#### Task 8.1: NTLM 중계 (ADCS ESC8)

```python
# src/core/attack/ntlm_relay.py

class NTLMRelay:
    """NTLM 중계 공격"""
    
    def start_listeners(self):
        """
        다중 리스너 시작:
        1. SMB 리스너 (445)
        2. HTTP 리스너 (80/443)
        """
        pass
    
    def relay_to_adcs(self, captured_credentials: dict):
        """
        NTLM을 ADCS로 중계
        
        결과: 인증서 탈취 → Domain Admin
        """
        pass

class DPAPIExploit:
    """DPAPI 악용"""
    
    def extract_credentials(self) -> dict:
        """저장된 자격증명 탈취"""
        
        # 1. Chrome 비밀번호
        chrome_passwords = self._extract_chrome_passwords()
        
        # 2. Edge 비밀번호
        edge_passwords = self._extract_edge_passwords()
        
        # 3. WiFi 프로필
        wifi_passwords = self._extract_wifi_passwords()
        
        return {
            'chrome': chrome_passwords,
            'edge': edge_passwords,
            'wifi': wifi_passwords,
        }
```

### Week 9: Device Code Phishing & WiFi

#### Task 9.1: OAuth 피싱

```python
# src/core/attack/oauth_phishing.py

class DeviceCodePhishing:
    """Device Code Flow 피싱"""
    
    def generate_phishing_link(self) -> dict:
        """피싱 디바이스 코드 생성"""
        
        # OAuth 엔드포인트 호출
        # Device Code 생성
        # 피싱 URL 생성
        
        return {
            'device_code': '...',
            'user_code': '...',
            'phishing_url': 'https://microsoft.com/...',
        }
    
    def poll_for_token(self, device_code: str) -> str:
        """사용자 인증 후 토큰 획득"""
        pass
```

---

## Phase 4: 웹 스캐너 & C2 (주차 10-11)

### Week 10: 웹 취약점 스캐너

#### Task 10.1: 커스텀 웹 스캐너

```python
# src/core/scanner/web_scanner.py

class WebScanner:
    """커스텀 웹 취약점 스캐너"""
    
    def crawl(self, url: str) -> set:
        """웹사이트 크롤링 (JavaScript 렌더링 포함)"""
        pass
    
    def scan_sqli(self, url: str) -> list:
        """SQL Injection 탐지"""
        pass
    
    def scan_xss(self, url: str) -> list:
        """XSS 탐지"""
        pass
    
    def generate_report(self) -> str:
        """HTML 리포트 생성"""
        pass
```

### Week 11: C2 기본 구현

#### Task 11.1: C2 서버

```go
// src/c2/main.go

package main

type C2Server struct {
    listeners map[string]*Listener
    sessions  map[string]*Session
}

func (s *C2Server) StartListener(protocol string, port int) {
    // HTTP/HTTPS 리스너 구현
}

func (s *C2Server) ExecuteCommand(sessionID string, command string) {
    // 명령 큐에 추가
}
```

---

## Phase 5: UI 통합 & 완성 (주차 12)

### Week 12: eDEX-UI 대시보드 & 테스트

#### Task 12.1: Electron UI

```typescript
// src/ui/main.ts

// Electron 앱 생성
// eDEX-UI CSS 적용
// 대시보드 렌더링
```

#### Task 12.2: 통합 테스트

```python
# tests/test_integration.py

def test_process_monitoring():
    """프로세스 모니터링 end-to-end 테스트"""
    pass

def test_malware_detection():
    """악성코드 탐지 테스트"""
    pass

def test_attack_tools():
    """공격 도구 테스트"""
    pass
```

---

## 📊 개발 체크리스트

### Phase 1: 기초 (주차 1-2)
- [ ] 저장소 구조 확정
- [ ] PowerShell ↔ Python 통신 설계
- [ ] SQLite 스키마 생성
- [ ] 프로세스 모니터링 PoC

### Phase 2: 방어 (주차 3-6)
- [ ] 행동 분석 엔진 (100+ 패턴)
- [ ] YARA 커스텀 규칙 (1000+)
- [ ] 프로세스 차단 메커니즘
- [ ] 실시간 모니터링 완성

### Phase 3: 공격 (주차 7-9)
- [ ] Kerberoasting 구현
- [ ] NTLM Relaying (ADCS ESC8)
- [ ] DPAPI 악용
- [ ] Device Code 피싱
- [ ] WiFi 크래킹 기본

### Phase 4: 웹 & C2 (주차 10-11)
- [ ] 웹 크롤러 + SQLi/XSS 탐지
- [ ] C2 기본 구현
- [ ] LLM Red Teaming 기본

### Phase 5: 통합 (주차 12)
- [ ] eDEX-UI 대시보드
- [ ] 엔드-투-엔드 통합 테스트
- [ ] 성능 최적화
- [ ] 보안 감사

---

## 🎯 다음 단계 (즉시)

1. **이 주 (Week 1)**
   - [ ] 기술 결정 (Named Pipe 통신 확정)
   - [ ] PowerShell 모니터링 PoC 시작
   - [ ] 팀 킥오프 미팅

2. **다음 주 (Week 2)**
   - [ ] Python 이벤트 핸들러 완성
   - [ ] SQLite DB 생성
   - [ ] 첫 번째 프로세스 탐지 데모

---

**제목**: Kx-Defender v1.0 MVP (12주)  
**상태**: 🟢 개발 준비 완료  
**시작일**: 2026-07-29  
**완료 예정**: 2026-10-20

