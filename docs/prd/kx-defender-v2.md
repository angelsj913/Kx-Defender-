# Kx-Defender PRD v2.0 — Attack Modules Scope (Implemented Slice)

**Status**: Implementation in progress for Phase 1 attack module orchestrator  
**Full product vision**: Windows attack+defense platform (see original PRD v2.0)

## This repository slice

Self-built modules callable via `kxctl`, with Cursor agent skills. **No SaaS API keys.**

### In scope (this PR)

- Common module contract + authorization gate + SQLite run store
- Short attack aliases + **262 catalog skills** (`detecting-*`, `analyzing-*`, `auditing-*`, `securing-*`, `triaging-*`, compliance, defensive `building-*`, `testing-for-*`, named offensive skills)
- Defense stub: process_monitor
- Agent skills under `skills/kx-attack-*` and `skills/kx-catalog-*`

### Hard exclusions

- Custom C2 implants / shellcode / AMSI·ETW bypass
- Real-world phishing kits against cloud IdPs
- Unauthorized targeting of public internet hosts in `execute` mode

### Authorization

- `authorized_scope`: `lab | owned | engagement`
- Default mode: `simulate`
- `execute` only for localhost / RFC1918 / `.lab` / `.local` / `.test` or engagement file allow-list
