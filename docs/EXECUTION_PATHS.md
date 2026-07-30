# Kx-Defender 프로그램 실행 경로 분석

**프로젝트**: Kx-Defender (Windows-oriented Attack + Defense Platform)  
**진입점**: `scripts/npx-entry.js`, `scripts/npm-kx.js`  
**생성일**: 2026-07-30

---

## 📋 명령어 실행 경로 목록

### 🎯 Defense Family (방어 명령어)

#### 1. sentry — 위협 탐지
```
kx sentry [subcommand] --scope [lab|owned|pact] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/ → engines/kxsig.py → engines/report.py
```

#### 2. trace — 추적/분석
```
kx trace [target] --scope [lab|owned|pact] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/process_monitor.py → engines/kxwatch.py → engines/report.py
```

#### 3. audit — 감시/검사
```
kx audit [component] --scope [lab|owned|pact] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/ → rules/kxsig/ → engines/kxsig.py → engines/report.py
```

#### 4. harden — 강화
```
kx harden [target] --scope [lab|owned|pact] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/ → engines/kxaction.py → engines/report.py
```

#### 5. triage — 분류
```
kx triage [alert] --scope [lab|owned|pact] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/sig_scan.py → rules/kxsig/core.json → engines/kxsig.py → engines/report.py
```

#### 6. comply — 준수
```
kx comply [policy] --scope [lab|owned|pact] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/ → rules/kxsig/ → engines/kxsig.py → engines/report.py
```

#### 7. forge — 구성/생성
```
kx forge [config] --scope [lab|owned|pact] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/ → engines/kxaction.py → engines/report.py
```

#### 8. sig scan — 시그니처 스캔
```
kx sig scan --scope lab --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/sig_scan.py → rules/kxsig/core.json → engines/kxsig.py → engines/report.py
```

#### 9. watch procs — 프로세스 모니터
```
kx watch procs --scope lab --live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/process_monitor.py → engines/kxwatch.py → engines/report.py
```

#### 10. kill pid — 프로세스 종료
```
kx kill pid --scope lab --pid [PID] --sim|--live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/defense/process_kill.py → engines/kxaction.py → engines/report.py
```

---

### 🔴 Attack Family (공격 명령어)

#### 11. roast tickets — Kerberoasting
```
kx roast tickets --scope lab --realm lab.local --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/kerberoasting.py → fixtures/ad/spns.json → engines/kxscore.py → engines/report.py
```

#### 12. relay — NTLM Relay
```
kx relay [type] --scope lab --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/ntlm_relay.py → fixtures/ad/ → engines/kxscore.py → engines/report.py
```

#### 13. loot — 데이터 탈취
```
kx loot [target] --scope owned --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/dpapi.py → fixtures/dpapi/secrets.json → engines/kxscore.py → engines/report.py
```

#### 14. bait — 미끼 배치
```
kx bait [type] --scope owned --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/device_code.py → engines/kxscore.py → engines/report.py
```

#### 15. breach — 침해
```
kx breach [target] --scope pact --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/llm_redteam.py → fixtures/llm/payloads.json → engines/kxscore.py → engines/report.py
```

#### 16. crack — 크랙
```
kx crack [type] --scope lab --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/wifi.py → fixtures/wifi/handshake.txt → fixtures/wifi/wordlist.txt → engines/kxscore.py → engines/report.py
```

---

### 🌐 Infrastructure Family (인프라 명령어)

#### 17. nexus listen — C2 리스너
```
kx nexus listen --scope lab --bind 127.0.0.1:4455 --live
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/c2.py → engines/nexus_store.py → engines/report.py
```

#### 18. graph — 그래프 모의
```
kx graph [query] --scope lab --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/c2.py → fixtures/ad/spns.json → engines/kxscore.py → engines/report.py
```

#### 19. probe — 프로브/탐사
```
kx probe [endpoint] --scope lab --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/web_scanner.py → fixtures/catalog/payloads.json → engines/kxscore.py → engines/report.py
```

#### 20. sweep web — 웹 스캔
```
kx sweep web --scope owned --url http://127.0.0.1:8080/ --sim
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/attack/web_scanner.py → fixtures/catalog/payloads.json → engines/kxscore.py → engines/report.py
```

---

### 📚 Utility Commands (유틸리티 명령어)

#### 21. lexicon — 스킬 사전
```
kx lexicon
  → npx-entry.js → npm-kx.js → npm-setup.js → runKx() → modules/__main__.py 
  → modules/catalog/factory.py → fixtures/catalog/kxlang_lexicon.json → fixtures/catalog/skills.json (262개) → engines/report.py
```

#### 22. lang — 언어 설정
```
kx lang [ko|en]
  → npx-entry.js → kx-shell.js → readLang() / writeLang() → ~/.kx-defender/config.json
```

#### 23. update — 업데이트
```
kx update
  → npm-kx.js → scripts/kx-update.js → GitHub 최신 버전 다운로드
```

#### 24. help / /h — 도움말
```
kx /h  또는  kx help
  → npx-entry.js → npm-kx.js → printHelp() → banner.js → 도움말 출력
```

#### 25. exit / quit — 종료
```
kx exit  또는  kx quit  또는  Ctrl+C
  → kx-shell.js → readline.close() → 프로세스 종료
```

---

### 🖥️ Interactive Shell (인터랙티브 쉘)

#### 26. kx — 대화형 쉘 시작
```
kx
  → npx-entry.js → npm-setup.js → ensureSetup() → kx-shell.js → startKxShell()
  → banner.js → printKxBanner() → readline REPL 시작
  → User Input (명령어 입력) → KxLang Parser
  → fixtures/catalog/kxlang_lexicon.json (명령어 검증)
  → modules/catalog/factory.py (스킬 로드)
  → 해당 모듈 라우팅 (attack/defense/engines)
```

