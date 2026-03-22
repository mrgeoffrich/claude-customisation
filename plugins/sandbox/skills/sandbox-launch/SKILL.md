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

Set up and launch Claude Code in a Docker Desktop Sandbox — a microVM with its own Linux kernel.
The sandbox provides filesystem and network isolation so Claude can operate autonomously without
risking your host system. A post-launch setup script configures the sandbox with:
- A `yolo` alias that runs `claude --dangerously-skip-permissions`
- `bypassPermissions` mode in Claude Code settings
- Automatic `cd` to the project directory on shell entry
- Starship prompt (if the host has `~/.config/starship.toml`)

Requires Docker Desktop 4.58+.

## Phase 1 — Detect environment

Run the detection script to determine what Docker capabilities are available:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/detect-environment.py"
```

Parse the key=value output. Present the findings to the user in a concise summary:
- OS and Docker version
- Whether Docker Sandboxes are available (Docker Desktop 4.58+)
- Whether GitHub token is configured
- Detected package managers (for network allowlist)
- Whether colored `ls` output is configured on the host
- Any existing sandboxes for this project directory

If `sandbox_available=false`, tell the user Docker Desktop 4.58+ is required and recommend
installing or upgrading it. Mention the native `/sandbox` command as a lighter alternative
that uses OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux) but does not fully
eliminate permission prompts. Do not proceed further without Docker Sandboxes.

## Phase 2 — Confirm

Present what the sandbox will do and ask the user to confirm before proceeding:
- A microVM will be created with its own kernel and private Docker daemon
- Files sync bidirectionally at the same absolute path
- Credentials (Claude account, GitHub token) are injected via proxy (never stored in the VM)
- A setup script will configure the sandbox with:
  - `yolo` alias → `claude --dangerously-skip-permissions`
  - `bypassPermissions` mode in Claude Code settings (suppresses permission prompts)
  - Auto-`cd` to the project directory when shelling in
  - Starship prompt with the host's config (if `~/.config/starship.toml` exists)

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

Claude account credentials are automatically proxied into the sandbox by Docker Desktop —
no `ANTHROPIC_API_KEY` is required.

If `github_token_set=false`, warn the user that `GH_TOKEN` (or `GITHUB_TOKEN`) must be set
for `gh` CLI and `git push` to work inside the sandbox.

If `github_token_in_profile=false` but `github_token_set=true`, warn the user that the
token is in their current session but **not** in their shell profile — the Docker Desktop
daemon won't pick it up. They need to add it to `~/.zshrc` or `~/.bashrc`.

Important details for GitHub token setup:
- The token must be exported in the shell profile (`~/.zshrc` or `~/.bashrc`), not just the
  current session — the Docker Desktop daemon reads env vars at startup, not from the
  active terminal
- Docker Desktop must be **restarted** after adding the token (quit fully and relaunch)
- If a sandbox was already created before the token was set, it must be removed and
  recreated (`docker sandbox rm` then `docker sandbox run`) for the credential proxy to
  pick it up
- The token is injected via proxy and never stored inside the sandbox VM

### Step 3 — Launch

```bash
docker sandbox run claude "$(pwd)"
```

This launches Claude Code in a microVM with bidirectional file sync. Files appear at the same
absolute path inside the sandbox.

### Step 3.5 — Run setup script

After the sandbox is created, run the setup script inside it to configure the environment.

**Starship prompt**: Check if `~/.config/starship.toml` exists on the host. If it does, copy
it into the project directory (which is synced into the sandbox) so the setup script can
detect and install Starship:

```bash
cp ~/.config/starship.toml <project_dir>/.starship.toml
```

The staged file is cleaned up automatically after setup. If network isolation is enabled,
ensure `starship.rs` and `*.starship.rs` are in the allowlist before running setup (the
install script downloads from `starship.rs` and the binary from `github.com`).

**Run the setup script** — pass `GH_TOKEN` via `-e` so the script can write it into the
sandbox's shell profile (the Docker credential proxy does not set env vars inside the VM).
If `ls_colors=true` was detected, also pass `SANDBOX_LS_COLORS=1` so the setup script
enables colored `ls` output inside the sandbox:

```bash
docker sandbox exec -e GH_TOKEN="$GH_TOKEN" -e SANDBOX_LS_COLORS="1" <sandbox-name> python3 <project_dir>/plugins/sandbox/skills/sandbox-launch/scripts/setup-sandbox.py <project_dir> <sandbox-name>
```

Only include `-e SANDBOX_LS_COLORS="1"` if `ls_colors=true` in the detection output.

The `setup-sandbox.py` script configures:
1. **Working directory** — appends `cd <project_dir>` to `.bashrc` so `docker sandbox exec`
   sessions land in the project folder, not the workspace root
2. **`yolo` alias** — `alias yolo='claude --dangerously-skip-permissions'` so the user can
   type `yolo` to launch Claude Code with all permissions bypassed
3. **LS colors** — if `SANDBOX_LS_COLORS` is set, adds `alias ls='ls --color=auto'` to
   `.bashrc` so `ls` output matches the host's colored style
4. **Claude Code permissions** — writes `bypassPermissions` mode and
   `skipDangerousModePermissionPrompt: true` to `~/.claude/settings.json` inside the sandbox
5. **Welcome message** — writes `~/.sandbox-info` and adds the welcome script to `.bashrc`
   so `docker sandbox exec` sessions display sandbox name, project dir, and environment controls
6. **Starship prompt** — if `.starship.toml` was staged, installs Starship to `~/.local/bin`,
   copies the config to `~/.config/starship.toml`, adds PATH and `eval "$(starship init bash)"`
   to `.bashrc`, then removes the staged file

The script is idempotent — it checks for markers before appending to `.bashrc` and merges
into existing `settings.json` if present.

### Step 4 — Configure network

Always apply deny-by-default network isolation. Do not ask the user — this is a security default.

Use the detected package managers to build the allowlist. Read
`${CLAUDE_SKILL_DIR}/references/network-allowlist.md` for the domain mapping table.

Always include these infrastructure domains:
```bash
docker sandbox network proxy <sandbox-name> \
  --policy deny \
  --allow-host "api.anthropic.com" \
  --allow-host "statsig.anthropic.com" \
  --allow-host "statsig.com" \
  --allow-host "sentry.io" \
  --allow-host "mcp-proxy.anthropic.com" \
  --allow-host "github.com" \
  --allow-host "*.github.com" \
  --allow-host "*.githubusercontent.com" \
  --allow-host "docker.io" \
  --allow-host "*.docker.io" \
  --allow-host "registry-1.docker.io" \
  --allow-host "auth.docker.io" \
  --allow-host "production.cloudflare.docker.com" \
  --allow-host "*.r2.cloudflarestorage.com"
