---
name: kx-catalog-defense
description: Run defensive catalog skills — detecting-*, analyzing-*, auditing-*, securing-*, triaging-*, compliance, and defensive building-*.
---

# Kx Catalog — Defense Skills

## Discover

```bash
kxctl modules list --family detecting --names-only
kxctl modules list --family analyzing --names-only
kxctl modules list --family auditing --names-only
kxctl modules list --family securing --names-only
kxctl modules list --family triaging --names-only
kxctl modules list --family compliance --names-only
kxctl modules list --family building_defense --names-only
```

## Examples

```bash
kxctl defense run detecting-anomalous-authentication-patterns --authorized-scope lab --mode simulate
kxctl defense run analyzing-threat-actor-ttps-with-mitre-attack --authorized-scope lab --mode simulate
kxctl defense run auditing-aws-s3-bucket-permissions --authorized-scope owned --mode simulate --target lab.local
kxctl defense run securing-aws-iam-permissions --authorized-scope owned --mode simulate
kxctl defense run triaging-security-incident --authorized-scope lab --mode simulate
kxctl defense run achieving-cmmc-level-2-compliance --authorized-scope lab --mode simulate
kxctl defense run building-detection-rules-with-sigma --authorized-scope lab --mode simulate
```

Use `kxctl skill run <full-name> ...` interchangeably.
---
