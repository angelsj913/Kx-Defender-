# PRD: Kx-Defender (v3.0)

**문서 버전**: 3.0  
**작성일**: 2026-07-29  
**상태**: 현재 코드베이스 기준 재작성 (구현 반영 + 제품 구상)  
**라이선스**: Apache-2.0  
**명령 언어**: KxLang / DEFCOM (`kx`)

> **Authorized & lawful use only.** 공격 기능은 소유 시스템, 서면 승인된 교전(pact), CTF/랩 환경에서만 사용한다.

---

## 1. Executive Summary

**Kx-Defender**는 Windows 중심의 **공격·방어 통합 보안 플랫폼**이다.  
외부 SaaS API 키에 의존하지 않고, 자체 모듈과 **고유 명령 언어(KxLang)** 로 동작한다.

### 핵심 가치
- **방어**: 프로세스 감시, 시그니처/행동 탐지, 감사·하드닝·트리아지·컴플라이언스 워크플로
- **공격(인가 랩)**: AD/Identity/WiFi/웹/LLM 레드팀 워크플로를 KxLang 동사로 통일
- **UX**: CLI는 `kx`, GUI는 eDEX-UI 스타일 대시보드(후속 위상)
- **에이전트**: Cursor 스킬이 Anthropic 스킬명이 아니라 **KxLang** 을 사용

### 현재 구현 상태 (v3 기준 사실)
| 영역 | 상태 |
|---|---|
| KxLang (`kx`, `/h`, lexicon) | ✅ 구현됨 |
| 오케스트레이터 + 인가 게이트 + SQLite | ✅ 구현됨 |
| 공격 코어 모듈 8 + 방어 stub | ✅ 랩/시뮬 경로 |
| 카탈로그 스킬 262 | ✅ family handler 기반 |
| Electron eDEX UI | ❌ 미구현 |
| Windows 실시간 커널급 모니터링 | ❌ 미구현 (stub만) |
| 커스텀 C2 임플란트 / AMSI 우회 | ❌ 의도적 제외 |

---

## 2. Problem Statement

### 방어
- 프로세스 행동·웹 위협·컴플라이언스가 도구별로 분절됨
- 연구자/CTF 사용자가 여러 CLI를 외워야 함

### 공격 (Red Team / 랩)
- Kerberoasting, NTLM relay, DPAPI, OAuth device-code, WiFi, C2, LLM 테스트가 각각 다른 도구
- 에이전트(AI)가 외부 스킬 이름에 종속되면 제품 정체성이 없음

### 해결
**하나의 제품 언어(KxLang) + 하나의 오케스트레이터 + 모듈 계약**으로 공격/방어를 통합한다.

---

## 3. Goals

### 3.1 Product Goals
1. KxLang이 유일한 1급 사용자/에이전트 인터페이스
2. 인가 게이트 없는 `live` 실행 불가
3. 방어·공격 결과가 동일 Result 스키마/DB로 저장
4. Windows 엔드포인트에서 방어 실시간성 확보 (후속 위상)
5. UI에서 KxLang 명령을 시각적으로 실행/재생

### 3.2 Non-Goals (명시적 제외)
- 커스텀 임플란트/셸코드 생성
- AMSI/ETW 우회 페이로드
- 실클라우드 무단 피싱 자동화
- 공개 인터넷 대상 기본 `live` 스캔
- 외부 LLM SaaS API 키 필수 의존

### 3.3 Success Metrics (제품)
| 지표 | 목표 |
|---|---|
| KxLang 동사 커버리지 | 방어/공격 핵심 플로우 100% `kx`로 가능 |
| 인가 우회 | `live` + 비인가 대상 → 거부율 100% |
| CLI 도움말 | `kx /h`로 초보자가 5분 내 첫 명령 실행 |
| 모듈 테스트 | CI에서 simulate 전 카탈로그 green |
| UI 초기 로딩 (후속) | <2초 |
| 방어 차단 응답 (후속) | <500ms |

---

## 4. Personas

1. **보안 연구자** — 탐지/분석/웹 스캔, 로컬 랩
2. **Red Team** — 인가된 AD/Identity/웹 시뮬레이션
3. **CTF 참가자** — 빠른 `kx` 명령, 직관적 도움말
4. **시스템 관리자 (후속)** — 모니터링·정책·리포트

---

## 5. Product Surface

### 5.1 KxLang (DEFCOM) — Primary CLI

```
kx <VERB> <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]
kx /h
kx /h <VERB>
kx lexicon
```

| Verb | 영역 |
|---|---|
| `sentry` `trace` `audit` `harden` `triage` `comply` `forge` | 방어 |
| `roast` `relay` `loot` `bait` `breach` `crack` | AD/Identity/WiFi |
| `nexus` `graph` `probe` `sweep` | C2 listener / Graph mock / LLM / Web |
| `watch` | 프로세스 |

상세: [`docs/kxlang.md`](../kxlang.md)

### 5.2 Low-level CLI
`kxctl` — 모듈 레지스트리/디버그용. 제품 UX의 아님.

