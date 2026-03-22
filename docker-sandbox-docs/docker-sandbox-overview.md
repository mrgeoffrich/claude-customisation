# Docker Sandboxes Overview

> Source: https://docs.docker.com/ai/sandboxes/

Docker Sandboxes lets you run AI coding agents in isolated environments on your machine.

## Key features

- **YOLO mode by default** — agents work without asking permission
- **Private Docker daemon** for test containers
- **File sharing** between host and sandbox
- **Network access control** via filtering proxy
- **MicroVM-based** — separate Linux kernel per sandbox

## Requirements

- Docker Desktop 4.58+ (macOS or Windows; Windows is experimental)
- Linux users can use legacy container-based sandboxes with Docker Desktop 4.57+

## Basic usage

```bash
docker sandbox run claude ~/my-project
```

Sandboxes persist — installed packages and configurations survive across sessions. Use
`docker sandbox ls` to view (not `docker ps`, since they are VMs not containers).

## Supported agents

| Agent | CLI name | Status |
|-------|----------|--------|
| Claude Code | `claude` | Production-ready |
| Codex | `codex` | Experimental |
| Copilot | `copilot` | Experimental |
| Gemini | `gemini` | Experimental |
| Docker Agent | `cagent` | Experimental |
| Kiro | `kiro` | Experimental |
| OpenCode | `opencode` | Experimental |
| Custom shell | `shell` | Experimental |

All agents share an Ubuntu 25.10 base with Docker CLI, Git, GitHub CLI, Node.js, Go,
Python 3, ripgrep, and jq pre-installed. The `agent` user has sudo access.

## One sandbox per workspace

Docker enforces one sandbox per directory. If the user works on multiple projects, they
need a separate sandbox for each one.
