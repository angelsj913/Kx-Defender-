---
name: kx-attack-device_code
description: Simulate OAuth device-code phishing against local mock IdP (no cloud API keys).
---

# Kx Attack — Device Code

Authorized lab use only. Uses `mock.idp.local` style targets — never real Microsoft/Google APIs.

## Command

```bash
kxctl attack run device_code --authorized-scope lab --mode execute --target mock.idp.local
```

## Output

Masked access token + verification URI for mock IdP.

## Forbidden

- Real phishing campaigns / real cloud device-code abuse
---
