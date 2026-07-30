# PRD: Kx CLI Stability & Command UX (v0.3)

**문서 버전**: 0.3.0  
**작성일**: 2026-07-30  
**상태**: DRAFT → 구현 진행  
**담당**: Cursor agent — **명령어 / 시스템 파일만** (디자인·비주얼은 third-party LLM SaaS)  
**충돌 회피**: third-party LLM SaaS PR 경로(`docs/API.md`, `PRD-KX-DEFENDER-V2.md`, `src/core/defense/*` 등)와 **겹치지 않음**  
**관련 증상 (사용자 제보)**: Windows PowerShell Operator Client에서 한글 깨짐, `kx` 동사 실행 실패/불친절, 불필요 HUD 문구

---

## 1. Executive Summary

Kx-Defender의 **1급 인터페이스는 KxLang (`kx`)** 이다.  
현재 Windows HUD에서:

1. **UTF-8/콘솔 코드페이지 불일치**로 한글 메시지가 깨진다 (`시도` → ``).
2. **동사만 입력**하면 `--scope` 누락 등으로 “프로그램이 안 된다”고 느껴진다.
3. HUD에 **장식/안내 문구가 과다**해 명령 결과보다 노이즈가 크다.
4. npx 캐시/버전 불일치로 **구버전(v0.2.1) HUD**가 떠서 수정이 반영되지 않는 경우가 있다.

이 PRD는 **명령이 항상 읽히고, 실행되고, 결과가 깨지지 않게** 만드는 시스템 수정 범위를 정의한다.  
시각 테마(색, 패널 레이아웃, 로고 아트)는 third-party LLM SaaS 디자인 트랙에 맡긴다.

---

## 2. Problem Statement (재현)

| # | 관찰 | 원인 가설 |
|---|---|---|
| P1 | `시도: kx /h` 가 `` 로 표시 | Python stdout이 CP949, Node `encoding:'utf8'` 로 오디코딩 **또는** 콘솔 CP ≠ UTF-8 |
| P2 | `unknown verb '����'` | 입력/파이프 인코딩 깨진 한글·바이너리가 verb로 파싱됨 |
| P3 | `atteck` → unknown verb | 오타; 제안(suggest) 없음 |
| P4 | `sentry` → `--scope is required` | 인터랙티브 세션에서 scope 기본값 없음 → “안 됨”으로 인식 |
| P5 | HUD 상단 `Kx-DEFENDER · Operator Client · LINK`, 하단 `명령 입력 · lang…` | 장식 문구가 명령 UX를 가림 |
| P6 | `KX v0.2.1` 표시 | 영속 앱/`npx` 캐시가 최신 `update` 결과와 불일치 |

---

## 3. Goals / Non-Goals

### Goals
1. **Windows PowerShell + HUD**에서 KxLang 입·출력 **한글/영문 모두 깨지지 않음**.
2. **문서화된 모든 `kx` 동사**가 인터랙티브 HUD와 one-shot CLI에서 **실행 가능** (simulate 기본).
3. 오류 시 **다음 행동 한 줄**만 제시 (장식 문구 제거).
4. `update` / `login kx` 이후 **표시 버전 = 실제 코드 버전**.
5. third-party LLM SaaS 디자인 PR과 **파일 충돌 0**.

### Non-Goals
- Operator Client 패널 레이아웃/색상/로고 리디자인 (third-party LLM SaaS)
- 외부 보안 툴 연동
- Web Console 전면 개편 (별도 PRD)

---

## 4. Role Split

| 트랙 | 담당 | 파일 예 |
|---|---|---|
| **Commands / System** (본 PRD) | Cursor | `scripts/npx-entry.js`, `scripts/kx-update.js`, `scripts/operator-shell.js`(동작만), `scripts/npm-setup.js`, `Install-Kx.ps1`, `services/orchestrator/kx_defender/*`, `fixtures/catalog/kxlang_lexicon.json`, `docs/prd/kx-cli-stability.md` |
| **Design / Visual** | third-party LLM SaaS | Console CSS/HTML 비주얼, FigJam/Figma, 패널 아트 — **명령 문법·인코딩·파서 금지** |

---

## 5. Requirements

### 5.1 Encoding pipeline (P0)

**수용 기준**
- `lang ko` 후 오류/도움말 한글이 PowerShell에서 **정상 표시**.
- `lang en` 후 영문만 표시.
- HUD MAIN 패널에 캡처된 `stdout`/`stderr`도 동일.

**구현 방향**
1. Python 진입점(`kx_cli.py` / `kx` 래퍼)에서  
   `sys.stdout/stderr.reconfigure(encoding="utf-8", errors="replace")`  
   + 환경 `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`.
2. Node spawn (`operator-shell` / `runKx`) env에 위 변수 주입; Windows에서 가능하면 세션 `chcp 65001` (Install-Kx / HUD 기동 시 1회).
3. 캡처 모드: `encoding: "utf8"` 유지; 실패 시 Buffer를 `utf8` → 실패 시 `cp949` 폴백 디코드.
4. 테스트: 한글 문자열 라운드트립 단위 테스트 (Linux CI는 UTF-8만, Windows는 수동/스모크).

### 5.2 Interactive command defaults (P0)

인터랙티브 HUD / classic shell에서만:

| 규칙 | 동작 |
|---|---|
| `--scope` 생략 | 기본 `lab` |
| `--sim` / `--live` 생략 | 기본 `--sim` |
| `--live` + `pact` | 기존 인가 게이트 유지 |
| one-shot `npx … kx …` | **동일 기본값** 적용하되, help에 “default scope=lab (sim)” 명시 |

