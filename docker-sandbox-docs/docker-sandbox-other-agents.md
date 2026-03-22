# Other Agents in Docker Sandboxes

> Sources:
> - https://docs.docker.com/ai/sandboxes/agents/
> - https://docs.docker.com/ai/sandboxes/agents/gemini/
> - https://docs.docker.com/ai/sandboxes/agents/copilot/
> - https://docs.docker.com/ai/sandboxes/agents/codex/
> - https://docs.docker.com/ai/sandboxes/agents/docker-agent/
> - https://docs.docker.com/ai/sandboxes/agents/kiro/
> - https://docs.docker.com/ai/sandboxes/agents/opencode/
> - https://docs.docker.com/ai/sandboxes/agents/shell/

## Agent summary

All agents share an Ubuntu 25.10 base with Docker CLI, Git, GitHub CLI, Node.js, Go,
Python 3, ripgrep, and jq. Agent type is bound at creation and cannot be changed.

## Gemini

- **CLI name:** `gemini`
- **Template:** `docker/sandbox-templates:gemini`
- **Auth:** `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- **YOLO mode:** `--yolo` flag bypasses approval prompts
- OAuth is disabled; credential management through proxy

## Copilot

- **CLI name:** `copilot`
- **Template:** `docker/sandbox-templates:copilot`
- **Auth:** `GH_TOKEN` or `GITHUB_TOKEN`
- **YOLO mode:** `--yolo` disables approval prompts
- Configure trusted folders in `~/.copilot/config.json`

## Codex

- **CLI name:** `codex`
- **Template:** `docker/sandbox-templates:codex`
- **Auth:** `OPENAI_API_KEY`
- **YOLO mode:** Set in `~/.codex/config.toml`:
  ```toml
  approval_policy = "never"
  sandbox_mode = "danger-full-access"
  ```
  Or use `--dangerously-bypass-approvals-and-sandbox`

## Docker Agent

- **CLI name:** `cagent`
- **Template:** `docker/sandbox-templates:cagent`
- **Auth:** Proxy-managed auth for OpenAI, Anthropic, Google, xAI, Nebius, Mistral
- **YOLO mode:** `-- run --yolo`

## Kiro

- **CLI name:** `kiro`
- **Template:** `docker/sandbox-templates:kiro`
- **Auth:** Device flow (browser-based). Auth persists in
  `~/.local/share/kiro-cli/data.sqlite3`
- **YOLO mode:** Trust-all-tools mode enabled by default

## OpenCode

- **CLI name:** `opencode`
- **Template:** `docker/sandbox-templates:opencode`
- **Auth:** Multi-provider — OpenAI, Anthropic, Google, xAI, Groq, AWS
- **Interface:** TUI mode

## Shell

- **CLI name:** `shell`
- **Template:** `docker/sandbox-templates:shell`
- **Purpose:** Minimal environment with no pre-installed agent. For custom agents,
  development, and troubleshooting

## Credential environment variables

| Variable | Agent(s) |
|----------|----------|
| `ANTHROPIC_API_KEY` | Claude Code, Docker Agent |
| `OPENAI_API_KEY` | Codex, Docker Agent, OpenCode |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Gemini |
| `GH_TOKEN` / `GITHUB_TOKEN` | Copilot |
| `XAI_API_KEY` | Docker Agent, OpenCode |
| `GROQ_API_KEY` | OpenCode |
| `NEBIUS_API_KEY` | Docker Agent |
| `MISTRAL_API_KEY` | Docker Agent |
