---
name: kx-attack-ntlm_relay
description: Run Kx-Defender NTLM relay / ADCS ESC8 lab state-machine module via kxctl.
---

# Kx Attack — NTLM Relay (ESC8)

Authorized lab use only.

## Command

```bash
kxctl attack run ntlm_relay --authorized-scope lab --mode simulate --target adcs.lab.local
kxctl attack run ntlm_relay --authorized-scope lab --mode execute --target adcs.lab.local
```

## Output

`artifacts.session` stage list + masked certificate stub.

## Forbidden

- Relaying against production ADCS without engagement authorization
---
