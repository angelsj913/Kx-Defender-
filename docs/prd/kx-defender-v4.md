# PRD: Kx DEFCOM — Command Integrity & Product Expansion (v4.0)

**문서 버전**: 4.0  
**작성일**: 2026-07-30  
**상태**: APPROVED FOR IMPLEMENTATION  
**제품**: Kx-Defender / KxLang DEFCOM  
**라이선스**: Apache-2.0  

---

## 0. Why this PRD

현장 보고:
1. **정상 명령이 먹지 않음** / 같은 문장만 반복
2. **실행 경로가 과도하게 복잡** (Node 런처 → 영속 app → Python CLI → 파서 → 오케스트레이터)
3. **`lang ko` 후에도 실행 결과가 영어**로 유지
4. README에 핵심 기능 나열이 과도함
5. 웹 콘솔은 폐기했는데 **잔여 코드**가 남음
6. 목표: 로컬에서 **더 빠르고·설명 가능하고·쓰기 쉬운** 보안 오퍼레이터 클라이언트

---

## 1. Product baseline (Kx 목표 상태)

| 영역 | Kx DEFCOM 목표 |
|---|---|
| 형태 | `kx` 네이티브 터미널 클라이언트 + 영속 `update` |
| 실시간 | 로컬 `daemon` / `watch --continuous` |
| 탐지·대응 | `sig` / `kill` / `quarantine` / `report` (자체 엔진) |
| 위생 | `clean dns\|browser\|cache\|temp` (로드맵) |
| 설명 가능 | `why` / `alert` / `report` / `audit` |
| UX | 단축 명령 **1경로**, 빠른 스코프 스캔, `kx update` |
| 언어 | **ko/en 완전 일관** (설정 → 도움말 → 결과) |
| 인가 랩 | Strike 동사 (roast/relay/… ) — 인가된 lab/owned/pact만 |
| 업데이트 | `kx update` 원커맨드 |

---

## 2. Current failure modes (검증된 원인)

- 오케스트레이터 자체는 동사 실행 OK인 경우가 많음
- `lang ko`는 config에 저장되지만 help/렌더가 영어면 “언어가 안 바뀐다”로 체감
- 런처 다층 / soft-lock / stale persistent app → **동일 고정 문장** 반복

### Root-cause classes
| ID | 원인 | 증상 |
|---|---|---|
| RC1 | Help/렌더 i18n 미적용 | `lang ko` 후에도 영어 |
| RC2 | 런처 다층 | 명령이 meta/TUI로 새어감 |
| RC3 | 웹 `serve` 잔여 | 혼란·동일 에러 문구 |
| RC4 | README 기능 나열 | GitHub 노출 과다 |
| RC5 | 방어 워크플로 UX 미정비 | 청소·위생 명령 부재 |

---

## 3. Goals

### P0 — Command & language integrity
1. **단일 명령 파이프라인**: `kx <verb> …` → 동일 파서 → 오케스트레이터
2. Meta만 예외: `lang | update | /h | lexicon | daemon | alert | report | why | form | suggest | ask`
3. `lang ko|en` → 도움말·에러·pretty·클라이언트에 즉시 반영
4. 성공 명령은 **새 결과** (동일 고정 문장 금지)

### P0 — Remove noise
5. README = 설치·실행만
6. 웹 콘솔 관련 코드·플래그 **완전 삭제**
7. 외부 제품명/경쟁 비교 문구를 공개 문서에 **기재하지 않음**

### P1 — Defend & operator excellence
8. **Defend pack**: `clean dns`, `clean browser`, `clean cache`, `clean adware`
9. **Realtime**: daemon + continuous watch + alerts
10. **Explainability**: `why`, `report`, `sig catalog`
11. **Perf**: quick vs full scan; 진행률
12. **Usability**: suggest, form ask, 한국어 우선

### Non-goals
- Electron/웹 UI 재도입
- 외부 보안 바이너리 래핑 (Self-Built Only)
- 실클라우드 무단 공격

---

## 4. Architecture — simplified command path

```
PowerShell: kx …
    └─ scripts/npm-kx.js
         ├─ meta: update → kx-update.js
         ├─ bare / login* → kx-client (TUI)
         └─ else → Python kx_cli.main(argv)   # ONE path
              ├─ meta verbs (lang, /h, daemon, …)
              └─ parse_argv → Orchestrator.run → render (lang-aware)
```

금지:
- 임의 substring 매칭으로 Strike 명령을 TUI에 삼키기
- 구버전 `~/.kx-defender/app`로 update 외 명령 리다이렉트 (semver gate)
- `serve` 진입점

---

## 5. Language contract

| Surface | `lang=en` | `lang=ko` |
|---|---|---|
| `kx lang` | English | 한국어 |
| `kx /h` | English | 한국어 |
| errors | English | 한국어 힌트 |
| `--pretty` / client | English labels | 한국어 라벨 |
| JSON raw fields | English keys | 동일 키 |

우선순위: `KX_LANG` > `~/.kx-defender/config.json` > `en`

---

## 6. Roadmap

### Phase A — Stability (이번 스프린트)
- RC1–RC4 수정, soft-lock 동사 해제, TUI `--pretty`
- README 슬림, 웹 잔여 제거, 브랜드 로고 고정
- Bugbot / security-review / code-review

### Phase B — Clean suite
- `kx clean dns|browser|cache|temp`
- `kx sig scan --profile quick`
- 리포트 한글 섹션

### Phase C — Realtime & performance
- daemon 설치 경로 단순화
- alert → kill 제안
- quick profile p95 측정

### Phase D — Operator excellence
- TUI 패널 안정화
- suggest 항상 동작
- 설치 1줄 UX

---

## 7. Acceptance

- `kx lang ko` → `kx /h` 한국어
- `kx <verb> … --sim` 동사별 **서로 다른** ok 결과
- soft-lock 후 동사 입력 시 해제·실행
- `kx update`로 최신 트리
- 공개 README/PRD에 외부 제품명·경쟁 비교 없음
