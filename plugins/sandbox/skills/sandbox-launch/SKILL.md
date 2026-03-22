---
name: sandbox-launch
description: >
  Launch Claude Code in an isolated Docker sandbox with --dangerously-skip-permissions enabled
  safely. Use this skill when the user wants to run Claude Code in a sandbox, container, Docker
  environment, or isolated mode with unrestricted permissions. Triggers on:
  "skip permissions safely", "isolated mode", "containerise claude", "dangerously-skip-permissions",
  "run unattended", "autonomous mode", "headless claude", "docker sandbox", "launch sandbox". Do NOT trigger for the built-in /sandbox command — this skill is for Docker-based full VM isolation, not the native OS-level sandbox.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
version: "0.1.0"
metadata:
  openclaw:
    category: "dev-tools"
    requires:
      bins: ["docker"]
---

# Launch Claude Code in a Docker Sandbox

Set up and launch Claude Code in a Docker Desktop Sandbox — a microVM with its own Linux kernel
where `--dangerously-skip-permissions` is enabled by default. The sandbox provides filesystem and
network isolation so Claude can operate autonomously without risking your host system.

Requires Docker Desktop 4.58+.

## Phase 1 — Detect environment

Run the detection script to determine what Docker capabilities are available:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/detect-environment.py"
```

Parse the key=value output. Present the findings to the user in a concise summary:
- OS and Docker version
- Whether Docker Sandboxes are available (Docker Desktop 4.58+)
- Whether API keys are configured
- Detected package managers (for network allowlist)
- Any existing sandboxes for this project directory

If `sandbox_available=false`, tell the user Docker Desktop 4.58+ is required and recommend
installing or upgrading it. Mention the native `/sandbox` command as a lighter alternative
that uses OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux) but does not fully
eliminate permission prompts. Do not proceed further without Docker Sandboxes.

## Phase 2 — Confirm

Present what the sandbox will do and ask the user to confirm before proceeding:
- A microVM will be created with its own kernel and private Docker daemon
- `--dangerously-skip-permissions` is enabled by default
- Files sync bidirectionally at the same absolute path
- Credentials are injected via proxy (never stored in the VM)

## Phase 3 — Launch

**Pre-installed tools**: Claude Code, Git, GitHub CLI (`gh`), Node.js, Python 3, Go, ripgrep,
jq, and a private Docker daemon. The `agent` user has sudo access for installing additional
packages.

### Step 1 — Check for existing sandboxes

```bash
docker sandbox ls
```

If a sandbox already exists for this directory, ask whether to reuse it or remove and recreate.
Docker enforces one sandbox per directory.

### Step 2 — Verify credentials

If `api_key_set=false`, warn the user:
- `ANTHROPIC_API_KEY` must be set as a host environment variable (in `~/.bashrc` or `~/.zshrc`)
- Docker Desktop must be restarted after setting it (the daemon reads env vars at startup)
- The key is injected via a proxy and never stored inside the sandbox VM

If `github_token_set=false`, mention that `GITHUB_TOKEN` or `GH_TOKEN` should be set for
`gh` CLI and `git push` to work inside the sandbox. Same proxy injection mechanism.

### Step 3 — Launch

```bash
docker sandbox run claude "$(pwd)"
```

This launches Claude Code in a microVM with bidirectional file sync. Files appear at the same
absolute path inside the sandbox.

### Step 4 — Configure network (optional)

Ask the user if they want strict network isolation (deny-by-default). If yes, use the detected
package managers to build an allowlist. Read `${CLAUDE_SKILL_DIR}/references/network-allowlist.md`
for the domain mapping table.

Example for a Node.js project with GitHub:
```bash
docker sandbox network proxy <sandbox-name> \
  --policy deny \
  --allow-host "api.anthropic.com" \
  --allow-host "statsig.anthropic.com" \
  --allow-host "sentry.io" \
  --allow-host "registry.npmjs.org" \
  --allow-host "*.npmjs.org" \
  --allow-host "github.com" \
  --allow-host "*.github.com" \
  --allow-host "*.githubusercontent.com"
```

Also ask whether the project calls any external APIs and add those domains.

### Step 5 — Summary

Tell the user what is now running and how to manage it:

- The sandbox is running with `--dangerously-skip-permissions` enabled
- Files sync bidirectionally — changes inside the sandbox appear on the host
- Credentials are injected via proxy (never stored in the VM)
- The sandbox has its own Docker daemon for building/running containers

Key commands:
- `docker sandbox ls` — list sandboxes
- `docker sandbox exec -it <name> bash` — shell in alongside Claude
- `docker sandbox stop <name>` — stop (preserves state)
- `docker sandbox rm <name>` — destroy (workspace files preserved on host)
- `docker sandbox network log` — monitor network activity

## Custom templates (advanced)

For users who want reproducible sandbox environments, Docker Sandboxes support custom templates.
This is useful for teams or projects with specific toolchain requirements.

Create a Dockerfile extending the base image:

```dockerfile
FROM docker/sandbox-templates:claude-code

USER root
RUN apt-get update && apt-get install -y <additional-packages>
USER agent
```

Build and use:
```bash
docker build -t my-template:v1 .
docker sandbox run -t my-template:v1 claude ~/my-project
```

Or snapshot a running sandbox after installing everything needed:
```bash
docker sandbox save <sandbox-name> my-template:v1
```
