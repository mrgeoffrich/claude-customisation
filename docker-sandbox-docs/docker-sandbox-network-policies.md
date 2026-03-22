# Docker Sandbox Network Policies

> Source: https://docs.docker.com/ai/sandboxes/network-policies/

The sandbox proxy enforces policies on outbound HTTP/HTTPS traffic. Connections to
external services over other protocols (raw TCP/UDP) are blocked.

## Policy modes

### Allow (default)

Permits most traffic while blocking:

| Range | Description |
|-------|-------------|
| `10.0.0.0/8` | Private network |
| `172.16.0.0/12` | Private network |
| `192.168.0.0/16` | Private network |
| `127.0.0.0/8` | Loopback |
| `::1/128` | IPv6 loopback |
| `169.254.0.0/16` | Link-local |
| `fe80::/10` | IPv6 link-local |
| `fc00::/7` | IPv6 unique local |

Explicitly permitted by default: `*.anthropic.com` and `platform.claude.com:443`.

### Deny

Blocks all traffic except explicitly allowed hosts. This is the mode the sandbox-launch
skill uses for security.

## Domain matching

- `example.com` does **NOT** match subdomains — you need `*.example.com` separately
- Specific patterns override broader ones through a five-level priority hierarchy

## HTTPS handling

**Default:** Man-in-the-middle inspection — TLS terminated and re-encrypted with proxy CA.

**Bypass mode:** Available for certificate-pinned services. Simple TCP tunnel, no
inspection. Configure with `--bypass-host`.

## Configuring policies

```bash
# Set deny-by-default policy
docker sandbox network proxy <sandbox> --policy deny

# Allow specific domains
docker sandbox network proxy <sandbox> --allow-host "api.anthropic.com"
docker sandbox network proxy <sandbox> --allow-host "*.github.com"

# Block specific domains (in allow mode)
docker sandbox network proxy <sandbox> --block-host "evil.com"

# Bypass MITM for certificate-pinned services
docker sandbox network proxy <sandbox> --bypass-host "pinned.example.com"

# CIDR-based rules
docker sandbox network proxy <sandbox> --allow-cidr "10.0.0.0/8"
docker sandbox network proxy <sandbox> --block-cidr "172.16.0.0/12"
```

## Monitoring

```bash
docker sandbox network log                    # aggregated request summaries
docker sandbox network log --json             # JSON output
docker sandbox network log --limit 50         # limit entries
docker sandbox network log -q                 # quiet mode
```

## Persistence

Policies are stored at:
- Per-sandbox: `~/.docker/sandboxes/vm/[name]/proxy-config.json`
- System defaults: `~/.sandboxd/proxy-config.json`

## Adding domains later

Domains can be added without recreating the sandbox:

```bash
docker sandbox network proxy <sandbox-name> --allow-host "example.com"
```