---

## 🔗 데이터 로드 순서 (Sequential Data Loading)

모든 명령어 실행 시 공통적으로 따르는 데이터 로드 순서:

```
User Input Command
  ↓
1. fixtures/catalog/kxlang_lexicon.json
   └─ 명령어 유효성 검증
   └─ 파라미터 구조 검증
  ↓
2. fixtures/catalog/param_schema.json
   └─ 파라미터 타입 및 범위 검증
  ↓
3. fixtures/catalog/skills.json (262개 스킬 메타데이터)
   └─ 스킬 인스턴스 생성
   └─ 카탈로그 초기화
  ↓
4. 명령어별 Fixtures 선택 로드
   ├─ roast → fixtures/ad/spns.json (Service Principal Names)
   ├─ relay → fixtures/ad/* (AD 구조)
   ├─ loot → fixtures/dpapi/secrets.json (DPAPI 테스트 시크릿)
   ├─ bait → fixtures/llm/fixture_responses.json (IdP 시뮬레이션)
   ├─ breach → fixtures/llm/payloads.json (LLM 페이로드)
   ├─ crack → fixtures/wifi/handshake.txt, wordlist.txt (WiFi)
   ├─ graph → fixtures/ad/ (AD 그래프)
   ├─ probe → fixtures/catalog/payloads.json (웹 페이로드)
   └─ sweep → fixtures/catalog/payloads.json (웹 스캔)
  ↓
5. 규칙 로드 (Defense 명령어)
   ├─ rules/kxsig/core.json (핵심 시그니처)
   └─ rules/kxsig/user/*.json (사용자 정의 규칙)
  ↓
6. Engines 실행
   ├─ kxaction.py (액션 실행: 프로세스 종료, 구성 변경)
   ├─ kxscore.py (위협도 점수 계산)
   ├─ kxsig.py (시그니처 매칭)
   ├─ kxwatch.py (프로세스 모니터링)
   ├─ nexus_store.py (C2 세션 저장소)
   └─ kxaction.py (실행 결과 처리)
  ↓
7. report.py (결과 포맷 변환)
   ├─ JSON 포맷
   ├─ CLI 테이블
   └─ 결과 출력
  ↓
CLI Output (사용자 화면)
```

---

## 🔄 모듈별 책임 분담

| 계층 | 파일/모듈 | 책임 |
|------|---------|------|
| **Entry** | `npx-entry.js` | 프로세스 시작 |
| **CLI Router** | `npm-kx.js` | 명령어 라우팅 |
| **Setup** | `npm-setup.js` | 환경 초기화, Python 실행 |
| **Shell** | `kx-shell.js` | 인터랙티브 REPL |
| **Parser** | modules/__main__.py | 명령어 파싱, 권한 검증 |
| **Attack** | modules/attack/* | 공격 시뮬레이션 |
| **Defense** | modules/defense/* | 방어 동작 |
| **Catalog** | modules/catalog/* | 스킬 로딩, 카탈로그 관리 |
| **Engines** | modules/engines/* | 실행, 계산, 저장 |
| **Fixtures** | fixtures/* | 고정 데이터 (테스트, 사전) |
| **Rules** | rules/kxsig/* | 탐지 규칙 |
| **Skills** | skills/* | 262개 카탈로그 스킬 |

---

## 🎯 권한 검증 흐름

모든 명령어 실행 전 다음 순서로 권한 검증:

```
1. Scope 검증
   ├─ 'lab'       → 로컬 테스트 환경 (항상 허용)
   ├─ 'owned'     → RFC1918 + .local/.test/.lab (IP 범위 검증)
   └─ 'pact'      → --engagement-file 필수 (명시적 허가)

2. Mode 검증
   ├─ '--sim'     → Simulation (기본값, 안전)
   └─ '--live'    → Execution (실제 실행, 제한)

3. 호스트 검증
   ├─ localhost (127.0.0.1, ::1)
   ├─ RFC1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
   ├─ .local/.test/.lab 도메인
   └─ 또는 --engagement-file 화이트리스트

4. 명령어 실행 승인
```

---

## 📊 명령어 분류 요약

### Defense Family (7개)
- sentry, trace, audit, harden, triage, comply, forge

### Attack Family (6개)
- roast, relay, loot, bait, breach, crack

### Infrastructure Family (4개)
- nexus, graph, probe, sweep

### Utility (5개)
- lexicon, lang, update, help, exit

### Interactive (1개)
- kx (shell)

**총 23개 주요 명령어 + 4개 서브커맨드 = 27개**

---

## 🔗 파일 의존성 맵

```
User Input
  ↓
scripts/npx-entry.js (start)
  ├─ scripts/npm-setup.js (setup)
  ├─ scripts/kx-shell.js (shell)
  ├─ scripts/banner.js (UI)
  └─ scripts/npm-kx.js (CLI routing)
    ↓
modules/__main__.py (parser)
  ├─ modules/attack/* (attack modules)
  ├─ modules/defense/* (defense modules)
  ├─ modules/catalog/* (skill catalog)
  └─ modules/engines/* (execution)
    ↓
fixtures/ (data)
  ├─ fixtures/catalog/ (lexicon, skills)
  ├─ fixtures/ad/ (AD data)
  ├─ fixtures/dpapi/ (secrets)
  ├─ fixtures/llm/ (LLM data)
  └─ fixtures/wifi/ (WiFi data)
    ↓
rules/ (detection rules)
  └─ rules/kxsig/ (Kx signatures)
    ↓
Output (CLI)
```

---

**문서 생성**: `/understand` 스킬 실행 전 준비 문서  
**마지막 업데이트**: 2026-07-30
