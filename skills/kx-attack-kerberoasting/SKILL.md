---
name: kx-attack-kerberoasting
description: Run Kx-Defender Kerberoasting lab module via kxctl (SPN/TGS fixtures, no live AD required for simulate).
---

# Kx Attack — Kerberoasting

Authorized lab use only.

## When to use

- Need SPN enumeration / TGS hash artifacts for AD lab workflows
- Agent should call `kxctl`, not invent Impacket commands

## Command

```bash
kxctl attack run kerberoasting --authorized-scope lab --mode simulate --domain lab.local
kxctl attack run kerberoasting --authorized-scope lab --mode execute --domain lab.local
```

## Output

JSON with `artifacts.spns`, `artifacts.tgs_hashes`, `run_id`.

## Forbidden

- Running against domains you do not own / lack written authorization for
---
