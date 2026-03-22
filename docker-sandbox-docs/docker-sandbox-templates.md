# Docker Sandbox Custom Templates

> Source: https://docs.docker.com/ai/sandboxes/templates/

## When to use

- Multiple team members need the same environment
- Many sandboxes with identical tooling
- Complex setup that shouldn't be repeated
- Specific tool versions required

## Building from Dockerfile

```dockerfile
FROM docker/sandbox-templates:claude-code

USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir pytest black pylint
USER agent
```

Official templates include: agent binary, Ubuntu base, Git, Docker CLI, Node.js, Python,
Go. The sandbox runs as an unprivileged `agent` user with sudo. Switch to `root` for
installs, back to `agent` before finishing.

## Using a custom template

```bash
docker build -t my-template:v1 .
docker sandbox run -t my-template:v1 claude ~/my-project
```

## Pull policies

| Flag | Behavior |
|------|----------|
| `--pull-template missing` | Use cached local, pull from registry if missing (default) |
| `--pull-template always` | Always refresh from registry |
| `--pull-template never` | Skip host cache, VM pulls directly each time |

## Saving from an existing sandbox

Snapshot a running sandbox after installing everything needed:

```bash
docker sandbox save claude-project my-template:v1
```

Export to tar:

```bash
docker sandbox save -o template.tar claude-project my-template:v1
```

## Sharing with a team

Push to a container registry with version tags:

```bash
docker push myorg/sandbox-templates:python-v1.0
```

Team members use:

```bash
docker sandbox run -t myorg/sandbox-templates:python-v1.0 claude ~/project
```

## Base template images

| Agent | Template Image |
|-------|---------------|
| Claude Code | `docker/sandbox-templates:claude-code` |
| Codex | `docker/sandbox-templates:codex` |
| Copilot | `docker/sandbox-templates:copilot` |
| Gemini | `docker/sandbox-templates:gemini` |
| Docker Agent | `docker/sandbox-templates:cagent` |
| Kiro | `docker/sandbox-templates:kiro` |
| OpenCode | `docker/sandbox-templates:opencode` |
| Shell | `docker/sandbox-templates:shell` |

## Limitation

Generic images like `python:3.11` lack agent binaries and sandbox config — they will fail.
Always extend from an official `docker/sandbox-templates:*` base.
