# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A public collection of Claude Code plugins distributed via the marketplace as `mrgeoffrich/claude-customisation`. There is no build system, no package manager, and no test runner — skills are prompt-based Markdown files, not compiled code.

## Plugin architecture

Each plugin lives under `plugins/<name>/` and is independently installable:

```
plugins/<name>/
├── .claude-plugin/plugin.json     # Manifest: name, version, description, hooks
└── skills/<skill-name>/
    ├── SKILL.md                   # Required: YAML frontmatter + instructions for Claude
    ├── scripts/                   # Executable scripts (Python, Bash, etc.)
    ├── assets/                    # Template files Claude copies into user projects
    ├── references/                # Documentation loaded on-demand during skill execution
    └── evals/evals.json          # Evaluation scenarios for skill quality validation
```

Agents used by skills live at `plugins/<name>/agents/<agent-name>.md`.

## SKILL.md frontmatter fields

The YAML frontmatter controls how and when a skill is invoked:

- `name` — used as the slash command name
- `description` — natural language trigger conditions; this is what Claude reads to decide whether to auto-invoke the skill
- `allowed-tools` — tools Claude may use without asking permission
- `hooks` — shell commands that run on lifecycle events (e.g. `SessionStart` to set up a Python venv)
- `version`, `metadata` — optional; metadata supports `openclaw` fields like `category` and `requires`

## The five plugins

| Plugin | Skills | Purpose |
|--------|--------|---------|
| `security` | `security-review`, `dependabot-fix` | Multi-agent security audit; Dependabot alert remediation with auto-PR |
| `web-dev` | `nextjs-starter` | Scaffolds Next.js + shadcn/ui + Tailwind v4 + Prisma v7 |
| `gws-skills` | `gws-gmail-compose` | Compose/reply/forward Gmail via `.eml` or `.md` draft files |
| `dev-setup` | `cli-tips`, `statusline` | CLI tool recommendations; statusline install/update |
| `sandbox` | `sandbox-launch` | Docker sandbox launcher for safe `--dangerously-skip-permissions` usage |

## Marketplace distribution

`.claude-plugin/marketplace.json` registers this repo as the `mrgeoffrich` marketplace publisher. Users install plugins via:

```
/plugin marketplace add mrgeoffrich/claude-customisation#plugins/<name>
/plugin install <name>@mrgeoffrich
```

## Statusline

The `statusline` skill (in `dev-setup`) installs a cross-platform Python 3 script (`statusline.py`) to `~/.claude/` and configures Claude Code's status line. It displays model name, git branch, context window usage bar, and Anthropic API usage limits (5-hour and 7-day) with reset countdowns.

## Running tests

Use the project `.venv` for running Python tests:

```bash
.venv/bin/python3 -m pytest <test-file> -v
```

## Scripting standards

- **All scripts must be written in Python 3** (stdlib only where possible) — no Bash scripts
- Scripts must work **cross-platform** (macOS, Linux, Windows) — use `pathlib`, `os.path`, and `platform` instead of platform-specific commands or paths
- Avoid shell-isms like `~`, `$HOME`, or hardcoded `/usr/bin` paths — use `Path.home()`, `os.environ`, and `shutil.which()`

## Docker Sandbox reference docs

`docker-sandbox-docs/` contains reference documentation for Docker Desktop Sandboxes (architecture, CLI, networking, templates, troubleshooting). Consult these when working on the `sandbox` plugin or its `sandbox-launch` skill.

## Skill quality standards

- `description` fields must be precise enough to trigger reliably without false positives — they are the primary routing mechanism
- `allowed-tools` should be minimal; only include tools the skill actually needs
- Scripts in `skills/*/scripts/` should be self-contained with minimal dependencies
- The `gws-gmail-compose` skill uses a `SessionStart` hook to auto-provision a Python venv — this is the pattern to follow for skills with pip dependencies
