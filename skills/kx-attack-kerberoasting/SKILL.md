---
name: kx-attack-kerberoasting
description: Run self-built KxRoast lab module via kx/kxctl (no external Kerberos tool binaries).
---

# Kx Attack — Kerberoasting (Self-Built)

Authorized lab use only.

```bash
kx roast tickets --scope lab --realm lab.local --sim
kx roast tickets --scope lab --realm lab.local --live
```

Forbidden: installing/calling external roasting toolchains.
---
