---
name: kx-attack-ip_rotation
description: Rotate source IPs through a proxy chain to mask origin during authorized red team operations.
---

# Kx Attack — IP Rotation (KxRotate)

Proxy-chain IP rotation for authorized lab / engagement targets.  
No implants, no persistent tunnels — traffic routing and IP masking verification only.

## Commands

```bash
# Check current external IP
kxctl attack run ip_rotation --authorized-scope lab --mode simulate --action check_ip

# Probe proxy pool reachability
kxctl attack run ip_rotation --authorized-scope lab --mode simulate --action probe

# Rotate through 3 proxies and verify IP masking
kxctl attack run ip_rotation --authorized-scope lab --mode simulate --action rotate --param rotate_count=3

# Execute against custom proxy list (owned engagement)
kxctl attack run ip_rotation --authorized-scope owned --mode execute --action rotate \
  --param proxy_list=http://10.0.1.5:8080,socks5://10.0.1.6:1080 \
  --param rotate_count=2 \
  --param check_ip=true

# Probe custom proxy pool
kxctl attack run ip_rotation --authorized-scope engagement --mode execute --action probe \
  --param proxy_list=http://proxy1.lab:3128,socks5://proxy2.lab:1080
```

## Parameters

| Param | Default | Description |
|---|---|---|
| `action` | `status` | `status` \| `check_ip` \| `probe` \| `rotate` |
| `proxy_list` | — | Comma-separated `proto://addr:port` entries |
| `rotate_count` | `3` | Hops per rotation sequence (max 10) |
| `check_ip` | `true` | Verify origin IP masking after rotation |

## Hard exclusions

- Execute listeners / proxies must be user-supplied (no built-in exit nodes)
- No Tor integration, no clearnet anonymisation service enumeration
- `simulate` mode uses RFC 5737 / 3849 documentation IPs only
---
