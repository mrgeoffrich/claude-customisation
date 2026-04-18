---
name: tailscale
description: >
  Reference guide and assistant for the Tailscale CLI tool. Use this skill whenever the user asks
  about Tailscale commands, wants to connect/disconnect from Tailscale, set up exit nodes, share
  files, expose local services, configure SSH, manage tailnet settings, troubleshoot connectivity,
  or do anything with the `tailscale` CLI. Trigger for questions like "how do I use tailscale",
  "tailscale up options", "how to serve a local port", "set up exit node", "tailscale file transfer",
  or any mention of tailscale commands, flags, or network operations.
---

# Tailscale CLI Reference

Tailscale v1.96+ — the easiest, most secure way to use WireGuard.

**Global flag:** `--socket <path>` — path to tailscaled socket (rarely needed)

---

## Connection Management

### `tailscale up` — Connect to Tailscale

Brings the tailnet connection online, triggering auth if needed. With no flags, simply reconnects
without changing settings. If flags are provided, they must represent the *complete* desired state
(use `--reset` to reset unspecified flags to defaults).

Key flags:
- `--auth-key <key>` — headless auth; prefix with `file:` to read from a file
- `--hostname <name>` — override the OS-provided hostname
- `--advertise-routes <cidrs>` — subnet routes to advertise (comma-separated, e.g. `10.0.0.0/8`)
- `--advertise-exit-node` — offer this machine as an exit node
- `--exit-node <ip|name|auto:any>` — route internet traffic through this exit node
- `--exit-node-allow-lan-access` — allow direct LAN access while using an exit node
- `--accept-routes` / `--accept-routes=false` — accept routes from other nodes (default: true)
- `--accept-dns` / `--accept-dns=false` — use tailnet DNS (default: true)
- `--shields-up` — block all incoming connections
- `--ssh` — enable Tailscale SSH server (respects admin policy)
- `--advertise-tags <tags>` — ACL tags, comma-separated, each starts with `tag:`
- `--reset` — reset unspecified settings to defaults
- `--force-reauth` — force re-authentication (avoid over SSH/RDP)
- `--login-server <url>` — use a custom control server (default: https://controlplane.tailscale.com)
- `--timeout <duration>` — max wait for daemon to reach Running state (0 = block forever)
- `--qr` / `--qr-format <auto|ascii|large|small>` — show QR code for login URL
- `--unattended` — keep running after GUI user logs out (Windows only)
- Workload identity flags: `--client-id`, `--client-secret`, `--audience`, `--id-token`

### `tailscale down` — Disconnect

Disconnects from Tailscale without logging out.

- `--accept-risk <type>` — skip confirmation for `lose-ssh`, `mac-app-connector`, or `all`
- `--reason <text>` — reason for disconnect (if required by policy)

### `tailscale login` — Log In

Logs the machine into a Tailscale account. Accepts the same network/auth flags as `up` plus:
- `--nickname <name>` — short label for this account
- `--qr` — show QR code

### `tailscale logout` — Log Out

Disconnects and expires the current node key (requires re-auth on next `up`).

### `tailscale switch` — Switch Accounts

Switch between multiple Tailscale accounts on the same machine.

---

## Settings & Configuration

### `tailscale set` — Change Individual Preferences

Unlike `up`, only specified flags are changed — safe to use without the full desired state.

- `--hostname <name>`
- `--accept-dns`, `--accept-routes`
- `--advertise-routes <cidrs>`, `--advertise-exit-node`, `--advertise-connector`
- `--exit-node <ip|name>`, `--exit-node-allow-lan-access`
- `--shields-up`, `--ssh`
- `--auto-update` — enable automatic updates
- `--update-check` — notify about available updates
- `--webclient` — expose web UI at port 5252 over Tailscale
- `--nickname <name>` — label for this account
- `--unattended` (Windows only)
- `--relay-server-port <port>` — UDP port for relay server (0 = random, empty = disable)
- `--relay-server-static-endpoints <ip:port,...>` — static relay endpoints
- `--report-posture` — allow management plane to collect device posture info

### `tailscale configure` — Host Feature Configuration

Enables deeper OS-level Tailscale features (e.g., DNS, system extensions). Run `tailscale configure --help` for platform-specific subcommands.

### `tailscale syspolicy` — MDM / System Policy Diagnostics

Diagnoses MDM and system policy configuration. Useful for managed corporate deployments.

---

## Status & Inspection

### `tailscale status` — Show Tailnet State

- `--active` — show only peers with active sessions
- `--json` — JSON output (schema may change between releases)
- `--peers=false` — hide peers, show only self
- `--self=false` — hide self
- `--web` — serve an HTML status page
- `--listen <addr>` — address for web mode (default `127.0.0.1:8384`)

### `tailscale ip` — Show Tailscale IPs

```
tailscale ip                    # show all IPs for this machine
tailscale ip <peer>             # show IPs for a peer (hostname or IP)
tailscale ip -4                 # IPv4 only
tailscale ip -6                 # IPv6 only
tailscale ip -1                 # first IP only
```

### `tailscale whois` — Identify a Tailscale IP

```
tailscale whois 100.x.y.z       # show machine + user for an IP
tailscale whois --json 100.x.y.z
tailscale whois --proto tcp 100.x.y.z:443
```

### `tailscale netcheck` — Network Condition Analysis

Analyzes local network conditions, NAT type, DERP latency, and UDP reachability.

- `--every <duration>` — repeat at interval
- `--format <json|json-line>` — machine-readable output
- `--verbose` — verbose logs
- `--bind-address <ip>` / `--bind-port <port>` — control the probe source

### `tailscale metrics` — Show Metrics

Prints Tailscale daemon metrics (Prometheus-compatible format).

---

## Connectivity Tools

### `tailscale ping` — Tailscale-layer Ping

Pings a peer through Tailscale and reports routing (DERP relay vs direct). Stops after first
direct path by default.

```
tailscale ping <hostname-or-IP>
```

Flags:
- `--c <n>` — max pings (default 10, 0 = infinite)
- `--until-direct=false` — keep pinging even after direct path found
- `--timeout <duration>` — per-ping timeout (default 5s)
- `--icmp` — ICMP-level ping through WireGuard
- `--tsmp` — TSMP-level ping (bypasses both OS stacks)
- `--peerapi` — probe the peer's peerapi HTTP server
- `--size <bytes>` — disco ping payload size
- `--verbose`

### `tailscale nc` — Netcat over Tailscale

Connects stdin/stdout to a TCP port on a peer. Useful for scripting or testing connectivity.

```
tailscale nc <hostname-or-IP> <port>
```

### `tailscale ssh` — SSH via Tailscale

Wrapper around system `ssh` that resolves hostnames via MagicDNS (even if `--accept-dns=false`)
and validates SSH host keys via the coordination server.

```
tailscale ssh user@hostname
tailscale ssh hostname
```

---

## Serving & Exposing Services

### `tailscale serve` — Expose a Service Within Your Tailnet

Shares a local service securely to other nodes on your tailnet only (not the public internet).

```
tailscale serve 3000                          # serve localhost:3000 over HTTPS on tailnet
tailscale serve --bg 3000                     # run in background
tailscale serve https+insecure://localhost:8443  # self-signed cert upstream
tailscale serve unix:/tmp/myservice.sock      # Unix socket (Linux/macOS)
tailscale serve status                        # view current config
tailscale serve reset                         # clear all serve config
```

Flags:
- `--http <port>` / `--https <port>` — force HTTP or HTTPS listener
- `--tcp <port>` / `--tls-terminated-tcp <port>` — raw TCP forwarding
- `--set-path <path>` — mount under a URL path prefix
- `--bg` — run as background process
- `--service <name>` — serve for a named service with its own virtual IP
- `--yes` — skip interactive prompts
- `--proxy-protocol <1|2>` — PROXY protocol version for TCP

Subcommands: `status`, `reset`, `drain`, `clear`, `advertise`, `get-config`, `set-config`

### `tailscale funnel` — Expose a Service to the Public Internet

Same interface as `serve` but routes traffic from the public internet to your local service.
Requires Funnel to be enabled in your tailnet admin panel.

```
tailscale funnel 3000                         # expose localhost:3000 publicly
tailscale funnel --bg 3000                    # background mode
tailscale funnel status
tailscale funnel reset
```

Supports the same `--tcp`, `--tls-terminated-tcp`, `--set-path`, `--bg`, `--yes`, `--proxy-protocol` flags as `serve`.

**Key difference:** `serve` = tailnet only. `funnel` = public internet.

---

## File Transfer (Taildrop)

### `tailscale file cp` — Send Files

```
tailscale file cp <file...> <target>:         # send to peer (note trailing colon)
tailscale file cp report.pdf laptop:          # send to "laptop"
tailscale file cp - laptop: --name data.txt  # send stdin with a given filename
tailscale file cp --targets                   # list available targets
```

Flags: `--name <filename>`, `--targets`, `--verbose`

### `tailscale file get` — Receive Files

Moves files out of the Tailscale file inbox into a local directory.

```
tailscale file get ~/Downloads
tailscale file get --wait ~/Downloads         # wait for a file if inbox is empty
tailscale file get --loop ~/Downloads         # continuously receive as files arrive
```

Conflict resolution: `--conflict skip` (default), `overwrite`, or `rename`

---

## Exit Nodes

### `tailscale exit-node list` — List Exit Nodes

```
tailscale exit-node list
tailscale exit-node list --filter US          # filter by country
```

### `tailscale exit-node suggest` — Get Best Exit Node

Suggests the optimal exit node based on latency and availability.

```
tailscale exit-node suggest
```

To use an exit node: `tailscale set --exit-node <ip|name|auto:any>`
To stop using one: `tailscale set --exit-node ""`

---

## DNS

### `tailscale dns status` — DNS Forwarder Status

```
tailscale dns status           # human-readable
tailscale dns status --json    # JSON
tailscale dns status --all     # include all resolvers
```

### `tailscale dns query` — Perform a DNS Query

```
tailscale dns query example.com
tailscale dns query example.com AAAA
tailscale dns query --json example.com
```

---

## Taildrive (Directory Sharing)

Requires the `drive:share` and `drive:access` node attributes set in the admin panel.

```
tailscale drive share docs /Users/me/Documents   # share a directory
tailscale drive rename docs newdocs               # rename a share
tailscale drive unshare newdocs                   # remove a share
tailscale drive list                              # list current shares
```

Shares are accessible via WebDAV at `http://100.100.100.100:8080/<tailnet>/<machine>/<share>`.

Permissions are controlled via ACL grants in the admin panel.

---

## TLS Certificates

### `tailscale cert` — Get TLS Certs for Your Node

```
tailscale cert my-node.tailnet-name.ts.net
tailscale cert --cert-file out.crt --key-file out.key my-node.ts.net
tailscale cert --cert-file - my-node.ts.net    # output to stdout
tailscale cert --serve-demo my-node.ts.net     # demo HTTPS server on :443
```

- `--min-validity <duration>` — ensure cert is valid for at least this long

---

## Tailnet Lock

Manages node signing keys to prevent unauthorized nodes from joining.

```
tailscale lock init              # initialize tailnet lock
tailscale lock status            # show lock state
tailscale lock add <key>         # add a trusted signing key
tailscale lock remove <key>      # remove a key
tailscale lock sign <node>       # sign a node or pre-approved auth key
tailscale lock disable <secret>  # disable tailnet lock using a disablement secret
tailscale lock log               # list changes to tailnet lock
tailscale lock local-disable     # disable lock for this node only
tailscale lock revoke-keys       # revoke compromised keys
tailscale lock disablement-kdf   # compute disablement value from secret (advanced)
```

---

## Updates

### `tailscale update`

```
tailscale update                        # update to latest stable
tailscale update --track unstable       # switch to dev/unstable track
tailscale update --version 1.95.0       # pin to a specific version
tailscale update --dry-run              # preview what would change
tailscale update --yes                  # skip interactive prompts
```

Tracks: `stable` (default), `release-candidate`, `unstable`

---

## Other Commands

| Command | Usage |
|---|---|
| `tailscale version` | Print version info |
| `tailscale bugreport` | Get a shareable ID for support tickets |
| `tailscale licenses` | Print open source license info |
| `tailscale web` | Run a local web UI for controlling Tailscale |
| `tailscale completion <bash\|zsh\|fish>` | Generate shell tab-completion scripts |
| `tailscale wait` | Wait until Tailscale interface/IPs are ready |
| `tailscale appc-routes` | Print current app connector routes |

---

## Common Workflows

**Set up this machine as an exit node:**
```
tailscale set --advertise-exit-node
# then approve in the admin panel
```

**Use an exit node:**
```
tailscale exit-node list
tailscale set --exit-node <name-or-ip>
tailscale set --exit-node ""  # stop using exit node
```

**Expose a local dev server to your tailnet:**
```
tailscale serve 3000         # https on port 443 of your tailscale hostname
tailscale serve --bg 3000    # background mode
tailscale serve status
```

**Send a file to another machine:**
```
tailscale file cp myfile.txt othermachine:
```

**SSH to a tailnet machine:**
```
tailscale ssh hostname
# or just: ssh hostname  (if Tailscale SSH is configured)
```

**Advertise a subnet route:**
```
tailscale set --advertise-routes 192.168.1.0/24
# then approve in the admin panel, and peers must run:
tailscale set --accept-routes
```

**Headless machine setup with auth key:**
```
tailscale up --auth-key tskey-auth-xxxxx --hostname myserver --ssh
```

**Check why connectivity isn't working:**
```
tailscale netcheck
tailscale ping othermachine
tailscale status
```