### 5.3 GUI (후속 위상) — “Console”
- eDEX-UI 감성: 다크, 사이언/마젠타 액센트, 모노스페이스
- 패널: Sentry(방어) / Strike(공격) / Sweep(웹) / Nexus(세션) / Ledger(로그)
- 모든 UI 액션은 내부적으로 KxLang 명령으로 변환·기록

---

## 6. Functional Requirements

### 6.1 Platform Core (✅ / partial)
- [x] 모듈 계약 (`validate` → `run` → `ModuleResult`)
- [x] 인가 게이트 (`lab|owned|engagement`, simulate/execute)
- [x] SQLite run store
- [x] KxLang 파서 + `/h`
- [x] 카탈로그 팩토리 (262)
- [ ] 이벤트 버스 (WebSocket) for UI
- [ ] 설정/프로파일 암호화 저장 (AES-256)
- [ ] 업데이트 채널 (시그니처/페이로드 팩)

### 6.2 Defense
| 기능 | 현재 | 목표 |
|---|---|---|
| 프로세스 스냅샷 | stub | Windows ETW/WMI 실시간 |
| 차단/종료 | 없음 | UI/CLI 원클릭 <500ms |
| YARA | 없음 | 메모리/파일 스캔 |
| 행동 점수 | 카탈로그 시뮬 | Top-N 패턴 엔진 |
| detecting/analyzing/... | family handler | 실제 데이터 소스 연동 |

### 6.3 Attack (lab-authorized)
| 기능 | 현재 | 목표 |
|---|---|---|
| roast / relay / loot | fixture/시뮬 | 랩 AD fixture → 제한적 live |
| bait / breach / graph | mock IdP/Graph | 로컬 mock 고도화 (클라우드 API 키 없음) |
| crack | handshake fixture | 오프라인 PCAP만 |
| nexus | echo listener | 멀티 리스너/세션 테이블 (임플란트 없음) |
| sweep | 자체 웹 스캐너 | OWASP Top 10 확장 + 리포트 |
| probe | 로컬 페이로드/규칙 | 로컬 모델 어댑터(선택, API 키 불필요) |

### 6.4 Reporting
- JSON 결과 (✅)
- HTML/PDF 리포트 (후속)
- Ledger 검색/필터 (후속)

---

## 7. System Requirements

- OS: Windows 10/11 x64 (1급), Linux/macOS (CLI/랩 개발)
- Python 3.9+
- 관리자 권한: 방어 live / 일부 공격 live
- RAM 8GB+, Disk 2GB+
- (후속) Node/Electron for Console UI

---

## 8. Scope by Phase

### Phase A — Foundation (현재 / 완료에 가까움)
- KxLang, orchestrator, auth, catalog, core modules, tests, docs

### Phase B — Defense Engine (다음 구현 우선)
- Windows process monitor (ETW/WMI)
- Kill/quarantine actions
- YARA integration
- Behavioral scoring v1
- `kx watch` / `kx sentry` live 경로

### Phase C — Strike Lab Hardening
- AD lab fixtures + safe live against private ranges
- Web scanner depth + HTML report
- LLM probe local adapter
- Nexus multi-listener + session ledger (no implant)

### Phase D — Console UI
- Electron + React eDEX-style shell
- Streams orchestrator events
- Command palette = KxLang

### Phase E — Ops
- Multi-host agent (optional)
- Central ledger
- Policy packs / compliance evidence export

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| 공격 기능 악용 | `--scope`/`--live` 게이트, pact 파일, 기본 `--sim` |
| 범위 과다 (262 스킬) | KxLang 동사로 UX 축소, 카탈로그는 백엔드 |
| Windows API 복잡도 | Phase B에서 ETW PoC 먼저 |
| UI 과설계 | Console은 KxLang 래퍼로만 시작 |
| 라이선스/법적 | Apache-2.0 + Authorized-use NOTICE, WiFi/C2 범위 제한 |

---

## 10. Open Decisions

1. Console UI 패키징: Electron vs Tauri
2. YARA 규칙 초기 소스 및 업데이트 채널
3. Windows 서비스화 여부 (항상 상주 vs on-demand)
4. 배포 채널 (GitHub Release only vs installer)

---

## 11. Acceptance (v3 Product Definition)

제품이 “동작한다”고 말하려면 최소:
1. `kx /h`로 언어를 학습할 수 있고
2. 방어·공격 대표 명령이 `--sim`에서 성공하며
3. `--live`는 인가 대상에서만 통과하고
4. 결과가 SQLite에 남으며
5. 문서/PRD/아키텍처가 코드와 일치한다

---

## Document History

| Ver | Date | Notes |
|---|---|---|
| 1.0 | 2026-07-29 | 방어 중심 초안 (외부) |
| 2.0 | 2026-07-29 | 공격+방어 통합 초안 (외부) |
| 2.0-slice | 2026-07-29 | 레포 내 구현 슬라이스 메모 |
| **3.0** | **2026-07-29** | **코드 반영 PRD + KxLang 중심 재작성** |
