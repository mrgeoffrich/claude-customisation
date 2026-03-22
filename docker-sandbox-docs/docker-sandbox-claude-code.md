# Claude Code in Docker Sandboxes

> Source: https://docs.docker.com/ai/sandboxes/agents/claude-code/

## Basic usage

```bash
docker sandbox run claude ~/my-project
```

## Launch with a prompt

```bash
docker sandbox run <sandbox-name> -- "Add error handling to the login function"
```

## Authentication

**Environment variable (preferred):** Set `ANTHROPIC_API_KEY` in shell profile and restart
Docker Desktop. The credential proxy injects it into sandbox requests automatically.

**OAuth token:** Generate via `claude setup-token` on the host, pass into sandbox as
`CLAUDE_CODE_OAUTH_TOKEN` environment variable. Each sandbox needs its own unique token.

**Interactive fallback:** If no key or token is set, Claude Code prompts for login inside
the sandbox. Since there is no browser in the headless VM, the user must copy/paste the
login URL. This requires re-auth per sandbox.

## Configuration

Pass Claude Code options after `--`:

```bash
docker sandbox run <sandbox-name> -- --continue
```

## Technical details

- Base image: `docker/sandbox-templates:claude-code`
- Claude Code launches with `--dangerously-skip-permissions` enabled by default
- Runs as unprivileged `agent` user with sudo access

## Credential environment variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | API key authentication |
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token for headless auth |
| `GH_TOKEN` / `GITHUB_TOKEN` | GitHub CLI and git push |
