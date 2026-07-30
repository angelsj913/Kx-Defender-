# Kx-Defender

Windows-oriented attack + defense platform with proprietary **KxLang/DEFCOM** (`kx`), orchestrator, and in-house modules.

License: **Apache-2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## KxLang (primary interface)

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

# Console UI
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

## Install & run (PowerShell eDEX HUD)

```powershell
npx clear-npx-cache; npx -y --prefer-online angelsj913/Kx-Defender-
# after first install, refresh without reinstall:
npx -y --prefer-online angelsj913/Kx-Defender- update
```

CLI stability PRD: [`docs/prd/kx-cli-stability.md`](docs/prd/kx-cli-stability.md)

```
 kx> /h
 kx> lang ko
 kx> sentry
 kx> roast tickets --realm lab.local
 kx> update
 kx> exit
```

### Session lock & re-login

| Action | Command |
|---|---|
| Lock session | `Ctrl+C` |
| Re-enter HUD | `login kx` or `[login kx]` |
| Update without reinstall | `update` / `kx update` / `npx -y --prefer-online angelsj913/Kx-Defender- update` |

Persistent install lives under `~/.kx-defender/app`. Shims: `login-kx`, `kx-update` (PATH: `%LOCALAPPDATA%\Kx-Defender\bin`).

Plain shell: `--classic` · Web Console: `serve`

One-shot:

```powershell
npx -y --prefer-online angelsj913/Kx-Defender- kx /h
npx -y --prefer-online angelsj913/Kx-Defender- kx roast tickets --scope lab --sim
npx -y --prefer-online angelsj913/Kx-Defender- update
npx -y --prefer-online angelsj913/Kx-Defender- login kx
```

Optional web Console (only when requested):

```powershell
npx -y --prefer-online angelsj913/Kx-Defender- serve
```

Also: `irm https://raw.githubusercontent.com/angelsj913/Kx-Defender-/main/Install-Kx.ps1 | iex`

If Python is missing, portable CPython is downloaded once to `~/.kx-defender/python`.

### Platform from a clone

```bash
npm install
node scripts/npx-entry.js
# or: node scripts/kx-shell.js
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

- **Primary:** `skills/kxlang` — use `kx` / KxLang
- Catalog guides: `skills/kx-catalog-attack`, `skills/kx-catalog-defense`
- Legacy helpers: `skills/kx-attack-*`
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
