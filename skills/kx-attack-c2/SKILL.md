---
name: kx-attack-c2
description: Manage lab C2 listeners/sessions (echo only). No implants, shellcode, or AMSI bypass.
---

# Kx Attack — C2 (Listener Only)

Authorized lab use only.

## Commands

```bash
kxctl attack run c2 --authorized-scope lab --mode simulate --action status
kxctl attack run c2 --authorized-scope lab --mode execute --action start_listener --host 127.0.0.1 --port 4455
kxctl attack run c2 --authorized-scope lab --mode execute --action register_session --param session_id=lab1
```

## Hard exclusions

- No PE/DLL/shellcode generation
- No AMSI/ETW bypass
- Execute listeners bind to loopback only
---
