# Kx-Defender 프로그램 & 명령어 가이드

**프로젝트**: Kx-Defender (Windows 중심 공격 + 방어 플랫폼)  
**언어**: Python, JavaScript  
**진입점**: `kx` (KxLang CLI)

---

## 🚀 빠른 시작

### 설치
```bash
npm install
node scripts/npx-entry.js
# 또는
npx -y --prefer-online angelsj913/Kx-Defender-
```

### 기본 명령어
```bash
kx                           # 대화형 쉘 시작
kx roast tickets --scope lab --sim     # Kerberoasting 시뮬레이션
kx sig scan --scope lab --sim          # 시그니처 스캔
kx lexicon                   # 262개 스킬 조회
kx /h                        # 도움말
```

---

## 📚 프로그램 구조

### 아키텍처 계층

```
User Input (명령어)
  ↓
NPX Entry (scripts/npx-entry.js)
  ↓
CLI Router (scripts/npm-kx.js)
  ↓
Environment Setup (scripts/npm-setup.js)
  ↓
Python Parser (modules/__main__.py)
  ├─ KxLang 검증
  ├─ 파라미터 검증
  └─ 권한 확인
  ↓
Modules (Python)
  ├─ Attack (8개): C2, DPAPI, Kerberoasting, WiFi, etc
  ├─ Defense (3개): Process Monitor, Process Kill, Sig Scan
  ├─ Catalog (2개): Factory, Handlers
  └─ Engines (6개): KxAction, KxScore, KxSig, KxWatch, etc
  ↓
Services (Orchestrator)
  ├─ KxLang Parser
  ├─ Registry
  ├─ Auth & Store
  └─ Render & Report
  ↓
Output (JSON/CLI/Table)
```

### 디렉토리 구조

```
kx-defender/
├─ scripts/              # Node.js 진입점 & 런타임
│  ├─ npx-entry.js     (프로세스 시작)
│  ├─ npm-kx.js        (CLI 라우터)
│  ├─ kx-shell.js      (대화형 쉘)
│  ├─ npm-setup.js     (환경 초기화)
│  └─ ... (기타 유틸리티)
│
├─ modules/             # Python 핵심 로직
│  ├─ attack/          (8개 공격 모듈)
│  ├─ defense/         (3개 방어 모듈)
│  ├─ catalog/         (스킬 팩토리)
│  └─ engines/         (실행 엔진)
│
├─ services/            # Orchestrator 서비스
│  └─ orchestrator/kx_defender/
│     ├─ orchestrator.py (메인)
│     ├─ kxlang.py      (언어 파서)
│     ├─ registry.py    (모듈 레지스트리)
│     ├─ auth.py        (권한)
│     └─ ... (17개 서비스)
│
├─ fixtures/            # 테스트 데이터
│  ├─ catalog/         (스킬, 사전)
│  ├─ ad/              (AD SPN 데이터)
│  ├─ dpapi/           (시크릿)
│  ├─ llm/             (LLM 페이로드)
│  └─ wifi/            (WiFi 데이터)
│
├─ rules/               # 탐지 규칙
│  └─ kxsig/           (시그니처)
│
├─ skills/              # 262개 Claude AI 스킬
│  ├─ kx-attack-*      (8개)
│  ├─ kx-catalog-*     (2개)
│  └─ kxlang           (언어)
│
├─ tests/               # 테스트 (7개)
├─ docs/                # 문서
│  ├─ architecture.md
│  ├─ kxlang.md
│  ├─ API.md
│  ├─ COMMANDS_TREE.md       ✨ 명령어 Tree
│  ├─ EXECUTION_PATHS.md     ✨ 실행 경로
│  └─ PROGRAM_GUIDE.md       ✨ 이 문서
│
└─ .ua/                 # 분석 결과
   ├─ knowledge-graph.json ✨ 프로젝트 구조
   ├─ COMMANDS_TREE.md
   ├─ EXECUTION_PATHS.md
   └─ .understandignore
```

---

## 🎯 명령어 분류

### 공격 (7개)
| 명령어 | 설명 | 모듈 |
|--------|------|------|
| `roast tickets` | Kerberos 공격 | kerberoasting.py |
| `relay` | NTLM 릴레이 | ntlm_relay.py |
| `loot` | DPAPI 탈취 | dpapi.py |
| `bait` | OAuth 미끼 | device_code.py |
| `breach` | LLM 침해 | llm_redteam.py |
| `crack` | WiFi 크랙 | wifi.py |
| `nexus listen` | C2 리스너 | c2.py |

