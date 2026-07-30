# PRD: Kx-Defender (v2.0)
## Windows 보안 통합 플랫폼 - 공격+방어 통합

**문서 버전**: 2.0  
**작성일**: 2026-07-29  
**작성자**: Security Development Team  
**상태**: 작성 완료 (검토 준비 중)

---

## 1. Executive Summary

**Kx-Defender**는 Windows 시스템을 위한 **공격 및 방어 통합 보안 플랫폼**입니다. 

### 핵심 가치
- **방어 영역**: 실시간 프로세스 모니터링, 악성코드 탐지, 행동 기반 위협 탐지
- **공격 영역**: Red Team 도구 통합 (Kerberoasting, NTLM Relaying, DPAPI, OAuth 피싱, WiFi 크래킹, C2, LLM Red Teaming)
- **웹 보안**: 자체 구현 웹 취약점 스캐너 (OWASP ZAP 수준)
- **UI**: eDEX-UI 스타일 통합 대시보드

### 대상 사용자
- 🔍 보안 연구자 (악성코드 분석, 취약점 조사)
- ⚔️ Red Team 팀 (침투 테스트, 공격 시뮬레이션)
- ⚛️ CTF 참가자 (방어/공격 연습)
- 🛡️ 시스템 관리자 (엔드포인트 보호)

### 기술 철학
> "공격과 방어를 한 플랫폼에서 경험하며, 최신 보안 기법을 학습하고 실험한다"

---

## 2. Problem Statement

### 현재 Windows 보안의 문제점

#### 2.1 방어 영역
- ❌ 실행 중인 프로세스의 행동을 상세히 모니터링할 수 없음
- ❌ 의심 프로세스 탐지 후 수동 대응 또는 기존 디펜더 의존
- ❌ 0-day 및 변형 악성코드 탐지 불가
- ❌ 웹 취약점과 프로세스 위협을 별개로 분석해야 함

#### 2.2 공격 영역 (Red Teaming)
- ❌ Active Directory 공격 (Kerberoasting, NTLM Relaying, DPAPI) → 별도 도구 필요
- ❌ Identity 공격 (OAuth Device Code Phishing, Entra ID) → 각각 구축 필요
- ❌ WiFi 보안 테스트 (Aircrack) → 복잡한 환경 설정
- ❌ C2 Infrastructure (Havoc, Sliver) → 높은 진입 장벽
- ❌ LLM Red Teaming (Garak) → 최신 도구지만 별도 구성
- ❌ 웹 취약점 스캔 → ZAP 같은 외부 도구 의존, 통합 어려움

**해결책**: Kx-Defender를 통해 모든 공격/방어 기능을 **단일 통합 플랫폼**에서 제공

---

## 3. Goals & Objectives

### 3.1 주요 목표

#### 방어 (Defense)
- ✅ Windows Defender/Kaspersky 수준의 프로세스 탐지/차단
- ✅ 0-day 악성코드 탐지를 위한 행동 기반 분석
- ✅ 실시간 모니터링으로 빠른 위협 대응 (<500ms)

#### 공격 (Red Teaming)
- ✅ AD 환경 침투 테스트 (Kerberoasting, NTLM Relaying, DPAPI 악용)
- ✅ Identity 공격 시뮬레이션 (OAuth 피싱, Entra ID 공격)
- ✅ 무선 네트워크 보안 테스트 (WiFi 크래킹)
- ✅ C2 인프라 구축 및 운영 (Havoc/Sliver 스타일)
- ✅ LLM 보안 테스트 (Garak 통합)

#### 웹 보안
- ✅ 자체 구현 웹 취약점 스캐너 (ZAP 대체, OWASP Top 10 커버)
- ✅ 동적 스캔으로 0-day 웹 취약점 탐지

#### 사용자 경험
- ✅ eDEX-UI 스타일 통합 대시보드로 전문가 경험 제공
- ✅ 공격/방어 기능을 한 곳에서 관리

### 3.2 핵심 성과 지표 (KPI)

| 지표 | 목표 | 측정 방법 |
|------|------|---------|
| 악성 프로세스 탐지율 | 95% 이상 | CTF 샘플, 공개 악성코드 테스트 |
| 거짓 양성(False Positive) | <5% | 정상 프로세스 10,000개 스캔 |
| 프로세스 차단 응답시간 | <500ms | 클릭-종료 시간 측정 |
| 메모리 사용량 | <200MB | 8시간 연속 실행 |
| 웹 취약점 탐지 정확도 | 90% 이상 | OWASP Top 10 테스트 |
| AD 공격 성공률 | 95% 이상 | Kerberoasting, NTLM 테스트 |
| C2 안정성 | 99% 가용성 | 24시간 에이전트 운영 |
| UI 로딩 시간 | <2초 | 초기 대시보드 렌더링 |

---

## 4. User Personas

### Persona 1: 보안 연구자 (Primary)
- **프로필**: 악성코드 분석, 취약점 조사, 0-day 분석
- **목표**: 의심 프로세스 격리, 행동 모니터링, 웹 취약점 스캔, 악성코드 메모리 분석
- **사용 빈도**: 매일, 고급 기능 중심
- **우선순위**: 탐지 정확도, 행동 분석, 웹 스캔

### Persona 2: Red Team 엔지니어
- **프로필**: 침투 테스트, 공격 시뮬레이션, 보안 연습
- **목표**: AD 환경 공격, Identity 공격, C2 운영, 웹 취약점 활용
- **사용 빈도**: 프로젝트 기반 (2-4주 집중 사용)
- **우선순위**: 공격 도구 통합, 자동화, 보안 우회

