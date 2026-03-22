# Docker Sandbox Architecture

> Source: https://docs.docker.com/ai/sandboxes/architecture/

## Private Docker daemon

Each sandbox has a complete Docker daemon inside its VM, isolated from the host and other
sandboxes. Agents' Docker commands operate exclusively within their private daemon.

## Hypervisor-level boundaries

| Platform | Hypervisor |
|----------|-----------|
| macOS | `virtualization.framework` |
| Windows | Hyper-V (experimental) |

Each sandbox gets a separate kernel — full isolation between sandbox and host.

## Security protections

- **Process isolation** — separate kernel
- **Filesystem isolation** — workspace directories only
- **Network isolation** — no inter-sandbox communication
- **Docker isolation** — no host daemon access

## File synchronization

Uses file synchronization, **not** volume mounting. Files are copied between host and VM.

- Workspace syncs **bidirectionally** at matching absolute paths
- e.g., `/Users/alice/projects/myapp` on host appears at the same path inside the sandbox
- Path preservation ensures error message paths match and hard-coded config paths work

## Storage

**Persistent** (survives stop/restart):
- Docker images/containers
- System packages
- Agent state/credentials
- Modified workspace files

**Ephemeral** (lost on `docker sandbox rm`):
- The entire VM and contents are deleted
- Multiple sandboxes do not share images or layers

## Network

- Internet access via host connection
- HTTP/HTTPS filtering proxy at `host.docker.internal:3128`
- Credential proxy intercepts outbound requests and injects auth headers
- **Credentials are never stored inside the sandbox VM**
- Sandboxes cannot communicate with each other
- Each VM has its own private network namespace
- Cannot access host's `localhost` services

## Lifecycle

| Command | Effect |
|---------|--------|
| `docker sandbox run` | Initialize VM and start agent |
| `docker sandbox create` | Set up without starting |
| `docker sandbox stop` | Preserves installed packages and Docker images |
| `docker sandbox rm` | Deletes VM and reclaims disk |

## Resource limits

MicroVMs run with **4GB RAM** by default.

> Reference: https://github.com/docker/for-mac/issues/7860
