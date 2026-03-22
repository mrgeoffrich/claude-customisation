# Docker Sandbox CLI Reference

> Source: https://docs.docker.com/reference/cli/docker/sandbox/

## Global options

| Option | Description |
|--------|-------------|
| `-D`, `--debug` | Enable debug logging |

## Commands

### docker sandbox run

Create and start a sandbox.

```
docker sandbox run SANDBOX [-- AGENT_ARGS...]
docker sandbox run AGENT [WORKSPACE] [EXTRA_WORKSPACE...] [-- AGENT_ARGS...]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--name` | auto | Custom sandbox identifier |
| `--pull-template` | `missing` | `always`, `missing`, `never` |
| `-t`, `--template` | agent-specific | Container image override |

Examples:

```bash
docker sandbox run claude                              # current directory
docker sandbox run claude ~/projects/my-app            # specific path
docker sandbox run claude . /path/to/docs:ro           # multiple workspaces
docker sandbox run --name my-project claude .           # custom name
docker sandbox run --template my-tpl:v1 claude .        # custom template
docker sandbox run claude . -- -p "Fix the bug"        # pass args to agent
docker sandbox run existing-sandbox                     # restart existing
```

### docker sandbox create

Create a sandbox without starting it.

```
docker sandbox create [OPTIONS] AGENT WORKSPACE
```

Options: `--name`, `--pull-template`, `-q`/`--quiet`, `-t`/`--template`.

Supported agents: `cagent`, `claude`, `codex`, `copilot`, `gemini`, `kiro`, `opencode`,
`shell`.

### docker sandbox exec

Execute a command inside a running sandbox.

```
docker sandbox exec [OPTIONS] SANDBOX COMMAND [ARG...]
```

| Option | Description |
|--------|-------------|
| `-d`, `--detach` | Run in background |
| `--detach-keys` | Override detach key sequence |
| `-e`, `--env` | Set environment variables |
| `--env-file` | Read env vars from file |
| `-i`, `--interactive` | Keep STDIN open |
| `-t`, `--tty` | Allocate pseudo-TTY |
| `-u`, `--user` | Run as specified user |
| `-w`, `--workdir` | Working directory inside sandbox |
| `--privileged` | Extended privileges |

Examples:

```bash
docker sandbox exec -it my-sandbox bash
docker sandbox exec -e GH_TOKEN="tok" my-sandbox python3 script.py
docker sandbox exec -d my-sandbox long-running-task
```

### docker sandbox ls

List all sandboxes. Alias: `docker sandbox list`.

```
docker sandbox ls [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--json` | JSON output |
| `-q`, `--quiet` | Only show sandbox IDs |

Output fields: VM ID, NAME, STATUS, WORKSPACE, SOCKET PATH, SANDBOXES count, AGENTS.

### docker sandbox inspect

Display detailed info on sandboxes.

```
docker sandbox inspect [OPTIONS] SANDBOX [SANDBOX...]
```

Returns JSON with: `id`, `name`, `created_at`, `status`, `template`, `labels`.

### docker sandbox stop

Stop sandboxes without removing them. State is preserved.

```
docker sandbox stop SANDBOX [SANDBOX...]
```

Stop all:

```bash
docker sandbox stop $(docker sandbox ls -q)
```

### docker sandbox rm

Remove one or more sandboxes. Alias: `docker sandbox remove`.

```
docker sandbox rm SANDBOX [SANDBOX...]
```

Remove all:

```bash
docker sandbox rm $(docker sandbox ls -q)
```

### docker sandbox save

Save a snapshot of a sandbox as a reusable template.

```
docker sandbox save SANDBOX TAG
```

| Option | Description |
|--------|-------------|
| `-o`, `--output` | Save to tar file instead of loading into host Docker |

Examples:

```bash
docker sandbox save my-sandbox my-template:v1
docker sandbox save -o template.tar my-sandbox my-template:v1
```

### docker sandbox reset

Reset all VM sandboxes and clean up state. **Destructive**.

```
docker sandbox reset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-f`, `--force` | Skip confirmation |

What it does:
- Stops all VMs (30s timeout)
- Removes state from `~/.docker/sandboxes/vm/`
- Clears image cache at `~/.docker/sandboxes/image-cache/`
- Purges internal registries

### docker sandbox version

Show sandbox plugin version.

```
docker sandbox version
```

Output example: `github.com/docker/sandboxes/cli-plugin v0.7.1 <commit-hash>`

### docker sandbox network proxy

Configure network policies for a sandbox.

```
docker sandbox network proxy <sandbox> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--policy` | Set default policy (`allow` or `deny`) |
| `--allow-host` | Permit access to domain/IP |
| `--block-host` | Block domain/IP |
| `--bypass-host` | Bypass MITM for domain |
| `--allow-cidr` | Remove IP range from block/bypass lists |
| `--block-cidr` | Block IP range (CIDR) |
| `--bypass-cidr` | Bypass MITM for IP range |

### docker sandbox network log

View network traffic logs.

```
docker sandbox network log [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--json` | JSON output |
| `--limit` | Limit entries |
| `-q`, `--quiet` | Quiet mode |

Output: timestamp, sandbox name, HTTP method, URL, allow/deny status.
