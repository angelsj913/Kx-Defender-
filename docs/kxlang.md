# KxLang (DEFCOM) — Kx-Defender Command Language

Kx-Defender 전용 명령 언어입니다. Anthropic 스킬 이름이나 일반 보안 도구 CLI를 그대로 쓰지 않고, **고유 동사(verb) + 대상(object) + 플래그**로 동작합니다.

## 문법

```
kx <VERB> <OBJECT> [flags...]
```

- `VERB`: 대소문자 무시 (권장: 소문자)
- `OBJECT`: 하이픈/슬래시 허용 (`auth-anomalies`, `web`, `havoc`)
- 기본 출력: JSON (도움말은 텍스트)

### 도움말

```bash
kx /h              # 전체 도움말
kx /h roast        # 동사별 도움말
kx roast /h        # 동사별 도움말 (동일)
kx -h
kx --help
kx help
kx ?
```

### 플래그 (KxLang 고유)

| Flag | 의미 | 내부 매핑 |
|---|---|---|
| `--scope lab\|owned\|pact` | 인가 범위 (필수) | `authorized_scope` (`pact`→`engagement`) |
| `--sim` | 시뮬레이션 (기본) | `mode=simulate` |
| `--live` | 인가된 실실행 | `mode=execute` |
| `--at <target>` | 대상 호스트/테넌트/ESSID/URL | `target` / 문맥별 |
| `--realm <domain>` | AD/Entra 도메인 | `domain` |
| `--url <url>` | 웹 대상 | `url` |
| `--bind <host:port>` | 리스너 바인드 | `host`, `port` |
| `--pact-file <path>` | 교전 허용 목록 | `engagement_file` |
| `--with key=value` | 추가 파라미터 | 자유 키 |

## 동사 체계

| Verb | 역할 | 예시 |
|---|---|---|
| `sentry` | 탐지 (`detecting-*`) | `kx sentry detect auth-anomalies --scope lab --sim` |
| `trace` | 분석 (`analyzing-*`) | `kx trace analyze mitre-ttps --scope lab --sim` |
| `audit` | 감사 (`auditing-*`) | `kx audit check s3 --scope owned --sim` |
| `harden` | 하드닝 (`securing-*`) | `kx harden apply iam --scope owned --sim` |
| `triage` | 트리아지 | `kx triage sort incident --scope lab --sim` |
| `comply` | 컴플라이언스 | `kx comply map cmmc --scope lab --sim` |
| `forge` | 방어 구축 (`building-*`) | `kx forge build sigma-rules --scope lab --sim` |
| `roast` | Kerberoasting | `kx roast tickets --scope lab --realm lab.local --sim` |
| `relay` | NTLM/ESC8 | `kx relay esc8 --scope lab --at adcs.lab.local --sim` |
| `loot` | DPAPI 시크릿 | `kx loot vault --scope lab --at 127.0.0.1 --live` |
| `bait` | Device-code OAuth | `kx bait dcode --scope lab --at mock.idp.local --live` |
| `breach` | Entra ID recon | `kx breach entra --scope lab --realm contoso.lab.local --sim` |
| `crack` | WiFi fixture crack | `kx crack wifi --scope lab --at LabWiFi --live` |
| `nexus` | C2 리스너(임플란트 없음) | `kx nexus listen havoc --scope lab --bind 127.0.0.1:4455 --live` |
| `graph` | Graph 모의 수집 | `kx graph pull mail --scope lab --at lab.local --sim` |
| `probe` | LLM 레드팀(로컬) | `kx probe mind --scope lab --at local-fixture --live` |
| `sweep` | 웹/테스팅 | `kx sweep web --scope owned --url http://127.0.0.1/ --live` |
| `watch` | 프로세스 감시 | `kx watch procs --scope lab --sim` |
| `lexicon` | 동사/오브젝트 사전 | `kx lexicon` |
| `help` | 도움말 | `kx help roast` |

## 설계 원칙

1. **Self-Built Only**: 외부 보안 프로그램을 가져오거나 감싸지 않음 ([policy](policy-self-built.md))
2. **브랜드 언어**: KxLang 동사만 노출 (외부 툴 CLI 이름 금지)
3. **인가 우선**: `--scope` 없으면 거부
4. **안전 기본값**: `--sim` 기본, `--live`는 랩/사설망/pact만
5. **지정 스킬 = 능력 목록**: 구현체는 전부 Kx 엔진

## 하위 호환

저수준 API는 계속 `kxctl`로 제공됩니다. 에이전트/사용자는 **`kx` (KxLang)** 을 기본으로 사용합니다.