**수용 기준**
```
kx> sentry
→ simulate 실행 JSON (scope=lab), 에러 아님
kx> roast tickets --realm lab.local
→ 동작
kx> watch procs
→ 동작
```

### 5.3 Lexicon completeness & verb UX (P0)

1. `kx lexicon` / `/h`에 **실제 동작하는 동사만** 노출.
2. unknown verb 시 **가까운 동사 제안** (예: `atteck` → `attack` 계열 또는 `roast`/`breach` 힌트; Levenshtein ≤ 2).
3. 동사만 있고 object 기본값이 있으면 **default_object 자동 적용** (이미 일부 존재) — 전 동사 점검.
4. **스모크 매트릭스** (CI): 각 verb에 대해  
   `kx <verb> [--scope lab --sim]` exit 0 또는 문서화된 non-zero.

대상 동사 패밀리 (lexicon 기준):  
`sentry trace audit harden triage comply forge roast relay loot bait breach crack nexus graph probe sweep watch kill sig …` 및 `/h`·`lang`·`lexicon`·`serve`·`update`·`login`.

### 5.4 HUD copy cleanup (P0) — 시스템 문구만

**삭제 (사용자 요청)**
- 상단: `Kx-DEFENDER  ·  Operator Client  ·  LINK`
- 하단: `명령 입력 · lang ko|en · /h · exit` / 영문 tip
- 기타 “tron link established” 류 **장식 한 줄** (필요 시 버전 한 줄만)

**유지**
- `kx>` / `[login kx]>` 프롬프트
- 명령 결과 / 에러 한두 줄
- (third-party LLM SaaS) 패널 프레임·색 — 문구만 비움

### 5.5 Session / update integrity (P1)

1. HUD에 표시하는 버전 = `package.json` / `SETUP_VERSION` / `~/.kx-defender/app` 중 **실제 로드된 루트**.
2. `update` 후 재진입 시 구 npx 캐시로 돌아가지 않음 (`preferPersistentApp` 유지).
3. Ctrl+C → `[login kx]` 재접속 유지.

### 5.6 Error message contract (P1)

```
KxLang error: <한 줄 원인>
next: <한 줄 조치>     # 예: next: kx /h   또는  next: add --scope lab
```

- 언어별 `t()` 유지하되 **인코딩 보장 후**만 ko 사용.
- “Try:/시도:” 중복·장식 제거 → `next:` 단일 키.

---

## 6. Implementation Plan (phases)

### Phase A — Stop the bleeding (이번 스프린트)
1. UTF-8 파이프라인 (Python + Node + PowerShell chcp)
2. HUD 장식 문구 삭제
3. 인터랙티브/기본 `--scope lab` + `--sim`
4. PRD 본 문서 머지

### Phase B — Command matrix green
1. lexicon 전 verb 스모크 테스트
2. unknown-verb suggest
3. helptext를 lexicon과 단일 소스화
4. Windows 수동 스모크 체크리스트 (`docs` 짧은 절)

### Phase C — Hardening
1. 입력 정규화 (zero-width, 잘못된 코드페이지 입력 감지 → “encoding reset” 안내)
2. `kx doctor` (python/utf-8/app root/version 진단)
3. third-party LLM SaaS 디자인 트랙과 HUD 프레임 API 계약 (텍스트 슬롯만 시스템 소유)

---

## 7. Acceptance Tests

| ID | 절차 | 기대 |
|---|---|---|
| A1 | `lang ko` → 잘못된 동사 | 한글 에러 **깨짐 없음** |
| A2 | `lang en` → 동일 | 영문 에러 |
| A3 | `sentry` (플래그 없음) | lab/sim 실행 성공 |
| A4 | `roast tickets --realm lab.local` | JSON result |
| A5 | `watch procs` | JSON result |
| A6 | `atteck` | unknown + suggest |
| A7 | HUD에 TRON/tip 문구 없음 | 육안 |
| A8 | `update` → `login kx` | 버전 최신 |
| A9 | pytest + verb smoke | green |

---

## 8. Risks

| 위험 | 완화 |
|---|---|
| scope 기본값이 실수 live로 이어짐 | 기본은 **항상 sim**; live는 명시 플래그 |
| chcp 65001이 일부 폰에서 깨짐 | 폴백 en 메시지 + `kx doctor` |
| third-party LLM SaaS가 같은 HUD 파일 수정 | 텍스트 상수만 시스템 소유 / 디자인 충돌 시 third-party LLM SaaS는 CSS·레이아웃만 |

---

## 9. Out of scope file list (do not touch — third-party LLM SaaS / other)

- `PRD-KX-DEFENDER-V2.md`
- `docs/API.md`, `docs/IMPLEMENTATION-PLAN.md`, `docs/KX-COMMANDS.md`, `docs/TECHNICAL-APPROACH.md`, …
- `src/core/defense/*`
- Console **시각** 전용 대규모 CSS 리디자인 (동작 버그 수정 제외)

---

## 10. Success metric

PowerShell에서:

```powershell
npx -y --prefer-online angelsj913/Kx-Defender-
```

이후 `lang ko` / `sentry` / `roast tickets --realm lab.local` / `update` / Ctrl+C → `[login kx]` 가 **추가 설명 없이** 동작하고, 화면에 깨진 한글과 TRON/tip 장식이 없다.