### Persona 3: CTF 참가자
- **프로필**: 해킹 챌린지 참가, 시스템 방어 연습
- **목표**: 빠른 위협 탐지/차단, 웹 취약점 찾기, 공격 기법 학습
- **사용 빈도**: 챌린지 기간 중 집중 사용
- **우선순위**: 속도, 직관성, 다양한 기능

### Persona 4: 시스템 관리자 (Phase 2)
- **프로필**: 엔드포인트 보호, 위협 모니터링
- **목표**: 중앙화된 모니터링, 정책 기반 차단
- **사용 빈도**: 지속적 모니터링
- **우선순위**: 안정성, 확장성, 보고

---

## 5. Features & Functional Requirements

### 5.1 방어 기능 (Defense Module)

#### 5.1.1 실시간 프로세스 모니터링
**요구사항**:
- 모든 실행 중인 프로세스 실시간 감시
- 프로세스 메타데이터 수집 (PID, 메모리, CPU, 부모, 명령줄)
- 프로세스 생성/종료/수정 이벤트 <100ms 내 감지
- 파일 접근, 레지스트리 변경, 네트워크 연결 추적
- 프로세스 트리 구조 시각화

#### 5.1.2 프로세스 차단 및 종료
**요구사항**:
- UI에서 한 클릭으로 프로세스 즉시 차단/종료 (<500ms)
- 차단 규칙 설정 (시그니처, 해시, 경로 기반)
- 차단 이력 저장 및 분석
- 강제 종료 불가능한 프로세스 감지 및 경고
- 차단 이유 기록 (자동/수동)

#### 5.1.3 악성코드 탐지 (시그니처 기반)
**요구사항**:
- YARA 규칙 통합 (기본 1000+ 규칙)
- 프로세스 메모리 스캔
- 파일 시스템 스캔
- 시그니처 데이터베이스 자동 업데이트
- 탐지된 악성코드 자동 격리

#### 5.1.4 행동 기반 위협 탐지 (Behavioral Detection)
**요구사항**:
- 의심 행동 패턴 감지 (메모리 주입, DLL 로드, 시스템 콜 변조)
- 동적 분석 (실행 시간 행동 모니터링)
- 행동 점수 계산 (0-100, 의심도 레벨)
- 자동 격리/차단 규칙 제안
- 비정상 네트워크 트래픽 감지

#### 5.1.5 로깅 및 리포팅
**요구사항**:
- 모든 이벤트를 로컬 DB에 기록
- 구조화된 로그 (JSON, CSV 내보내기)
- 분석 리포트 생성 (HTML, PDF)
- 감사 추적 (감시자 수정 사항 추적)
- 로그 검색/필터링

---

### 5.2 공격 기능 (Red Team Module)

#### 5.2.1 Active Directory 공격 (AD Attack Suite)

##### 5.2.1.1 Kerberoasting
**목표**: TGS-REP 메시지에서 암호 크래킹 가능한 서비스 계정 찾기  
**기능**:
- 도메인의 모든 SPN(Service Principal Names) 열거
- TGS(Ticket Granting Service) 요청 및 수집
- Hashcat/John 호환 형식으로 해시 추출
- 오프라인 크래킹 지원
- 크래킹 결과 자동 검증

**Acceptance Criteria**:
- AD 환경에서 100% SPN 발견
- TGS 추출 시간 <5초 (100개 SPN)
- 크래킹된 계정 즉시 활용 가능
- 로그 위장 옵션 제공

##### 5.2.1.2 NTLM Relaying (특히 ADCS ESC8)
**목표**: NTLM 인증을 ADCS 서버로 중계하여 인증서 탈취  
**기능**:
- SMB/HTTP NTLM 캡처
- LDAP/ADCS로의 중계 (ESC8 공격 경로)
- 인증서 자동 생성 및 추출
- 생성된 인증서로 TGT 획득
- 다양한 프로토콜 지원 (SMB, HTTP, LDAP, ADCS)

**Acceptance Criteria**:
- 캡처된 NTLM 중계 성공률 95% 이상
- 인증서 탈취 자동화
- Domain Admin 권한 상승 (ADCS를 통한)
- 모니터링 회피 옵션

##### 5.2.1.3 DPAPI 악용 (Credential Access)
**목표**: Windows DPAPI로 보호된 자격증명 탈취  
**기능**:
- DPAPI 캐시 발견 및 추출
- 마스터 키 덤핑
- 자격증명 복호화 (로컬 권한으로)
- 도메인 동기화 키로 오프라인 복호화
- 브라우저 저장 비밀번호 자동 추출

**Acceptance Criteria**:
- 로컬 저장 자격증명 100% 복호화
- 브라우저 비밀번호 추출 (Chrome, Edge, Firefox)
- WiFi 프로필 복호화
- 추출된 자격증명으로 수평 이동 가능

---

#### 5.2.2 Identity & OAuth 공격 (Identity Attack Suite)

##### 5.2.2.1 Device Code Flow Phishing
**목표**: OAuth Device Code 피싱으로 사용자 토큰 탈취  
**기능**:
- 피싱 디바이스 자격증명 생성
- 타겟 사용자에게 링크/코드 전달
- 사용자 인증 후 자동 토큰 탈취
- 토큰 유효성 검증
- 타겟 대상 Microsoft 365 / Google Workspace 지원

**Acceptance Criteria**:
- 피싱 성공률 추적 (사용자 승인율)
- 획득한 토큰으로 API 호출 가능
- 다중 테넌트 지원
- 감지 회피 옵션

##### 5.2.2.2 Entra ID (Azure AD) 공격
**목표**: Azure AD 환경에서 권한 상승 및 데이터 탈취  
**기능**:
- 유효한 사용자 열거
- 약한 암호 정책 테스트 (비밀번호 스프레이)
- 조건부 접근(Conditional Access) 우회
- 응용 프로그램 권한 악용
- Graph API를 통한 메타데이터 수집

