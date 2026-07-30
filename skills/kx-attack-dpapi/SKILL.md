---
name: kx-attack-dpapi
description: Decode DPAPI lab fixture secrets with Kx-Defender dpapi module (masked output).
---

# Kx Attack — DPAPI

Authorized lab use only.

## Command

```bash
kxctl attack run dpapi --authorized-scope lab --mode execute --target 127.0.0.1
```

## Output

`artifacts.credentials[]` with `secret_masked` fields only.

## Forbidden

- Dumping real user DPAPI stores without authorization
---
