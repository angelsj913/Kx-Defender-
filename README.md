# Kx-Defender

Windows-oriented attack + defense security platform (Phase 1 slice): **self-built modules**, proprietary **KxLang/DEFCOM** command language (`kx`), low-level `kxctl`, and **Cursor agent skills**.

> **Authorized & lawful use only.** Attack modules are for systems you own or have explicit written permission to test (lab / CTF / engagement).

License: **Apache-2.0** (not MIT). See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## KxLang (primary interface)

Kx-Defender has its own command grammar — do **not** drive the product with Anthropic skill names.

```bash
kx lexicon
kx help roast

kx roast tickets --scope lab --realm lab.local --sim
kx sentry detect --scope lab --sim
kx nexus listen --scope lab --bind 127.0.0.1:4455 --live
kx sweep web --scope owned --url http://127.0.0.1:8080/ --live
kx probe mind --scope lab --at local-fixture --live
kx forge sigma-rules --scope lab --sim
```

Full grammar: [`docs/kxlang.md`](docs/kxlang.md)  
Lexicon: [`fixtures/catalog/kxlang_lexicon.json`](fixtures/catalog/kxlang_lexicon.json)

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
| `attack_named` | 10 | Entra/ROADtools, OAuth device code, Havoc/Sliver listeners, NTLM ESC8, DPAPI, WiFi, Kerberoasting, GraphRunner mock, Garak-style LLM |
| `testing_for` | 12 | `testing-for-xss-vulnerabilities`, JWT, XXE, ... |
| `detecting` | 96 | `detecting-*` |
| `analyzing` | 76 | `analyzing-*` |
| `auditing` | 12 | `auditing-*` |
| `securing` | 13 | `securing-*` |
| `triaging` | 5 | `triaging-*` |
| `compliance` | 7 | CMMC, PCI-DSS, NERC CIP, ... |
| `building_defense` | 31 | defensive `building-*` (Sigma, SIEM, IR playbooks, ...) |

**Not included:** custom C2 implants, AMSI/ETW bypass, real phishing kits, SaaS LLM API calls.

## Install

```bash
python3 -m pip install -e ".[dev]"
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
