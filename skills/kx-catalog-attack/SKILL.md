---
name: kx-catalog-attack
description: Run named offensive catalog capabilities via KxLang/kxctl using self-built engines only.
---

# Kx Catalog — Attack (Self-Built)

Authorized lab use only. **No external security binaries.**

Skill names are capability IDs. Engines are Kx-Defender modules.

```bash
kx /h
kx breach entra --scope lab --realm contoso.lab.local --sim
kx bait dcode --scope lab --at mock.idp.local --live
kx nexus listen --scope lab --bind 127.0.0.1:4455 --live
kx relay esc8 --scope lab --at adcs.lab.local --sim
kx loot vault --scope lab --at 127.0.0.1 --live
kx crack wifi --scope lab --at LabWiFi --live
kx roast tickets --scope lab --realm lab.local --sim
kx graph pull --scope lab --at lab.local --sim
kx probe mind --scope lab --at local-fixture --live
kx sweep xss --scope owned --url http://127.0.0.1/?q=1 --sim
```
---
