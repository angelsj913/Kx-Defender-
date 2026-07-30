---
name: kx-attack-llm_redteam
description: Local LLM red-team probes with payload bank and rule evaluator (zero SaaS API keys).
---

# Kx Attack — LLM Red Team

No third-party LLM SaaS/third-party LLM SaaS API keys. Uses `fixtures/llm/` payloads + responses.

## Command

```bash
kxctl attack run llm_redteam --authorized-scope lab --mode execute --target local-fixture
```

## Output

`artifacts.probes`, `artifacts.stats`, `api_keys_used: 0`.
---
