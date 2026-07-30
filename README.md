# Kx-Defender

**Self-built** Windows-oriented attack + defense platform. Proprietary **KxLang/DEFCOM** (`kx`), orchestrator, and in-house modules.

> **Authorized & lawful use only.**  
> **Self-Built Only:** 외부 보안 프로그램(Impacket/Aircrack/Havoc/ZAP/Garak 등)을 **가져오지 않습니다.**  
> 사용자가 지정한 스킬은 능력 목록일 뿐, 구현은 전부 이 레포에서 직접 작성합니다.  
> 정책: [`docs/policy-self-built.md`](docs/policy-self-built.md)

License: **Apache-2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## KxLang (primary interface)

Kx-Defender has its own command grammar — do **not** drive the product with Anthropic skill names.

```bash
kx /h
kx lexicon

# Strike / Sentry
kx roast tickets --scope lab --realm lab.local --sim
kx watch procs --scope lab --live
kx sig scan --scope lab --sim
kx kill pid --scope lab --pid 4242 --sim
kx nexus listen --scope lab --bind 127.0.0.1:4455 --live
kx sweep web --scope owned --url http://127.0.0.1:8080/ --sim

# Console UI (self-built)
kx serve --bind 127.0.0.1:8787
# open http://127.0.0.1:8787/
```

Full grammar: [`docs/kxlang.md`](docs/kxlang.md)  
Lexicon: [`fixtures/catalog/kxlang_lexicon.json`](fixtures/catalog/kxlang_lexicon.json)  
**PRD v3:** [`docs/prd/kx-defender-v3.md`](docs/prd/kx-defender-v3.md)  
**Architecture:** [`docs/architecture.md`](docs/architecture.md)

| Verb | Meaning |
|---|---|
| `sentry` / `trace` / `audit` / `harden` / `triage` / `comply` / `forge` | Defense families |
| `roast` / `relay` / `loot` / `bait` / `breach` / `crack` | AD / identity / wifi |
| `nexus` / `graph` / `probe` / `sweep` | C2 listener / Graph mock / LLM / web |
| `watch` | Process monitor |

Flags: `--scope lab|owned|pact`, `--sim` (default), `--live`, `--at`, `--realm`, `--url`, `--bind`, `--pact-file`

## What this slice includes

### Short aliases (legacy)

| Module | Type | Notes |
|---|---|---|
| `kerberoasting` | attack | SPN/TGS lab fixtures |
| `ntlm_relay` | attack | ESC8 state machine (lab) |
| `dpapi` | attack | Fixture secret decode (masked) |
| `device_code` | attack | Mock IdP only (no cloud API keys) |
| `wifi` | attack | Handshake fixture dictionary crack |
| `c2` | attack | Listener/session manager only (no implant) |
| `web_scanner` | attack | Self-built crawler + SQLi/XSS/CSRF |
| `llm_redteam` | attack | Local payload bank + rule scoring |
| `process_monitor` | defense | Snapshot stub |

### Full catalog skills (262)

Loaded from [`fixtures/catalog/skills.json`](fixtures/catalog/skills.json):

| Family | Count | Examples |
|---|---|---|
| `attack_named` | 10 | Entra(KxBreach), OAuth device-code, Nexus listeners, NTLM ESC8, DPAPI, WiFi, Kerberoasting, KxGraph, KxProbe |
| `testing_for` | 12 | `testing-for-*` → 자체 KxSweep |
| `detecting` | 96 | `detecting-*` → 자체 Sentry handlers |
| `analyzing` | 76 | `analyzing-*` |
| `auditing` | 12 | `auditing-*` |
| `securing` | 13 | `securing-*` |
| `triaging` | 5 | `triaging-*` |
| `compliance` | 7 | CMMC, PCI-DSS, NERC CIP, ... |
| `building_defense` | 31 | defensive `building-*` blueprints |

**금지:** 외부 보안 바이너리 래핑, 커스텀 임플란트, AMSI 우회, SaaS LLM API 키 필수 의존.

## Install

```bash
npx --yes kx-defender add --all -g
```

Installs bundled agent skills into `~/.agents/skills` and `~/.cursor/skills`.  
Quiet output — no GitHub Source banner, no Eve/PromptScript errors.

Equivalents:

```bash
npx --yes kx-defender --all -g
node scripts/npx-entry.js add --all -g
```

> Do **not** use the third-party `npx skills add …` CLI for this repo — it always prints a GitHub Source line and fails on agents that lack global skill support (Eve, PromptScript).

### Platform runtime (optional)

Requires **Node.js 16+** and **Python 3.9+**:

```bash
npx --yes kx-defender setup
# or from a clone:
npm install && npm start
kx /h
npm test
```

## Low-level CLI (`kxctl`)

Prefer `kx` (KxLang). `kxctl` remains for debugging/module inspection:

```bash
kxctl modules families
kxctl modules list --family detecting --names-only
kxctl skill run attacking-entra-id-with-roadtools --authorized-scope lab --mode simulate --domain contoso.lab.local
kxctl result list
```

### Authorization rules

- `--authorized-scope` is required: `lab | owned | engagement`
- Default `--mode` is `simulate`
- `execute` requires localhost / RFC1918 / `.lab` / `.local` / `.test` **or** `--engagement-file` allow-list

## Cursor skills

Agent skills live under [`skills/`](skills/):

- **Primary:** `skills/kxlang` — use `kx` / KxLang (self-built only)
- Catalog guides: `skills/kx-catalog-attack`, `skills/kx-catalog-defense`
- Legacy helpers: `skills/kx-attack-*`
- Policy: [`docs/policy-self-built.md`](docs/policy-self-built.md)
- PRD: [`docs/prd/kx-defender-v3.md`](docs/prd/kx-defender-v3.md)
- Architecture: [`docs/architecture.md`](docs/architecture.md)

## Tests

```bash
python3 -m pytest -q
```

## Layout

```
modules/attack/          # self-built attack modules
modules/defense/         # defense stubs
services/orchestrator/   # kx_defender package + kxctl
skills/                  # Cursor agent skills
fixtures/                # lab fixtures (AD, wifi, llm, dpapi)
docs/prd/                # PRD slice
```
