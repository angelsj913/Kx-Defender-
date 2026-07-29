---
name: kxlang
description: Use Kx-Defender's proprietary KxLang/DEFCOM `kx` CLI. Self-built engines only — never install or call external security tools.
---

# KxLang (DEFCOM)

Always prefer `kx`. Never suggest Impacket/Aircrack/Havoc/ZAP/Garak/etc.

Self-Built Only: [`docs/policy-self-built.md`](../../docs/policy-self-built.md)

## Grammar

```
kx <VERB> <OBJECT> --scope lab|owned|pact [--sim|--live] [flags]
```

## Meta / Help

```bash
kx /h
kx /h roast
kx roast /h
kx lexicon
```

## Examples

```bash
kx roast tickets --scope lab --realm lab.local --sim
kx sentry detect --scope lab --sim
kx nexus listen --scope lab --bind 127.0.0.1:4455 --live
kx sweep web --scope owned --url http://127.0.0.1:8080/ --live
kx probe mind --scope lab --at local-fixture --live
```

See `docs/kxlang.md`.
---
