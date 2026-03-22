# Security Considerations for Sandboxed Claude Code

## Docker Sandboxes vs Devcontainers

| Property | Docker Sandboxes (Strategy A) | Devcontainer (Strategy B) |
|----------|-------------------------------|---------------------------|
| **Isolation boundary** | Hypervisor (microVM with own kernel) | Linux namespaces (container) |
| **Credential handling** | MITM proxy injects headers; keys never stored in VM | Bind-mount `~/.claude`; keys visible inside container |
| **File access** | Bidirectional sync (copy-based) | Bind mount (direct access) |
| **Network isolation** | Configurable via `docker sandbox network proxy` | iptables firewall in container |
| **Docker-in-Docker** | Private daemon (no host access) | Not available (unless host socket mounted — don't do this) |
| **Workspace safety** | Claude can modify/delete files in mounted workspace | Same — bind mount is read-write |

**Recommendation**: Docker Sandboxes (Strategy A) is strictly stronger. Use devcontainers only when Docker Desktop 4.58+ is unavailable.

## Credential exposure

### Docker Sandboxes (proxy-based injection)
The host runs a MITM proxy that intercepts outbound HTTPS requests and injects `Authorization` headers for recognised providers (Anthropic, GitHub, OpenAI, Google). The actual API keys are never stored inside the VM.

**Residual risk**: A compromised Claude session could use the *injected* credentials for unintended API calls within the sandbox's allowed network destinations. The keys themselves cannot be read or exfiltrated, but the proxy will still inject them into matching requests.

### Devcontainers (bind-mounted credentials)
The `~/.claude` directory is bind-mounted into the container. This means:
- `ANTHROPIC_API_KEY` or OAuth tokens are directly readable inside the container
- If network isolation fails or is misconfigured, credentials could be exfiltrated
- A malicious CLAUDE.md or AGENTS.md could instruct Claude to `cat` credential files

**Mitigation**: The iptables firewall blocks all outbound traffic except allowlisted domains. This limits exfiltration targets but does not eliminate the risk if an allowed domain is compromised or domain fronting is used.

## Prompt injection

Sandboxing limits the **blast radius** but does not prevent prompt injection:
- A cloned untrusted repo may contain `CLAUDE.md`, `AGENTS.md`, or hidden instructions in code comments
- These could instruct Claude to write malicious code that *looks* correct
- They could instruct Claude to exfiltrate data to allowed network destinations
- Sandboxing ensures that even a fully compromised Claude session cannot escape to the host filesystem or network beyond the allowlist

**Guidance**: Only run `--dangerously-skip-permissions` with **trusted repositories**. For untrusted code, review the repo contents before launching the sandbox.

## Docker socket

**Never mount `/var/run/docker.sock` into a devcontainer.** Access to the Docker socket is effectively root access to the host system. Docker Sandboxes avoid this entirely by providing a private Docker daemon inside the microVM.

The devcontainer assets provided by this skill intentionally do not include a Docker socket mount.

## Workspace mutability

Both Docker Sandboxes and devcontainers give Claude full read-write access to the mounted workspace:
- `rm -rf` inside the workspace **will delete files on the host**
- Claude can overwrite, corrupt, or modify any file in the project
- The sandbox prevents access to the broader host filesystem but not to the project itself

**Mitigation**: Use git. Ensure your work is committed before launching a sandbox session. If Claude goes off the rails, `git checkout .` restores your files.

## Network isolation is not optional

Without network isolation, a compromised Claude session could:
- Exfiltrate SSH keys, environment variables, or source code
- Download and execute arbitrary code
- Communicate with command-and-control servers

**Both filesystem AND network isolation are required.** Anthropic's own documentation emphasises this point repeatedly.

The devcontainer path (Strategy B) should refuse to launch without verifying the firewall works (the `init-firewall.sh` script includes a verification step that aborts if `example.com` is reachable).

## Domain fronting caveat

Even with domain allowlists, **domain fronting** on CDNs could theoretically bypass network filtering. An attacker could route traffic through an allowed CDN domain to reach an arbitrary backend. This is an accepted residual risk — mitigating it would require deep packet inspection beyond what iptables or the Docker proxy provides.

## `--dangerously-skip-permissions` vs `--permission-mode bypassPermissions`

| Flag | Behaviour |
|------|-----------|
| `--dangerously-skip-permissions` | Bypasses **all** permission checks. No restrictions whatsoever. |
| `--permission-mode bypassPermissions` | Skips permission prompts but still protects `.git`, `.claude`, `.vscode`, and `.idea` directories from writes. |

For most sandbox use cases, `bypassPermissions` is sufficient and safer — it prevents Claude from accidentally corrupting its own configuration or git history. Use `--dangerously-skip-permissions` only when you specifically need Claude to modify these directories.
