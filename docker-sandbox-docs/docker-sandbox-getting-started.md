# Getting Started with Docker Sandboxes

> Source: https://docs.docker.com/ai/sandboxes/get-started/

## Prerequisites

- Docker Desktop 4.58+
- macOS or Windows (Windows is experimental)
- Claude API key (or Claude Pro/Max subscription for OAuth)

## Step 1 — Configure API key

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

Docker Sandboxes use a daemon process that runs independently of your current shell
session, so inline variable settings won't work. Source the file and **restart Docker
Desktop** after changes.

## Step 2 — Launch

```bash
docker sandbox run claude [PATH]
```

The system auto-generates names based on agent and workspace directory. You can mount
multiple workspaces with `:ro` for read-only:

```bash
docker sandbox run claude . /path/to/docs:ro
```

## What happens at launch

1. Docker creates a lightweight microVM with a private Docker daemon
2. Assigns an automatic name
3. Synchronizes your workspace into the VM
4. Launches Claude Code as a container inside the sandbox VM

## Management commands

```bash
docker sandbox ls                        # list all sandboxes
docker sandbox exec -it <name> bash      # interactive shell
docker sandbox rm <name>                 # remove sandbox
```

Sandboxes don't appear in `docker ps`. Configuration changes require removing and
recreating the sandbox.

## Starting fresh

```bash
docker sandbox rm <name>
docker sandbox run claude ~/my-project
```
