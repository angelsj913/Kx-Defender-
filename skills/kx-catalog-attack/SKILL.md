---
name: kx-catalog-attack
description: Run named offensive catalog skills (Entra, OAuth device code, Havoc/Sliver C2 listeners, NTLM ESC8, DPAPI, WiFi, Kerberoasting, GraphRunner mock, Garak-style LLM, testing-for-*).
---

# Kx Catalog — Attack Skills

Authorized lab use only. No SaaS API keys. No implants/AMSI bypass.

## Discover

```bash
kxctl modules families
kxctl modules list --family attack_named --names-only
kxctl modules list --prefix testing-for- --names-only
```

## Named skills

```bash
kxctl skill run attacking-entra-id-with-roadtools --authorized-scope lab --mode simulate --domain contoso.lab.local
kxctl skill run attacking-oauth-with-device-code-phishing --authorized-scope lab --mode execute --target mock.idp.local
kxctl skill run building-red-team-c2-infrastructure-with-havoc --authorized-scope lab --mode execute --host 127.0.0.1 --port 4455 --action start_listener
kxctl skill run building-c2-infrastructure-with-sliver-framework --authorized-scope lab --mode simulate --action status
kxctl skill run relaying-ntlm-for-adcs-esc8 --authorized-scope lab --mode simulate --target adcs.lab.local
kxctl skill run abusing-dpapi-for-credential-access --authorized-scope lab --mode execute --target 127.0.0.1
kxctl skill run performing-wifi-password-cracking-with-aircrack --authorized-scope lab --mode execute --essid LabWiFi
kxctl skill run performing-kerberoasting-attack --authorized-scope lab --mode execute --domain lab.local
kxctl skill run post-exploiting-microsoft-graph-with-graphrunner --authorized-scope lab --mode simulate --target lab.local
kxctl skill run red-teaming-llms-with-garak --authorized-scope lab --mode execute --target local-fixture
kxctl skill run testing-for-xss-vulnerabilities --authorized-scope owned --mode execute --url http://127.0.0.1:8080/?q=test
```
---
