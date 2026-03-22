# Security Considerations for Sandboxed Claude Code

## Credential handling

The host runs a MITM proxy that intercepts outbound HTTPS requests and injects `Authorization` headers for recognised providers (Anthropic, GitHub, OpenAI, Google). The actual API keys are never stored inside the VM.

**Residual risk**: A compromised Claude session could use the *injected* credentials for unintended API calls within the sandbox's allowed network destinations. The keys themselves cannot be read or exfiltrated, but the proxy will still inject them into matching requests.

## Prompt injection

Sandboxing limits the **blast radius** but does not prevent prompt injection:
- A cloned untrusted repo may contain `CLAUDE.md`, `AGENTS.md`, or hidden instructions in code comments
- These could instruct Claude to write malicious code that *looks* correct
- They could instruct Claude to exfiltrate data to allowed network destinations
- Sandboxing ensures that even a fully compromised Claude session cannot escape to the host filesystem or network beyond the allowlist

**Guidance**: Only run `--dangerously-skip-permissions` with **trusted repositories**. For untrusted code, review the repo contents before launching the sandbox.

## Docker-in-Docker

Each sandbox has its own private Docker daemon. The host Docker daemon, containers, and images are never visible to the sandbox. Never mount `/var/run/docker.sock` — Docker Sandboxes avoid this entirely.

## Workspace mutability

The sandbox gives Claude full read-write access to the mounted workspace:
- `rm -rf` inside the workspace **will delete files on the host** (bidirectional sync)
- Claude can overwrite, corrupt, or modify any file in the project
- The sandbox prevents access to the broader host filesystem but not to the project itself

**Mitigation**: Use git. Ensure your work is committed before launching a sandbox session. If Claude goes off the rails, `git checkout .` restores your files.

## Network isolation is not optional

Without network isolation, a compromised Claude session could:
- Exfiltrate SSH keys, environment variables, or source code
- Download and execute arbitrary code
- Communicate with command-and-control servers

**Both filesystem AND network isolation are required.** Anthropic's own documentation emphasises this point repeatedly. Use `docker sandbox network proxy` to configure deny-by-default policies.

## Domain fronting caveat

Even with domain allowlists, **domain fronting** on CDNs could theoretically bypass network filtering. An attacker could route traffic through an allowed CDN domain to reach an arbitrary backend. This is an accepted residual risk — mitigating it would require deep packet inspection beyond what the Docker proxy provides.

## `--dangerously-skip-permissions` vs `--permission-mode bypassPermissions`

| Flag | Behaviour |
|------|-----------|
| `--dangerously-skip-permissions` | Bypasses **all** permission checks. No restrictions whatsoever. |
| `--permission-mode bypassPermissions` | Skips permission prompts but still protects `.git`, `.claude`, `.vscode`, and `.idea` directories from writes. |

For most sandbox use cases, `bypassPermissions` is sufficient and safer — it prevents Claude from accidentally corrupting its own configuration or git history. Use `--dangerously-skip-permissions` only when you specifically need Claude to modify these directories.
