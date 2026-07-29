---
name: kxlang
description: Use Kx-Defender's proprietary KxLang/DEFCOM command language via the `kx` CLI (not Anthropic skill names).
---

# KxLang (DEFCOM)

Always prefer `kx` over raw `kxctl` or Anthropic skill names.

## Grammar

```
kx <VERB> <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]
```

## Meta

```bash
kx lexicon
kx help roast
```

## Attack examples

```bash
kx roast tickets --scope lab --realm lab.local --sim
kx relay esc8 --scope lab --at adcs.lab.local --sim
kx loot vault --scope lab --at 127.0.0.1 --live
kx bait dcode --scope lab --at mock.idp.local --live
kx breach entra --scope lab --realm contoso.lab.local --sim
kx crack wifi --scope lab --at LabWiFi --live
kx nexus listen --scope lab --bind 127.0.0.1:4455 --live
kx nexus sliver --scope lab --sim
kx graph pull --scope lab --at lab.local --sim
kx probe mind --scope lab --at local-fixture --live
kx sweep web --scope owned --url http://127.0.0.1:8080/ --live
kx sweep xss --scope owned --url http://127.0.0.1/?q=1 --sim
```

## Defense examples

```bash
kx sentry detect --scope lab --sim
kx trace mitre-ttps --scope lab --sim
kx audit s3 --scope owned --sim
kx harden iam --scope owned --sim
kx triage incident --scope lab --sim
kx comply cmmc --scope lab --sim
kx forge sigma-rules --scope lab --sim
kx watch procs --scope lab --sim
```

## Flags

- `--scope lab|owned|pact` (required; `pact` = engagement)
- `--sim` (default) / `--live`
- `--at`, `--realm`, `--url`, `--bind host:port`, `--pact-file`, `--with key=value`

See `docs/kxlang.md`.
---
