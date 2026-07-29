---
name: kx-attack-web_scanner
description: Run self-built OWASP-ish web scanner (SQLi/XSS/CSRF) against authorized local targets via kxctl.
---

# Kx Attack — Web Scanner

Authorized owned/lab targets only. No ZAP API.

## Command

```bash
kxctl attack run web_scanner --authorized-scope lab --mode simulate --url http://127.0.0.1:8080/
kxctl attack run web_scanner --authorized-scope owned --mode execute --url http://127.0.0.1:8080/?q=test&id=1
```

## Output

Findings with severities + crawled links.

## Forbidden

- Scanning public internet hosts without engagement allow-list
---
