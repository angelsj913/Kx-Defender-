# Kx-Defender

Windows-oriented attack + defense security platform (Phase 1 slice): **self-built modules**, **`kxctl` CLI**, and **Cursor agent skills**.

> **Authorized & lawful use only.** Attack modules are for systems you own or have explicit written permission to test (lab / CTF / engagement).

License: **Apache-2.0** (not MIT). See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## What this slice includes

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

**Not included:** custom C2 implants, AMSI/ETW bypass, real phishing kits, SaaS LLM API calls.

## Install

```bash
python3 -m pip install -e ".[dev]"
```

## Agent-friendly CLI

```bash
kxctl modules list

kxctl attack run kerberoasting --authorized-scope lab --mode simulate --domain lab.local
kxctl attack run web_scanner --authorized-scope owned --mode execute --url http://127.0.0.1:8080/
kxctl attack run llm_redteam --authorized-scope lab --mode execute --target local-fixture

kxctl result list
kxctl result show <run_id>

kxctl defense run process_monitor --authorized-scope lab --mode simulate
```

### Authorization rules

- `--authorized-scope` is required: `lab | owned | engagement`
- Default `--mode` is `simulate`
- `execute` requires localhost / RFC1918 / `.lab` / `.local` / `.test` **or** `--engagement-file` allow-list

## Cursor skills

Agent skills live under [`skills/`](skills/). Each skill documents the exact `kxctl` invocation for one module.

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
