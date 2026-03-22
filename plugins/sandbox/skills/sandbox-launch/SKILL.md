---
name: sandbox-launch
description: >
  Launch Claude Code in an isolated Docker sandbox with --dangerously-skip-permissions enabled
  safely. Use this skill when the user wants to run Claude Code in a sandbox, container, Docker
  environment, or isolated mode with unrestricted permissions. Triggers on: "run in docker",
  "skip permissions safely", "isolated mode", "containerise claude", "dangerously-skip-permissions",
  "run unattended", "autonomous mode", "headless claude", "docker sandbox", "launch sandbox",
  "run claude in a container". Do NOT trigger for the built-in /sandbox command — this skill is
  for Docker-based full VM isolation, not the native OS-level sandbox.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
version: "0.1.0"
metadata:
  openclaw:
    category: "dev-tools"
    requires:
      bins: ["docker"]
---

# Launch Claude Code in a Docker Sandbox

Set up and launch Claude Code in an isolated Docker environment where `--dangerously-skip-permissions`
can be used safely. The sandbox provides filesystem and network isolation so Claude can operate
autonomously without risking your host system.

Two approaches are supported:
- **Docker Desktop Sandboxes** (recommended) — microVM-based isolation with its own kernel
- **Devcontainer** (fallback) — Docker container with iptables firewall

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

## Phase 2 — Choose strategy

Based on the detection results, recommend one of three strategies:

| Condition | Strategy |
|-----------|----------|
| `sandbox_available=true` | **Strategy A**: Docker Sandboxes (recommended) |
| `docker_running=true` but `sandbox_available=false` | **Strategy B**: Devcontainer |
| `docker_installed=false` | **Strategy C**: Installation guidance |

Present the recommended strategy and ask the user to confirm before proceeding.

If the user has a preference (e.g., they specifically asked for a devcontainer), follow their preference regardless of what is available.

## Phase 3 — Execute

### Strategy A: Docker Sandboxes

This is the strongest isolation option. Docker Desktop Sandboxes run in dedicated microVMs with
their own Linux kernel. `--dangerously-skip-permissions` is enabled by default.

**Pre-installed tools**: Claude Code, Git, GitHub CLI (`gh`), Node.js, Python 3, Go, ripgrep,
jq, and a private Docker daemon. The `agent` user has sudo access for installing additional
packages.

**Step 1 — Check for existing sandboxes**

```bash
docker sandbox ls
```

If a sandbox already exists for this directory, ask whether to reuse it or remove and recreate.
Docker enforces one sandbox per directory.

**Step 2 — Verify credentials**

If `api_key_set=false`, warn the user:
- `ANTHROPIC_API_KEY` must be set as a host environment variable (in `~/.bashrc` or `~/.zshrc`)
- Docker Desktop must be restarted after setting it (the daemon reads env vars at startup)
- The key is injected via a proxy and never stored inside the sandbox VM

If `github_token_set=false`, mention that `GITHUB_TOKEN` or `GH_TOKEN` should be set for
`gh` CLI and `git push` to work inside the sandbox. Same proxy injection mechanism.

**Step 3 — Launch**

```bash
docker sandbox run claude "$(pwd)"
```

This launches Claude Code in a microVM with bidirectional file sync. Files appear at the same
absolute path inside the sandbox.

**Step 4 — Configure network (optional)**

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

**Step 5 — Summary**

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

### Strategy B: Devcontainer

Use this when Docker is available but `docker sandbox` is not (Docker Desktop < 4.58 or Docker
Engine only). This generates a `.devcontainer/` directory in the user's project.

**Step 1 — Detect project domains**

Use Glob to check which package manager files exist in the project. Read
`${CLAUDE_SKILL_DIR}/references/network-allowlist.md` for the full domain mapping table.

Build a list of domains to allow based on detected package managers from the `package_managers`
field in the detection output.

**Step 2 — Ask about persistence**

Ask the user whether to commit the `.devcontainer/` directory to the repo (useful for teams)
or generate it as a local-only config (add to `.gitignore`).

**Step 3 — Write the devcontainer files**

Read the three asset templates from `${CLAUDE_SKILL_DIR}/assets/` and write them to the project:

1. Read `${CLAUDE_SKILL_DIR}/assets/Dockerfile` → write to `.devcontainer/Dockerfile`
2. Read `${CLAUDE_SKILL_DIR}/assets/devcontainer.json` → write to `.devcontainer/devcontainer.json`
3. Read `${CLAUDE_SKILL_DIR}/assets/init-firewall.py` → write to `.devcontainer/init-firewall.py`

Before writing `init-firewall.py`, customise the `project_domains` list with the domains
detected in Step 1. Replace the placeholder comment with actual domain entries. If GitHub access
is needed, uncomment the GitHub IPs block.

Make the firewall script executable:
```bash
chmod +x .devcontainer/init-firewall.py
```

**Step 4 — Security warnings**

Read `${CLAUDE_SKILL_DIR}/references/security-considerations.md` and present the key warnings:

- The devcontainer bind-mounts `~/.claude` — credentials are directly accessible inside the
  container (unlike Docker Sandboxes which use proxy injection)
- Claude can modify/delete any file in the mounted workspace
- Ensure your work is committed before launching
- Only use with trusted repositories

**Step 5 — Launch instructions**

Provide instructions based on the user's setup:

- **VS Code**: "Reopen in Container" via the Remote-Containers extension
- **CLI**: `devcontainer up --workspace-folder .` then `devcontainer exec --workspace-folder . claude --dangerously-skip-permissions`
- **Manual**: `docker build -t claude-sandbox .devcontainer/` then `docker run --cap-add=NET_ADMIN --cap-add=NET_RAW -v "$(pwd):/workspace" -v "$HOME/.claude:/home/node/.claude" -it claude-sandbox`

Inside the container, start Claude with:
```bash
claude --dangerously-skip-permissions
```

### Strategy C: No Docker

If Docker is not installed:

1. Recommend installing Docker Desktop (available for macOS, Windows, and Linux)
2. Mention that Docker Desktop 4.58+ includes Docker Sandboxes, the strongest isolation option
3. Note the native `/sandbox` command as a lighter alternative — it uses OS-level sandboxing
   (Seatbelt on macOS, bubblewrap on Linux) but does not fully eliminate permission prompts
4. Offer to come back and set up the sandbox once Docker Desktop is installed

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