**Acceptance Criteria**:
- 유효한 사용자 계정 90% 이상 열거
- 약한 암호 계정 발견 (테스트 모드)
- Conditional Access 우회 기법 2+ 가지
- Graph 데이터 추출 (메일, OneDrive)

---

#### 5.2.3 무선 보안 (Wireless Attack Suite)

##### 5.2.3.1 WiFi Password Cracking (Aircrack 스타일)
**목표**: WiFi WPA/WPA2/WPA3 네트워크 보안 테스트  
**기능**:
- 네트워크 스캔 및 ESSID 열거
- 핸드셰이크 캡처 (WPA/WPA2)
- 사전 공격(Dictionary Attack)
- Rainbow Table 공격
- GPU 가속 크래킹 지원
- WPS (WiFi Protected Setup) 취약점 테스트

**Acceptance Criteria**:
- 핸드셰이크 캡처 성공률 95% 이상
- 약한 비밀번호 (<=12자) 1분 내 크래킹
- GPU 지원으로 속도 10배 이상
- 9개 내 핸드셰이크 재전송 (WPS 테스트)

##### 5.2.3.2 네트워크 가시성 (와이파이 트래픽 분석)
**요구사항**:
- 무선 트래픽 패킷 캡처
- 신호 강도(RSSI) 모니터링
- 연결된 클라이언트 추적
- DNS 쿼리 분석
- 비암호화 트래픽 검사

---

#### 5.2.4 C2 Infrastructure 구축 (Havoc/Sliver 스타일)

##### 5.2.4.1 C2 서버 관리
**목표**: Red Team 운영을 위한 경량 C2 프레임워크  
**기능**:
- 다중 리스너 지원 (HTTP/HTTPS, DNS, SMB, TCP)
- 에이전트 자동 생성 (PE, DLL, Shellcode)
- 암호화 통신 (TLS, AES-256)
- 다중 명령 (cmd, PowerShell, 파일 전송)
- 세션 관리 (대기, 활성, 종료)
- 빔 운영 (Teamserver) 지원

**Acceptance Criteria**:
- 100+ 동시 세션 관리
- <100ms 명령 응답 시간
- 탐지 회피 기법 (코드 동적 로드, AMSI 우회)
- 모든 리스너 타입 안정적 작동

##### 5.2.4.2 Post-Exploitation 도구
**기능**:
- 대역외 수집(Exfiltration) (HTTP, DNS, ICMP)
- 프로세스 주입 및 숨김
- 권한 상승 (UAC 우회, 토큰 스틸)
- 횡방향 이동 (PsExec, WMI, WinRM)
- 영속성 메커니즘 (스케줄 작업, 레지스트리 Run)

---

#### 5.2.5 웹 취약점 스캔 - 자체 구현 (Custom Web Scanner)

##### 5.2.5.1 URL 크롤링 및 발견
**목표**: 동적 웹 크롤링으로 모든 취약점 공격 면 발견  
**기능**:
- 종자 URL에서 자동 크롤링 시작
- JavaScript 렌더링 (Puppeteer/Playwright)
- 숨겨진 폼 필드 발견
- API 엔드포인트 자동 감지
- 인증된 크롤링 지원 (로그인 자동화)
- 깊이/너비 제한 설정

**Acceptance Criteria**:
- 크롤링 커버리지 95% 이상 (매뉴얼 확인 기준)
- JavaScript 동적 콘텐츠 100% 처리
- 30초 내 1000개 페이지 크롤링
- 자동 인증 성공률 90%

##### 5.2.5.2 취약점 스캔 (OWASP Top 10)

###### 5.2.5.2.1 Injection (SQLi, NoSQLi, Command Injection)
**탐지 기법**:
- 페이로드 기반 테스트 (100+ SQLi 페이로드)
- 시간 기반 블라인드 SQLi
- 에러 기반 SQLi (에러 메시지 분석)
- 유니언 쿼리 테스트
- 스택 기반 커맨드 주입

**정확도 목표**: 90%+

###### 5.2.5.2.2 Broken Authentication
**탐지 기법**:
- 세션 토큰 강도 분석
- 비밀번호 정책 평가 (최소 길이 등)
- 다중 인증(MFA) 부재 감지
- 자격증명 리스트 공격(Credential Stuffing) 테스트
- 세션 고정 취약점

###### 5.2.5.2.3 Cross-Site Scripting (XSS)
**탐지 기법**:
- Reflected XSS (GET/POST 파라미터)
- Stored XSS (데이터베이스 저장 후 표시)
- DOM-based XSS (JavaScript 분석)
- 이벤트 핸들러 필터링 우회
- Context-aware 페이로드 (HTML, JavaScript, CSS, URL 콘텍스트)

**정확도 목표**: 95%+

###### 5.2.5.2.4 CSRF (Cross-Site Request Forgery)
**탐지 기법**:
- CSRF 토큰 유무 확인
- 토큰 유효성 검증 (재사용 가능성)
- SameSite 쿠키 정책 확인
- Origin/Referer 검증

###### 5.2.5.2.5 기타 (XXE, SSRF, Path Traversal, File Upload 등)
**지원 취약점**:
- XXE (XML External Entity)
- SSRF (Server-Side Request Forgery)
- Path Traversal (/etc/passwd 포함)
- 파일 업로드 필터 우회
- 오픈 리다이렉트
- 정보 공개 (헤더, 에러 메시지)

##### 5.2.5.3 결과 분석 및 보고
**기능**:
- 발견된 취약점 위험도 자동 분류 (CVSS v3.1)
- 중복 탐지 제거
- 거짓 양성 필터링 (재확인)
- 상세 기술 보고서 생성 (HTML, JSON, PDF)
- 수정 권장사항 제공

