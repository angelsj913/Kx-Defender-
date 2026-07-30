# Kx-Defender 입력 가능한 명령어 전체 Tree

**프로젝트**: Kx-Defender (Windows 중심 공격 + 방어 플랫폼)  
**인터페이스**: KxLang / CLI  
**기본 사용법**: `kx [command] [subcommand] [options]`

---

## 📋 전체 명령어 Tree

```
kx/
│
├─ 🔴 ATTACK FAMILY (공격 명령어 - 7개)
│  │
│  ├─ roast ........................... Kerberos 티켓 공격
│  │  └─ tickets [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --realm <domain>
│  │     ├─ --sim (시뮬레이션 - 기본값)
│  │     └─ --live (실제 실행)
│  │
│  ├─ relay ........................... NTLM 릴레이 공격
│  │  └─ [type] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ loot ............................ 데이터 탈취 (DPAPI)
│  │  └─ [target] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ bait ............................ 미끼 배치 (OAuth)
│  │  └─ [type] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ breach .......................... 침해 시뮬레이션 (LLM)
│  │  └─ [target] [options]
│  │     ├─ --scope [pact] (필수)
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ crack ........................... 패스워드 크랙 (WiFi)
│  │  └─ [type] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  └─ nexus ........................... C2 리스너 (네트워크)
│     ├─ listen
│     │  ├─ --scope [lab|owned|pact]
│     │  ├─ --bind <host:port>
│     │  ├─ --sim
│     │  └─ --live
│     └─ [other subcommands]
│
│
├─ 🟢 DEFENSE FAMILY (방어 명령어 - 7개)
│  │
│  ├─ sentry .......................... 위협 탐지
│  │  └─ [target] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ trace ........................... 추적/분석
│  │  └─ [target] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ audit ........................... 감시/검사
│  │  └─ [component] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ harden .......................... 강화
│  │  └─ [target] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ triage .......................... 분류
│  │  └─ [alert] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ comply .......................... 준수
│  │  └─ [policy] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ forge ........................... 구성/생성
│  │  └─ [config] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ sig ............................ 시그니처 명령어
│  │  └─ scan [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim (기본값)
│  │     └─ --live
│  │
│  ├─ watch ........................... 모니터링
│  │  ├─ procs [options]
│  │  │  ├─ --scope [lab|owned|pact]
│  │  │  ├─ --sim
│  │  │  └─ --live
│  │  └─ [other targets]
│  │
│  └─ kill ............................ 강제 종료
│     ├─ pid [options]
│     │  ├─ --scope [lab|owned|pact]
│     │  ├─ --pid <PID>
│     │  ├─ --sim
│     │  └─ --live
│     └─ [other targets]
│
│
├─ 🌐 INFRASTRUCTURE FAMILY (인프라 명령어 - 4개)
│  │
│  ├─ graph ........................... 그래프 모의
│  │  └─ [query] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ probe ........................... 프로브/탐사
│  │  └─ [endpoint] [options]
│  │     ├─ --scope [lab|owned|pact]
│  │     ├─ --sim
│  │     └─ --live
│  │
│  ├─ sweep ........................... 웹 스캔
│  │  ├─ web [options]
│  │  │  ├─ --scope [lab|owned|pact]
│  │  │  ├─ --url <target_url>
│  │  │  ├─ --sim
│  │  │  └─ --live
│  │  └─ [other targets]
│  │
│  └─ (nexus 포함 - 위 ATTACK 섹션 참고)
│
│
└─ ⚙️ UTILITY COMMANDS (유틸리티 - 6개)
   │
   ├─ lexicon ......................... 스킬 사전 조회
   │  └─ (옵션 없음)
   │
   ├─ lang ............................ 언어 설정
   │  ├─ ko (한국어)
   │  └─ en (영어)
   │
   ├─ update .......................... 버전 업데이트
   │  └─ (또는 upgrade)
   │
   ├─ help ............................ 도움말 표시
   │  ├─ /h
   │  └─ --help
   │
   ├─ exit ............................ 프로그램 종료
   │  ├─ exit
   │  ├─ quit
   │  └─ q
   │
   └─ (interactive shell)
      └─ kx (대화형 쉘 시작)
         ├─ 프롬프트: Kx>
         └─ 명령어 자동완성 지원


```

