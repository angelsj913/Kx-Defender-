---
name: kx-attack-wifi
description: Crack WiFi handshake fixtures with local dictionary via kxctl wifi module (no live RF).
---

# Kx Attack — WiFi

Authorized lab use only. Operates on fixtures under `fixtures/wifi/`.

## Command

```bash
kxctl attack run wifi --authorized-scope lab --mode execute --essid LabWiFi
```

## Output

`artifacts.cracked`, `artifacts.password_masked`.

## Forbidden

- Attacking networks without written authorization
---
