# PRD: Kx-Defender (v3.1)

**문서 버전**: 3.1  
**작성일**: 2026-07-29  
**상태**: **APPROVED** — 전체 시스템 구현 진행  
**라이선스**: Apache-2.0  
**명령 언어**: KxLang / DEFCOM (`kx`)  
**강제 정책**: [`docs/policy-self-built.md`](../policy-self-built.md)

> **Authorized & lawful use only.** 공격 기능은 소유 시스템, 서면 승인된 교전(pact), CTF/랩 환경에서만 사용한다.

---

## 0. Self-Built Only (최상위 불변 조건)

**다른 외부 보안 프로그램을 가져오지 않는다.**  
기능은 사용자가 지정한 스킬 목록을 **개념 참조**로만 쓰고, **엔진·프로토콜·스캐너·리스너·탐지 로직은 전부 직접 작성**한다.

| 허용 | 금지 |
|---|---|
| 사용자가 지정한 스킬 이름/워크플로 개념 | Impacket, Aircrack, Hashcat, Havoc, Sliver, ZAP, Burp, Garak, ROADtools, GraphRunner 등 **설치·호출·래핑** |
| Python 표준 라이브러리 + OS API | 외부 보안 바이너리 shell-out |
| 자체 포맷 (`KxSig`, `KxRule`, fixtures) | “유명 도구 연동”으로 기능 대체 |
| KxLang 명령 표면 | 외부 도구 CLI를 제품 UX로 노출 |

이 조건을 어기는 설계/PR은 제품이 아니다.

---

## 1. Executive Summary

**Kx-Defender**는 Windows 중심의 **공격·방어 통합 보안 플랫폼**이다.  
외부 보안 도구/SaaS에 의존하지 않고, **자체 구현 모듈**과 **고유 명령 언어(KxLang)** 로 동작한다.

### 핵심 가치
- **방어**: 자체 프로세스 감시·시그니처(`KxSig`)·행동 점수·감사/하드닝/트리아지/컴플라이언스
- **공격(인가 랩)**: AD/Identity/WiFi/웹/LLM 레드팀 워크플로를 **직접 구현**하고 KxLang으로 통일
- **UX**: `kx` 언어, (후속) 자체 Console UI
- **에이전트**: Cursor 스킬도 KxLang만 사용

### 현재 구현 상태
| 영역 | 상태 |
|---|---|
| Self-Built Only 정책 문서 | ✅ |
| KxLang (`kx`, `/h`, lexicon, `serve`) | ✅ (stdlib) |
| 오케스트레이터 + 인가 게이트 + SQLite | ✅ |
| 공격 코어 + KxSweep HTML report + Nexus ledger | ✅ |
| KxWatch / KxScore / KxAction / KxSig | ✅ |
| 지정 스킬 카탈로그 262 (개념→자체 handler) | ✅ |
| 자체 Console UI (`kx serve`) | ✅ stdlib HTTP + HTML/CSS/JS |
| Windows 센서 | ✅ tasklist 경로 / POSIX /proc (심화 여지) |
| 외부 툴 래핑 | ❌ 금지·미사용 |

---

## 2. Problem Statement

분절된 외부 도구 집합 대신, **하나의 자체 엔진**으로 공격/방어 학습·실험·인가 테스트를 수행한다.  
외부 프로그램 설치 없이 KxLang만으로 동일 UX를 제공한다.

---

## 3. Goals

### 3.1 Product Goals
1. **100% self-built engines** (지정 스킬 개념만 외부 참조)
2. KxLang이 유일한 1급 인터페이스
3. 인가 게이트 없는 `live` 불가
4. 동일 Result/Ledger 스키마
5. Windows 방어 실시간성 (후속, 자체 센서)
6. 자체 Console UI (후속)

### 3.2 Non-Goals
- 외부 보안 프로그램 번들/연동/포크
- 커스텀 임플란트/셸코드/AMSI·ETW 우회
- 실클라우드 무단 피싱
- 공개 인터넷 기본 `live`
- SaaS LLM API 키 필수 의존

---

## 4. Personas

연구자 / Red Team(인가) / CTF / 관리자(후속) — 모두 **KxLang**으로 접근.

---

## 5. Product Surface

### 5.1 KxLang
```
kx <VERB> <OBJECT> --scope lab|owned|pact [--sim|--live]
kx /h
kx lexicon
```
상세: [`docs/kxlang.md`](../kxlang.md)

### 5.2 `kxctl`
저수준 디버그. 제품 UX 아님.

### 5.3 Console (후속)
자체 UI. 시각 레퍼런스만 허용(스타일), **eDEX 등 외부 앱을 포함하지 않음**.  
모든 액션 → KxLang 문자열 → Orchestrator.

---

## 6. Functional Requirements

### 6.1 Core
- [x] 모듈 계약 / auth / SQLite / KxLang / catalog
- [ ] Event bus
- [ ] 설정 AES 저장
- [ ] 자체 규칙 팩 업데이트 (`KxSig`/`KxRule`)

### 6.2 Defense (자체)
| 기능 | 현재 | 목표 |
|---|---|---|
| 프로세스 | stub | 자체 Windows 센서 |
| 차단 | 없음 | 자체 action API |
| 시그니처 | 없음 | **KxSig** (자체 규칙 엔진) |
| 행동 점수 | 시뮬 | 자체 scorers |
| family skills | handler | 센서 데이터 연결 |

### 6.3 Attack (자체, 인가 랩)
지정 스킬 개념을 자체 모듈로 구현: roast/relay/loot/bait/breach/crack/nexus/graph/probe/sweep 등.  
**원본 도구를 실행하지 않음.**

### 6.4 Reporting
JSON ✅ → HTML/PDF 자체 생성기 (후속)

---

## 7. System Requirements

- Windows 10/11 x64 (1급), Linux/macOS (CLI 개발)
- Python 3.9+ (표준 라이브러리 우선)
- 관리자 권한: 방어/일부 live
- 외부 보안 바이너리: **불필요·금지**

---

## 8. Phases

| Phase | 내용 | Self-built 제약 |
|---|---|---|
| A | Language + orchestrator + modules | ✅ 현재 |
| B | Windows sensor, KxSig, kill, sentry live | 자체 센서/규칙만 |
| C | Strike lab 심화, sweep report, nexus sessions | 자체 프로토콜만 |
| D | Console UI | 자체 앱 (스타일 참고만) |
| E | packs / multi-host | 자체 에이전트 |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| “일단 유명한 툴 붙이자” 유혹 | Self-Built Only Law / PR 체크리스트 |
| 구현량 과다 | KxLang 동사로 UX 축소, 엔진은 점진 심화 |
| 악용 | scope/live 게이트, pact, 기본 sim |

---

## 10. Acceptance

1. 외부 보안 프로그램 의존 0  
2. `kx /h`로 언어 학습 가능  
3. 지정 스킬 능력이 자체 모듈로 실행됨  
4. live는 인가 대상만  
5. PRD/정책/코드 일치  

---

## History

| Ver | Notes |
|---|---|
| 3.0 | KxLang 중심 재작성 |
| **3.1** | **Self-Built Only 최상위 고정, 외부 툴 연동 전면 금지** |