---

## 🎯 주요 Flag 정리

### Scope 옵션 (필수/권한별)
```
--scope lab        → 로컬 테스트 환경 (항상 허용)
--scope owned      → RFC1918 + .local/.test/.lab (IP 검증)
--scope pact       → 명시적 허가 필요 (--engagement-file)
```

### Mode 옵션
```
--sim              → 시뮬레이션 (기본값, 안전)
--live             → 실제 실행 (제한됨)
```

### 기타 옵션
```
--realm <domain>   → 타겟 도메인
--bind <host:port> → 바인딩 주소:포트
--url <target>     → 타겟 URL
--pid <PID>        → 타겟 프로세스 ID
--at <timestamp>   → 시간 지정
```

---

## 📊 명령어 분류 요약

| 카테고리 | 개수 | 예시 | 주용도 |
|---------|------|------|--------|
| **Attack** | 7 | roast, relay, breach | 공격 시뮬레이션 |
| **Defense** | 10 | sentry, audit, watch | 방어 및 모니터링 |
| **Infrastructure** | 4 | nexus, sweep, graph | 네트워크 관리 |
| **Utility** | 6 | lexicon, lang, help | 도구 관리 |
| **Total** | **27** | - | - |

---

## 🔑 사용 예시

### 예시 1: Kerberoasting 공격
```bash
kx roast tickets --scope lab --realm lab.local --sim
```

### 예시 2: 시그니처 스캔
```bash
kx sig scan --scope lab --sim
```

### 예시 3: 프로세스 모니터링
```bash
kx watch procs --scope lab --live
```

### 예시 4: 웹 스캔
```bash
kx sweep web --scope owned --url http://127.0.0.1:8080/ --sim
```

### 예시 5: C2 리스너
```bash
kx nexus listen --bind 127.0.0.1:4455 --live
```

### 예시 6: 스킬 조회
```bash
kx lexicon
```

### 예시 7: 대화형 쉘
```bash
kx
Kx> roast tickets --scope lab --sim
Kx> lang ko
Kx> exit
```

---

## 🛡️ 권한 검증 흐름

```
명령어 입력
  ↓
1️⃣ Scope 검증
   ├─ lab      → ✅ 허용 (로컬)
   ├─ owned    → 🔒 IP 검증 (RFC1918)
   └─ pact     → 🔐 화이트리스트 필수

  ↓
2️⃣ Mode 검증
   ├─ --sim    → ✅ 시뮬레이션 (안전)
   └─ --live   → 🔴 실제 실행 (제한)

  ↓
3️⃣ 호스트 검증
   ├─ localhost (127.0.0.1)
   ├─ RFC1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
   ├─ .local/.test/.lab 도메인
   └─ 또는 --engagement-file 화이트리스트

  ↓
✅ 명령어 실행
```

---

## 📈 계층별 명령어 흐름

```
User Input (명령어)
  ↓
scripts/npm-kx.js (CLI 라우터)
  ↓
scripts/npm-setup.js (환경 초기화)
  ↓
modules/__main__.py (파서)
  ├─ KxLang 검증
  ├─ 파라미터 검증
  └─ 권한 확인
  ↓
modules/attack/ 또는 modules/defense/
  ├─ 공격 모듈 로드
  ├─ Fixtures 로드
  └─ 엔진 실행
  ↓
modules/engines/
  ├─ kxaction (실행)
  ├─ kxscore (점수 계산)
  ├─ kxsig (시그니처)
  └─ kxwatch (감시)
  ↓
modules/engines/report.py
  ├─ JSON 포맷
  ├─ CLI 테이블
  └─ 결과 출력
  ↓
User Output (결과)
```

---

## ✨ 주요 특징

✅ **27개 주요 명령어**  
✅ **3단계 권한 검증** (Scope → Mode → Host)  
✅ **시뮬레이션 기본 설정** (안전성 우선)  
✅ **한국어/영어 언어 지원**  
✅ **대화형 쉘 + 원샷 명령 모두 지원**  
✅ **262개 Claude AI 스킬 통합**  

---

**이 문서 저장**: `.ua/COMMANDS_TREE.md`  
**동반 문서**: `.ua/EXECUTION_PATHS.md` (각 명령어 상세 실행 경로)
