---
name: sandbox-launch
description: >
  Launch Claude Code in an isolated Docker sandbox with --dangerously-skip-permissions enabled
  safely. Use this skill when the user wants to run Claude Code in a sandbox, container, Docker
  environment, or isolated mode with unrestricted permissions. Triggers on:
  "skip permissions safely", "isolated mode", "containerise claude", "dangerously-skip-permissions",
  "run unattended", "autonomous mode", "headless claude", "docker sandbox", "launch sandbox". Do NOT trigger for the built-in /sandbox command — this skill is for Docker-based full VM isolation, not the native OS-level sandbox.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
version: "0.2.0"
metadata:
  openclaw:
    category: "dev-tools"
    requires:
      bins: ["docker"]
---

# Launch Claude Code in a Docker Sandbox

Set up and launch Claude Code in a Docker Desktop Sandbox — a microVM with its own Linux kernel.
The sandbox provides filesystem and network isolation so Claude can operate autonomously without
risking your host system.

The sandbox uses a pre-built template image (`cc-sandbox:latest`) that bakes in static config:
- `yolo` alias → `claude --dangerously-skip-permissions`
- `bypassPermissions` mode in Claude Code settings
- Colored `ls` output
- Starship prompt binary (pre-installed, no download needed at launch)

A lightweight setup script then applies per-project dynamic config:
- Automatic `cd` to the project directory on shell entry
- GitHub token and OAuth token exports
- Starship config file from the host
- Welcome message with sandbox info

Requires Docker Desktop 4.58+.

Each sandbox is tied to a single project directory — Docker enforces one sandbox per directory,
and network allowlist rules are scoped to that sandbox. If the user works on multiple projects,
they will need a separate sandbox for each one. Mention this upfront so the user understands
the sandbox they are about to create is project-specific.

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
- The template image includes: `yolo` alias, `bypassPermissions`, Starship, colored `ls`
- A setup script will apply project-specific config (working directory, tokens, welcome message)

**Optional — pre-generate an auth token**: Claude Code requires authentication when it first
starts. Inside the headless sandbox VM there is no browser, so the user must manually copy/paste
a login URL. To avoid this, the user can run `claude setup-token` in their terminal **before
confirming** (it requires a TTY and browser, so it cannot be run programmatically). This outputs
a long-lived OAuth token (`sk-ant-oat01-...`) that will be injected into the sandbox during
setup. Each sandbox requires its own unique token. Requires Claude Pro or Max subscription.

Tell the user: if they want seamless auth, run `claude setup-token` now in a separate terminal
and paste the token here. Otherwise they can skip this and authenticate manually inside the
sandbox later (press `c` to copy the login URL when prompted).

## Phase 3 — Launch

**Pre-installed tools** (in the template image): Claude Code, Git, GitHub CLI (`gh`), Node.js,
Python 3, Go, ripgrep, jq, Starship prompt, and a private Docker daemon. The `agent` user has
sudo access for installing additional packages.

### Step 1 — Build template image (if needed)

Run the build script to ensure the `cc-sandbox:latest` template image exists and is up-to-date:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/build-template.py"
```

Parse the key=value output:
- `action=none` — template is up-to-date, proceed
- `action=built` — template was built for the first time
- `action=rebuilt` — template was rebuilt because the base image changed

If the script fails, show the error and stop. The template image is required.

On first run this pulls the base image and builds the template (may take a minute). Subsequent
launches skip this step entirely unless the base image has been updated.

### Step 2 — Check for existing sandboxes

```bash
docker sandbox ls
```

If a sandbox already exists for this directory, ask whether to reuse it or remove and recreate.
Docker enforces one sandbox per directory.

### Step 3 — Verify credentials

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

### Step 4 — Launch sandbox

```bash
docker sandbox run --name "$(basename "$(pwd)")-cc" -t cc-sandbox:latest claude "$(pwd)"
```

The sandbox name uses the pattern `<directory>-cc` (e.g. `my-project-cc`). The `-cc` suffix
identifies it as a Claude Code sandbox without the default `claude-` prefix that Docker adds.

Files appear at the same absolute path inside the sandbox via bidirectional sync.

### Step 5 — Run setup script

After the sandbox is created, run the lightweight setup script for per-project config.

**Starship config**: Check if `~/.config/starship.toml` exists on the host. If it does, copy
it into the project directory (which is synced into the sandbox) so the setup script can
install it:

```bash
cp ~/.config/starship.toml <project_dir>/.starship.toml
```

The staged file is cleaned up automatically after setup.

**Stage the setup script** — copy it into the project directory (which is synced into the
sandbox) so it's accessible inside the VM. `${CLAUDE_SKILL_DIR}` resolves to a host path
outside the synced directory, so the script must be staged like `.starship.toml`:

```bash
cp ${CLAUDE_SKILL_DIR}/scripts/setup-sandbox.py <project_dir>/.setup-sandbox.py
```

**Run the setup script** — pass `GH_TOKEN` via `-e` so the script can write it into the
sandbox's shell profile. If the user provided an OAuth token during Phase 2, pass it via
`CLAUDE_CODE_OAUTH_TOKEN`:

```bash
docker sandbox exec -e GH_TOKEN="$GH_TOKEN" -e CLAUDE_CODE_OAUTH_TOKEN="<token>" <sandbox-name> python3 <project_dir>/.setup-sandbox.py <project_dir> <sandbox-name>
```

Only include `-e CLAUDE_CODE_OAUTH_TOKEN="<token>"` if the user provided a token during Phase 2.

**Clean up** — remove the staged script from the project directory after setup completes:

```bash
rm -f <project_dir>/.setup-sandbox.py
```

The `setup-sandbox.py` script configures:
1. **Working directory** — appends `cd <project_dir>` to `.bashrc` so `docker sandbox exec`
   sessions land in the project folder, not the workspace root
2. **GitHub token** — exports `GH_TOKEN` in `.bashrc` if provided
3. **Auth token** — if `CLAUDE_CODE_OAUTH_TOKEN` is set, exports it in `.bashrc` so Claude
   Code authenticates without opening a browser (each sandbox needs its own unique token)
4. **Welcome message** — writes `~/.sandbox-info` and adds the welcome script to `.bashrc`
   so `docker sandbox exec` sessions display sandbox name, project dir, and environment controls
5. **Terminal title** — sets the terminal title to `🔒 <sandbox-name>` so sandbox sessions
   are visually distinct from host terminals
6. **Starship config** — if `.starship.toml` was staged, copies it to `~/.config/starship.toml`
   (the binary is already installed in the template image)

The script is idempotent — it checks for markers before appending to `.bashrc`.

### Step 6 — Configure network

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

### Step 7 — Summary

Tell the user what is now running and how to manage it:

- Files sync bidirectionally — changes inside the sandbox appear on the host
- Credentials are injected via proxy (never stored in the VM)
- If an OAuth token was provided, authentication is pre-configured (no browser needed inside the sandbox)
- The sandbox has its own Docker daemon for building/running containers
- Type `yolo` inside the sandbox to launch Claude with `--dangerously-skip-permissions`
- Shell sessions auto-`cd` to the project directory
- Terminal title shows `🔒 <sandbox-name>` to distinguish sandbox from host terminals
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

For users who want to further customize the template, they can extend `cc-sandbox:latest`:

```dockerfile
FROM cc-sandbox:latest

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