### 방어 (10개)
| 명령어 | 설명 | 모듈 |
|--------|------|------|
| `sentry` | 위협 탐지 | defense/*.py |
| `trace` | 추적/분석 | defense/*.py |
| `audit` | 감시/검사 | defense/*.py |
| `harden` | 강화 | defense/*.py |
| `triage` | 분류 | defense/*.py |
| `comply` | 준수 | defense/*.py |
| `forge` | 구성 | defense/*.py |
| `sig scan` | 시그니처 | sig_scan.py |
| `watch procs` | 프로세스 모니터 | process_monitor.py |
| `kill pid` | 프로세스 종료 | process_kill.py |

### 인프라 (4개)
| 명령어 | 설명 |
|--------|------|
| `graph` | 그래프 모의 |
| `probe` | 탐사/프로브 |
| `sweep web` | 웹 스캔 |
| `nexus` | C2 (위 공격 섹션) |

### 유틸리티 (7개)
| 명령어 | 설명 |
|--------|------|
| `lexicon` | 262개 스킬 조회 |
| `lang ko\|en` | 언어 설정 |
| `update` | 버전 업데이트 |
| `help / /h` | 도움말 |
| `uninstall` | 데이터/캐시 삭제 |
| `exit / quit` | 종료 |
| `kx` | 대화형 쉘 |

---

## 🛡️ 권한 & 보안

### Scope (필수)
```
--scope lab        로컬 테스트 (항상 허용)
--scope owned      RFC1918 네트워크 (IP 검증)
--scope pact       명시적 허가 (--engagement-file)
```

### Mode (기본: --sim)
```
--sim              시뮬레이션 (안전)
--live             실제 실행 (제한)
```

### 권한 검증 흐름
```
입력 → Scope 검증 → Mode 검증 → 호스트 검증 → 실행
```

---

## 📊 주요 통계

| 항목 | 수량 |
|------|------|
| **총 명령어** | 28 |
| **공격 모듈** | 8 |
| **방어 모듈** | 3 |
| **엔진** | 6 |
| **서비스** | 17 |
| **스킬** | 262 |
| **테스트** | 7 |

---

## 🔑 사용 예시

### 예시 1: Kerberoasting
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

### 예시 5: 대화형 쉘
```bash
kx
Kx> roast tickets --scope lab --sim
Kx> lang ko
Kx> lexicon
Kx> exit
```

---

## 📖 상세 문서

- **[COMMANDS_TREE.md](COMMANDS_TREE.md)** — 전체 명령어 Tree (한눈에 보기)
- **[EXECUTION_PATHS.md](EXECUTION_PATHS.md)** — 각 명령어 상세 실행 경로
- **[knowledge-graph.json](../.ua/knowledge-graph.json)** — 프로젝트 구조 분석 (JSON)
- **[architecture.md](architecture.md)** — 아키텍처 상세
- **[kxlang.md](kxlang.md)** — KxLang 언어 사양
- **[API.md](API.md)** — REST API 문서

---

## 🧪 테스트 실행

```bash
npm test
# 또는
node scripts/npm-test.js
```

테스트 파일:
- `test_ad_wifi_c2.py` — 통합 테스트
- `test_auth.py` — 인증 테스트
- `test_catalog.py` — 카탈로그 테스트
- `test_kxlang.py` — 언어 파서 테스트
- `test_local_execute.py` — 로컬 실행 테스트
- `test_modules_simulate.py` — 모듈 시뮬레이션
- `test_system.py` — 시스템 통합 테스트

---

## 🔄 프로젝트 분석

이 프로젝트는 다음 도구로 분석되었습니다:
- **Claude Code**: `/understand` 스킬 (지식 그래프 생성)
- **분석 결과**: `.ua/knowledge-graph.json` (78개 노드, 47개 엣지)
- **구조 분석**: 7계층 아키텍처, 8단계 학습 경로

---

## 📝 라이선스

Apache-2.0  
See [LICENSE](../LICENSE) and [NOTICE](../NOTICE)

---

**마지막 업데이트**: 2026-07-30  
**Git Commit**: 495e926a56c017af85101d44654ea5cdb51a1f1d