**Acceptance Criteria**:
- 거짓 양성 <10%
- 거짓 음성 <5% (OWASP Top 10 테스트 케이스 기준)
- 스캔 시간 (1000개 페이지) <30분
- 보고서 생성 <1초

---

#### 5.2.6 LLM Red Teaming (Garak 스타일)

##### 5.2.6.1 LLM 프롬프트 인젝션 테스트
**목표**: LLM의 보안 결함(Jailbreak, 데이터 유출) 발견  
**기능**:
- 50+ 프롬프트 인젝션 페이로드 (Garak에서 선별)
- 역할 변환 공격 (Role-switching)
- 감정 자극 공격 (Emotional manipulation)
- 데이터 추출 요청 (데이터 유출)
- 정책 회피 기법 테스트
- 여러 LLM 모델 지원 (OpenAI, Claude, Gemini, Local LLMs)

**Acceptance Criteria**:
- 100개 요청 내 Jailbreak 성공률 측정
- 기밀 정보 유출 감지율 90%+
- 다양한 LLM 모델 호환성 100%

##### 5.2.6.2 응답 분석 및 점수 부여
**기능**:
- 응답이 원래 정책 위반했는지 자동 판단
- 민감 정보 탐지 (이메일, API 키, 내부 정보)
- 응답 위험도 점수 (0-100)
- 공격 유형별 통계

---

### 5.3 UI/UX 기능 (Dashboard & Interface)