```

Add Starship download domains if the setup script will install Starship:
```bash
  --allow-host "starship.rs" \
  --allow-host "*.starship.rs"
```

Then add package manager domains based on the detected package managers — refer to
`${CLAUDE_SKILL_DIR}/references/network-allowlist.md` for the domain mapping table.

Ask the user whether the project calls any external APIs and add those domains too.

Additional domains can be added later without recreating the sandbox:
```bash
docker sandbox network proxy <sandbox-name> --allow-host "example.com"
```

For ongoing monitoring, offer to run the interactive network monitor. This polls for blocked
requests every 5 seconds and lets the user allow domains on the fly:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/network-monitor.py <sandbox-name>
```

The monitor shows a numbered list of blocked domains. The user can type a number to allow a
single domain, `a` to allow all, `r` to refresh, or `q` to quit.

### Step 5 — Summary

Tell the user what is now running and how to manage it:

- Files sync bidirectionally — changes inside the sandbox appear on the host
- Credentials are injected via proxy (never stored in the VM)
- The sandbox has its own Docker daemon for building/running containers
- Type `yolo` inside the sandbox to launch Claude with `--dangerously-skip-permissions`
- Shell sessions auto-`cd` to the project directory
- Starship prompt is configured (if the host had `~/.config/starship.toml`)

Key commands:
- `docker sandbox ls` — list sandboxes
- `docker sandbox exec -it <name> bash` — shell into the sandbox
- `docker sandbox stop <name>` — stop (preserves state)
- `docker sandbox rm <name>` — destroy (workspace files preserved on host)
- `docker sandbox network log` — monitor allowed/blocked network traffic

End by showing the user the exact commands to shell in and monitor network traffic:

```
To shell into your sandbox, run:
  docker sandbox exec -it <sandbox-name> bash

To monitor and manage blocked network traffic, run:
  python3 ${CLAUDE_SKILL_DIR}/scripts/network-monitor.py <sandbox-name>
```

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
