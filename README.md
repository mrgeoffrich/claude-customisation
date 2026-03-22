# Claude Customisation

A public collection of plugins and skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Plugins

Drop-in plugins that extend what Claude Code can do. Each plugin is focused on a single domain — install only what you need.

### `security` — Security Review

```
/plugin marketplace add mrgeoffrich/claude-customisation
/plugin install security@mrgeoffrich
```

**`security-review`** — Full security audit on demand. Detects your tech stack, then fans out parallel agents across auth, injection, cryptography, dependencies, and infrastructure — each focused on a specific attack surface. Results come back as a prioritised report (CRITICAL → LOW) with file:line references and remediation steps. Covers OWASP Top 10, supply chain risks, and platform-specific categories for web, API, CLI, and mobile projects.

### `web-dev` — Web Development

```
/plugin marketplace add mrgeoffrich/claude-customisation
/plugin install web-dev@mrgeoffrich
```

**`nextjs-starter`** — Scaffolds a production-ready Next.js app from scratch. Wires together Next.js (App Router, Turbopack), shadcn/ui, Tailwind CSS v4, Prisma v7, and dark mode theming — everything configured and talking to each other out of the box. Asks for your project name, database (SQLite/PostgreSQL/MySQL), colour theme, and starter components, then builds the whole thing including a landing page and a `npm run dev`-ready dev server.

### `gws-skills` — Google Workspace

```
/plugin marketplace add mrgeoffrich/claude-customisation
/plugin install gws-skills@mrgeoffrich
```

**`gws-gmail-compose`** — Compose, reply, forward, and send Gmail messages without touching raw base64 APIs. Write your email as a plain `.eml` file or a Markdown `.md` file (auto-converted to styled HTML), and the skill handles RFC 2822 encoding, threading headers, and the Gmail API call. Supports reply, reply-all, forward, and save-as-draft workflows. Requires the [gws CLI](https://github.com/googleworkspace/cli).

### `sandbox` — Docker Sandbox Launcher

```
/plugin marketplace add mrgeoffrich/claude-customisation
/plugin install sandbox@mrgeoffrich
```

**`sandbox-launch`** — Launch Claude Code in an isolated Docker environment with `--dangerously-skip-permissions` enabled safely. Detects your Docker setup and recommends Docker Desktop Sandboxes (microVM-based, strongest isolation) or generates a devcontainer with iptables firewall as fallback. Auto-detects project package managers to configure network allowlists. Handles credential forwarding, network isolation, and workspace security. Pre-installed tools in Docker Sandboxes include Git, GitHub CLI, Node.js, Python 3, Go, and a private Docker daemon.

### `dev-setup` — Developer Setup

```
/plugin marketplace add mrgeoffrich/claude-customisation
/plugin install dev-setup@mrgeoffrich
```

**`cli-tips`** — Opinionated recommendations for CLI tools worth adding to your setup, organised by what kind of work you're doing. Must-haves: **GitHub CLI** (`gh`) for managing PRs, issues, and workflows without leaving the terminal. Web dev & automation: **Playwright CLI**, including codegen, UI mode, trace viewer, and tips for writing reliable browser tests fast. Google Workspace: **gws CLI** — a Rust-built, AI-friendly tool for Drive, Gmail, Calendar, Sheets, and more.

**`statusline`** — Installs a cross-platform Python 3 statusline script to `~/.claude/statusline.py` and configures Claude Code to run it. Displays model name, git branch, context window usage bar, and Anthropic API usage limits (5-hour and 7-day) with reset countdowns. Works on macOS, Linux, and Windows with no pip dependencies.

![Statusline screenshot](screenshot.png)

---

## Structure

- `plugins/` — Claude Code plugins organised by domain