#### 5.3.1 eDEX-UI 스타일 통합 대시보드
**요구사항**:
- 테마: 사이버펑크/터미널 스타일 (eDEX-UI 기반)
- 색상: 검정(#000000), 사이언(#00D9FF), 마젠타(#FF00FF), 주황(#FF6600)
- 폰트: Courier New, IBM Plex Mono (터미널 느낌)
- 반응형 디자인 (1080p ~ 4K 모니터 지원)

#### 5.3.2 주요 화면

##### 메인 대시보드
- 실시간 위협 카운트 (Critical, High, Medium, Low)
- 프로세스 트리 뷰 (계층 구조)
- 최근 이벤트 스트림 (실시간 업데이트)
- 네트워크 트래픽 그래프
- C2 세션 상태 (공격 모드)

##### 방어 모듈 화면
- 모든 프로세스 목록 (필터/검색)
- 프로세스 상세 정보 (메모리, 네트워크, 파일 접근)
- 차단 버튼 (즉시 종료)
- YARA 탐지 결과
- 행동 점수 시각화

##### 공격 모듈 화면
- Kerberoasting: SPN 목록, TGS 추출 결과, 해시 아웃풋
- NTLM Relaying: 캡처된 토큰, 중계 상태, 획득 권한
- WiFi 크래킹: 네트워크 목록, 핸드셰이크 상태, 크래킹 진행률
- C2 관리: 리스너 목록, 에이전트 세션, 명령 실행 결과
- 웹 스캔: 크롤링 진행, 발견된 취약점 목록, 상세 보고서

##### 웹 보안 화면
- 대상 URL 입력 및 스캔 설정
- 실시간 크롤링 진행 바
- 발견된 취약점 (위험도별 필터)
- 취약점 상세 정보 (Request/Response 덤프)
- 수정 권장사항

##### 설정 화면
- 탐지 규칙 관리 (YARA, 행동)
- 차단 정책 설정
- 공격 도구 구성 (Kerberoasting, NTLM, C2)
- 웹 스캔 정책 커스터마이징
- 로그 보관 기간
- 업데이트 설정

#### 5.3.3 상호작용 패턴
- 실시간 업데이트: 1초 주기 새로고침
- 알림: Critical은 음성 경고 + 토스트 알림 + 진동
- 단축키: Ctrl+Q(종료), Ctrl+P(검색), Ctrl+L(로그 초기화), Ctrl+N(신규 스캔)
- 드래그앤드롭: 파일/URL을 앱에 드래그해 스캔

---

### 5.4 기술 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   Kx-Defender UI                        │
│              (eDEX-UI 기반 대시보드)                     │
│         HTTP/WebSocket ← 실시간 이벤트 → REST API       │
└─────────────────────────────────────────────────────────┘
                          ↕
┌──────────────────────────────────────────────────────────┐
│         Main Service (Backend Orchestrator)              │
│                  (.NET 또는 Python)                      │
└──────────────────────────────────────────────────────────┘
      ↕           ↕           ↕           ↕
  ┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │PowerShell│ │WSL/Linux │  │웹 스캐너  │  │C2 Server │
  │ 모니터링  │  │YARA/분석 │  │(커스텀)   │  │(Havoc)   │
  │& 차단    │  │공격 도구 │  │          │  │          │
  │(방어)    │  │(공격)   │  │(보안)    │  │(공격)    │
  └────────┘  └──────────┘  └──────────┘  └──────────┘
       ↓            ↓            ↓            ↓
  ┌──────────────────────────────────────────────────────┐
  │         SQLite 데이터베이스 (로컬 저장소)             │
  │  - 로그 (프로세스, 탐지, 스캔)                        │
  │  - 규칙 (YARA, 행동)                                │
  │  - 설정 (정책, 프로필)                               │
  │  - 세션 (C2 에이전트, 스캔 결과)                     │
  └──────────────────────────────────────────────────────┘
```

#### 기술 스택

| 영역 | 선택지 | 이유 |
|------|--------|------|
| **방어 모듈** | PowerShell + WMI | Windows API 직접 접근 |
| **분석 엔진** | WSL2 + Linux | 고성능, YARA 네이티브 |
| **웹 스캐너** | Python (커스텀) | OWASP 독립 구현 |
| **공격 도구** | Python/Go | 이식성, 성능 |
| **C2 서버** | Go (Havoc 기반) | 경량, 빠른 응답 |
| **UI** | Electron + React | 크로스플랫폼, 반응성 |
| **DB** | SQLite | 경량, 의존성 최소 |
| **통신** | Named Pipe + REST API | 보안, 유연성 |

#### 보안 고려사항
- 권한: 관리자 권한 필수 (프로세스 모니터링/차단)
- 암호화: 민감 설정/로그는 AES-256 로컬 암호화
- 샌드박싱: 분석 엔진은 격리된 WSL 컨테이너에서 실행
- 악용 방지: Kx-Defender 프로세스 자신도 보호 (차단 불가)
- 탐지 회피: 공격 도구에 anti-forensics 옵션 제공

---

## 6. User Stories & Acceptance Criteria

### 방어 User Stories

#### Story 1: 실시간 프로세스 모니터링
```
As a 보안 연구자,
I want to 실시간으로 모든 프로세스를 모니터링할 수 있고,
So that 의심 프로세스의 행동을 추적하고 분석할 수 있다.
```

**Acceptance Criteria**:
- ✅ 새 프로세스 생성 시 <100ms 내에 감지
- ✅ 프로세스 메타데이터 (PID, 메모리, CPU, 명령줄) 표시
- ✅ 프로세스 트리 구조 시각화
- ✅ 필터링/검색 기능 (이름, PID, 부모)
- ✅ 실시간 로그에 모든 변경사항 기록
- ✅ 자식 프로세스 확장/축소 가능

#### Story 2: 의심 프로세스 차단
```
As a CTF 참가자,
I want to 한 클릭으로 의심 프로세스를 즉시 종료할 수 있고,
So that 악성 프로세스로부터 시스템을 보호할 수 있다.
```

**Acceptance Criteria**:
- ✅ UI "차단" 버튼 클릭 시 프로세스 즉시 종료 (<500ms)
- ✅ 차단된 프로세스 이력 저장
- ✅ 강제 종료 불가능 프로세스에 경고 표시
- ✅ 차단 사유 기록 (자동/수동)
- ✅ 차단 규칙 저장 및 향후 자동 차단 가능

#### Story 3: YARA 악성코드 탐지
```
As a 보안 연구자,
I want to YARA 시그니처로 악성코드를 자동 탐지하고,
So that 알려진 악성코드로부터 시스템을 보호할 수 있다.
```

**Acceptance Criteria**:
- ✅ 기본 YARA 규칙 세트 포함 (>1000 규칙)
- ✅ 프로세스 메모리 스캔 지원
- ✅ 파일 시스템 스캔 지원
- ✅ 시그니처 자동 업데이트 기능
- ✅ 탐지된 악성코드 자동 격리

#### Story 4: 행동 기반 탐지
```
As a 보안 연구자,
I want to 프로세스의 의심 행동을 탐지하고,
So that 0-day 악성코드와 변형 악성코드를 탐지할 수 있다.
```

**Acceptance Criteria**:
- ✅ 메모리 주입 탐지 (코드 인젝션)
- ✅ 비정상적인 DLL 로드 감지
- ✅ 시스템 콜 변조 탐지
- ✅ 행동 점수 계산 (0-100)
- ✅ 자동 차단 임계값 설정 가능

---

### 공격 User Stories

#### Story 5: Kerberoasting 공격
```
As a Red Team 엔지니어,
I want to 도메인의 모든 SPN을 열거하고 TGS를 크래킹할 수 있고,
So that 서비스 계정 권한으로 초기 접근을 확보할 수 있다.
```

**Acceptance Criteria**:
- ✅ 100% SPN 발견 (도메인 조회)
- ✅ TGS 추출 시간 <5초 (100개 SPN)
- ✅ Hashcat 호환 해시 포맷
- ✅ 크래킹 결과 자동 검증
- ✅ 로그 위장 옵션

#### Story 6: NTLM Relaying (ADCS ESC8)
```
As a Red Team 엔지니어,
I want to NTLM 인증을 ADCS로 중계하여 인증서를 탈취할 수 있고,
So that Domain Admin 권한을 획득할 수 있다.
```

**Acceptance Criteria**:
- ✅ SMB/HTTP NTLM 캡처 및 중계
- ✅ ADCS 인증서 자동 생성
- ✅ 생성 인증서로 TGT 획득 가능
- ✅ ESC8 공격 체인 자동화
- ✅ 감지 회피 옵션 (로그 삭제 등)

#### Story 7: DPAPI 자격증명 탈취
```
As a Red Team 엔지니어,
I want to 로컬 DPAPI 자격증명을 복호화할 수 있고,
So that 저장된 비밀번호와 토큰을 탈취할 수 있다.
```

**Acceptance Criteria**:
- ✅ 로컬 저장 자격증명 100% 복호화
- ✅ 브라우저 비밀번호 추출 (Chrome, Edge, Firefox)
- ✅ WiFi 프로필 복호화
- ✅ 도메인 동기화 키 이용한 오프라인 복호화
- ✅ 추출된 자격증명 즉시 활용 가능

#### Story 8: Device Code Phishing
```
As a Red Team 엔지니어,
I want to OAuth Device Code를 피싱하여 사용자 토큰을 탈취할 수 있고,
So that 사용자 권한으로 클라우드 리소스에 접근할 수 있다.
```

**Acceptance Criteria**:
- ✅ 피싱 디바이스 자격증명 자동 생성
- ✅ 사용자 승인 추적
- ✅ 토큰 자동 탈취 및 검증
- ✅ Microsoft 365 / Google Workspace 지원
- ✅ 획득한 토큰으로 API 호출 가능

#### Story 9: WiFi 비밀번호 크래킹
```
As a Red Team 엔지니어,
I want to WiFi 핸드셰이크를 캡처하고 비밀번호를 크래킹할 수 있고,
So that 무선 네트워크 접근을 확보할 수 있다.
```

**Acceptance Criteria**:
- ✅ 핸드셰이크 캡처 성공률 95% 이상
- ✅ 약한 비밀번호 (<12자) 1분 내 크래킹
- ✅ GPU 가속으로 속도 10배 이상
- ✅ WPA/WPA2/WPA3 모두 지원
- ✅ 결과 자동 검증

#### Story 10: C2 세션 관리
```
As a Red Team 엔지니어,
I want to 100+ 에이전트를 동시에 관리하고 명령을 실행할 수 있고,
So that 침투 테스트를 효율적으로 진행할 수 있다.
```

**Acceptance Criteria**:
- ✅ 100+ 동시 세션 안정적 관리
- ✅ <100ms 명령 응답 시간
- ✅ 다중 리스너 지원 (HTTP, DNS, SMB, TCP)
- ✅ 에이전트 자동 생성 (PE, DLL, Shellcode)
- ✅ 세션 상태 실시간 추적

---

### 웹 보안 User Stories

#### Story 11: 통합 웹 취약점 스캔
```
As a 보안 연구자,
I want to 대상 웹사이트를 완전히 크롤링하고 OWASP Top 10을 자동으로 스캔할 수 있고,
So that 모든 취약점을 빠르게 찾을 수 있다.
```

**Acceptance Criteria**:
- ✅ JavaScript 렌더링을 포함한 완전 크롤링
- ✅ 30초 내 1000개 페이지 크롤링
- ✅ SQLi, XSS, CSRF, 파일 업로드 취약점 탐지
- ✅ 거짓 양성 <10%
- ✅ 발견된 모든 취약점에 대한 PoC 제공

#### Story 12: LLM Red Teaming
```
As a 보안 연구자,
I want to LLM의 프롬프트 인젝션 취약점을 테스트할 수 있고,
So that LLM 기반 애플리케이션의 보안을 평가할 수 있다.
```

**Acceptance Criteria**:
- ✅ 50+ 다양한 인젝션 페이로드
- ✅ 여러 LLM 모델 지원 (OpenAI, Claude, Gemini)
- ✅ 응답 자동 분석 (정책 위반 감지)
- ✅ 민감 정보 유출 탐지 (API 키, 개인정보)
- ✅ 공격 유형별 통계 리포트

---

## 7. Technical Requirements

### 7.1 시스템 요구사항
- **OS**: Windows 10/11 (64-bit)
- **프로세서**: Intel i5 / AMD Ryzen 5 이상 (멀티코어)
- **메모리**: 8GB RAM (권장 16GB)
- **디스크**: 2GB 여유 공간
- **WSL2**: 필수 (Linux 엔진 실행용)
- **관리자 권한**: 필수

### 7.2 소프트웨어 의존성

| 컴포넌트 | 버전 | 용도 |
|---------|------|------|
| PowerShell | 5.0+ | Windows API 접근 |
| WSL2 | 최신 | Linux 도구 실행 |
| Python | 3.9+ | 웹 스캐너, 공격 도구 |
| Go | 1.18+ | C2 서버 |
| YARA | 4.3+ | 악성코드 탐지 |
| Aircrack-ng | 1.7+ | WiFi 크래킹 |
| Impacket | 0.10+ | AD/Kerberos 도구 |
| Hashcat | 6.2+ | 크래킹 엔진 |
| Node.js | 16+ | UI 개발 서버 |
| Electron | 12+ | UI 패키징 |

### 7.3 성능 요구사항

| 지표 | 목표 |
|------|------|
| 메모리 사용량 | <200MB (유휴), <500MB (스캔 중) |
| CPU 오버헤드 | <5% (모니터링 중) |
| 프로세스 차단 응답시간 | <500ms |
| UI 렌더링 | <2초 (초기 로딩) |
| 실시간 업데이트 | 1초 이하 |
| 웹 스캔 속도 | 30초/1000페이지 |
| C2 명령 응답 | <100ms |

---

## 8. Success Metrics

### 8.1 기능 성공 지표

| 메트릭 | 목표 | 측정 방법 | 책임자 |
|--------|------|---------|--------|
| **방어** | | | |
| 악성 프로세스 탐지율 | 95% | CTF 샘플 테스트 | QA |
| 거짓 양성 비율 | <5% | 정상 프로세스 10K 스캔 | QA |
| 프로세스 차단 응답시간 | <500ms | 클릭-종료 시간 측정 | Performance |
| **공격** | | | |
| Kerberoasting 성공률 | 95% | AD 테스트 환경 | Security |
| WiFi 크래킹 속도 | <1min (weak pwd) | GPU 벤치 | Performance |
| C2 세션 안정성 | 99% | 24h 에이전트 테스트 | Reliability |
| **웹 보안** | | | |
| 웹 취약점 탐지율 | 90% | OWASP Top 10 테스트 | QA |
| 거짓 양성 | <10% | 안전한 웹앱 스캔 | QA |
| **UI/UX** | | | |
| UI 로딩 시간 | <2초 | 크롬 개발자 도구 | Frontend |
| 사용성 점수 | 8/10 | 사용자 테스트 | UX |

### 8.2 보안 메트릭
- 코드 커버리지: 85% 이상 (단위 테스트)
- 보안 감사: 0개 Critical 취약점
- 의존성 취약점: 0개 Critical/High 버전 사용
- 소스 코드 스캔: Semgrep/SonarQube 통과

### 8.3 사용자 만족도
- Red Team 피드백: 4/5 별 이상
- 보안 연구자 재사용 의도: 80% 이상
- CTF 참가자 선호도: 상위 3개 보안 도구 내 진입

---

## 9. Scope

### In-Scope (MVP - Phase 1, 12주)
#### 방어 (Defense)
✅ 실시간 프로세스 모니터링  
✅ 프로세스 차단 및 종료  
✅ YARA 기반 악성코드 탐지  
✅ 기본 행동 기반 탐지 (Top 10 패턴)  
✅ 로컬 로깅 및 검색  

#### 공격 (Red Team)
✅ Kerberoasting (기본)  
✅ NTLM Relaying (ADCS ESC8)  
✅ DPAPI 악용 (브라우저 비밀번호 추출)  
✅ Device Code Phishing  
✅ WiFi 크래킹 (WPA/WPA2)  
✅ C2 기본 구현 (1-2 리스너)  
✅ LLM Red Teaming (기본 페이로드)  

#### 웹 보안
✅ 커스텀 웹 스캐너 (SQLi, XSS, CSRF)  
✅ 크롤링 + 기본 스캔  
✅ HTML 리포트  

#### UI
✅ eDEX-UI 스타일 대시보드  
✅ 방어/공격 모듈 탭  
✅ 실시간 프로세스/위협 뷰  

### Out-of-Scope (Phase 2+, 향후)
❌ 네트워크 기반 중앙 모니터링  
❌ 다중 시스템 에이전트 배포  
❌ 머신러닝 기반 탐지  
❌ 커스텀 시그니처 작성 UI  
❌ 라이트 테마 (Phase 2)  
❌ 모바일 앱  
❌ 고급 C2 기능 (C2 토너먼트 기능)  
❌ Entra ID 고급 공격  
❌ 자동화된 침투 테스트 보고서  

---

## 10. Timeline & Milestones

### Phase 1: MVP (12주)

| 주차 | 이정표 | 산출물 | 상태 |
|------|--------|--------|------|
| 1-2 | **환경 설정 & 아키텍처** | 기술 설계, GitHub 설정, 빌드 파이프라인 | 📋 계획 |
| 3 | **PowerShell 모니터링 엔진** | 프로세스 감시 + 이벤트 로깅 모듈 | 📋 계획 |
| 4 | **행동 분석 엔진** | 의심 패턴 탐지 + 점수 계산 | 📋 계획 |
| 5 | **YARA 통합 & 기본 탐지** | 시그니처 DB + 스캔 엔진 | 📋 계획 |
| 6 | **공격 도구 Phase 1** | Kerberoasting + NTLM Relaying + DPAPI | 📋 계획 |
| 7 | **웹 스캐너 구현** | 크롤러 + SQLi/XSS 탐지 | 📋 계획 |
| 8 | **C2 서버 기본 구현** | 리스너 + 에이전트 제너레이터 | 📋 계획 |
| 9 | **LLM Red Teaming** | 페이로드 DB + 응답 분석 | 📋 계획 |
| 10 | **UI 개발** | eDEX-UI 기반 대시보드 + 통합 | 📋 계획 |
| 11 | **통합 테스트** | 엔드-투-엔드 테스트 + 버그 수정 | 📋 계획 |
| 12 | **최적화 & MVP 릴리스** | 성능 튜닝 + v1.0 릴리스 | 📋 계획 |

### Phase 2: 확장 (Phase 1 후 6-8주)
- 머신러닝 기반 탐지
- 커스텀 시그니처 작성 UI
- 고급 C2 기능 (C2 토너먼트 수준)
- Entra ID 고급 공격
- 중앙 모니터링 (기본)

---

## 11. Risks & Mitigation

| 위험 | 영향 | 확률 | 대응 전략 |
|------|------|------|---------|
| PowerShell/WSL 통신 복잡도 | 높음 | 중간 | Week 1-2에 PoC 검증, Named Pipe vs REST 결정 |
| Windows API 접근 제한 | 높음 | 낮음 | 관리자 권한 필수 명시, 대체 API 조사 |
| YARA 성능 병목 | 중간 | 중간 | WSL에서 병렬 처리, 메모리 캐싱 |
| ZAP 커스텀 구현 복잡도 | 높음 | 높음 | 주차 7에 완성도 80% 이상 목표, 단계별 구현 |
| C2 탐지/차단 우려 | 높음 | 중간 | 공격 회피 옵션 제공, 교육 목표 명시 |
| 거짓 양성 과다 | 중간 | 중간 | 사전 테스트 1000+ 정상 프로세스 |
| UI 반응성 | 낮음 | 낮음 | 비동기 처리, 웹워커 활용 |

---

## 12. Dependencies & Assumptions

### 의존성
- PowerShell 5.0+ (Windows 10/11 기본 포함)
- WSL 2 설치 및 작동 (사용자 설치 필요)
- YARA 4.3+ 바이너리
- Python 3.9+ (WSL)
- Go 1.18+ (C2 컴파일용)
- Aircrack-ng (WiFi 기능)
- Impacket (AD 도구)
- Node.js 16+ (UI 개발)
- Electron 12+ (패키징)

### 가정사항
- 사용자는 관리자 권한으로 실행
- Windows 10/11 (64-bit) 환경
- 최소 8GB RAM, 2GB 디스크
- 인터넷 연결 (시그니처/페이로드 업데이트)
- Python/Go 기본 지식 (확장 시)

---

## 13. Open Questions & Decision Items

| 질문 | 현재 상태 | 담당자 | 마감일 |
|------|---------|--------|--------|
| 1. PowerShell ↔ WSL 통신 방식 선택 | 🔴 열림 | Arch Team | 2026-08-05 |
| 2. UI 프레임워크 (Electron vs 브라우저) | 🔴 열림 | Frontend | 2026-08-05 |
| 3. 초기 YARA 규칙 소스 | 🔴 열림 | Security | 2026-08-05 |
| 4. C2 커스텀 구현 vs Havoc/Sliver 포크 | 🔴 열림 | Red Team | 2026-08-08 |
| 5. 웹 스캐너 성능 vs 기능 트레이드오프 | 🟡 진행중 | QA | 2026-08-10 |
| 6. 라이선싱 모델 (오픈소스 vs 비공개) | 🔴 열림 | 경영진 | 2026-08-12 |
| 7. WiFi 기능 법적 제약 명시 필요 | 🟡 검토중 | Legal | 2026-08-12 |

---

## 14. Approval Checklist

### 기술 검토 (Architecture Team)
- [ ] 아키텍처 타당성
- [ ] PowerShell/WSL 통신 설계 검증
- [ ] 성능 요구사항 달성 가능성
- [ ] 보안 구현 계획 검토
- [ ] 의존성 관리 계획

**검토자**: Security Architecture Lead  
**마감**: 2026-08-05

### 보안 검토 (Security Team)
- [ ] YARA 통합 전략
- [ ] ZAP 커스텀 구현 안전성
- [ ] 권한 에스컬레이션 위험 평가
- [ ] 공격 도구 악용 방지 메커니즘
- [ ] C2 탐지 회피 기법 검증

**검토자**: Senior Security Engineer  
**마감**: 2026-08-08

### 법적/컴플라이언스 검토
- [ ] 오픈소스 라이선싱 검증
- [ ] 규제 준수 (WiFi 크래킹, C2 등)
- [ ] 사용 약관 및 책임 명시

**검토자**: Legal Counsel  
**마감**: 2026-08-12

### UI/UX 검토 (Design Lead)
- [ ] eDEX-UI 스타일 일관성
- [ ] 사용성 평가
- [ ] 반응형 디자인 테스트
- [ ] 접근성 (WCAG 2.1)

**검토자**: Lead Designer  
**마감**: 2026-08-08

### 제품 검토 (Product Manager)
- [ ] 사용자 니즈 충족
- [ ] 우선순위 적절성
- [ ] 마켓 적합성
- [ ] 경쟁 분석

**검토자**: Product Manager  
**마감**: 2026-08-10

### 최종 승인 (Project Sponsor)
- [ ] 모든 기술/보안 검토 완료
- [ ] 리소스 할당 확인
- [ ] 타임라인 현실성
- [ ] 예산 승인

**검토자**: Engineering Lead / Project Sponsor  
**마감**: 2026-08-12

---

## 15. Sign-Off

| 역할 | 이름 | 서명 | 날짜 | 상태 |
|------|------|------|------|------|
| Architecture Lead | TBD | _____ | _____ | ⏳ 대기 |
| Security Lead | TBD | _____ | _____ | ⏳ 대기 |
| UI/UX Lead | TBD | _____ | _____ | ⏳ 대기 |
| Product Manager | TBD | _____ | _____ | ⏳ 대기 |
| Project Sponsor | TBD | _____ | _____ | ⏳ 대기 |

---

## Appendix

### A. 참고 자료

#### 방어 관련
- Windows API Reference: https://docs.microsoft.com/windows/win32/
- YARA Rules: https://github.com/Yara-Rules/rules
- Sigma Rules: https://github.com/SigmaHQ/sigma

#### 공격 관련
- Impacket: https://github.com/SecureAuthCorp/impacket
- Aircrack-ng: https://www.aircrack-ng.org/
- Havoc C2: https://github.com/HavocFramework/Havoc
- Sliver: https://github.com/BishopFox/sliver

#### 웹 보안
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Burp Suite Documentation: https://portswigger.net/burp/documentation
- WebGoat: https://github.com/WebGoat/WebGoat

#### UI/UX
- eDEX-UI: https://github.com/GitSquared/edex-ui
- Electron: https://www.electronjs.org/
- React: https://reactjs.org/

#### 기타
- Garak (LLM Red Teaming): https://github.com/leondz/garak
- Semgrep: https://semgrep.dev/

### B. 용어 정의

**시그니처**: 악성코드의 고유한 특징 (파일 해시, 문자열 패턴)

**행동 탐지**: 악성코드의 실행 시간 행동 분석 (메모리 주입, 네트워크 연결)

**거짓 양성(False Positive)**: 정상 프로세스를 악성으로 오탐하는 경우

**응답시간**: 탐지부터 차단까지의 소요 시간

**SPN(Service Principal Names)**: Active Directory에 등록된 서비스의 고유 식별자

**TGS(Ticket Granting Service)**: Kerberos에서 서비스 액세스 권한을 부여하는 티켓

**NTLM Relaying**: NTLM 인증을 다른 서버로 중계하는 공격 기법

**DPAPI**: Windows 데이터 보호 API (자격증명 암호화)

**Device Code Flow**: OAuth 2.0의 디바이스 인증 흐름 (사물 인터넷용)

**ADCS(Active Directory Certificate Services)**: 인증서 발급 및 관리 서비스

**C2(Command & Control)**: Red Team이 침투한 시스템을 제어하는 인프라

**ESC(Elevation of Privilege)**: ADCS 기반 권한 상승 공격 (ESC8 등)

**ZAP(OWASP Zap)**: 오픈소스 웹 보안 스캐닝 도구 (본 프로젝트에서 커스텀 구현)

**LLM Red Teaming**: 대규모 언어 모델의 보안 취약점 테스트

---

## Document Change History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 1.0 | 2026-07-29 | 초안 (방어 중심) | Security Team |
| 2.0 | 2026-07-29 | 공격+방어 통합, 웹 스캐너 자체 구현 | Security Team |

---

**최종 수정**: 2026-07-29  
**상태**: 검토 준비 중 (기술 검토 대기)

