# Claude Customisation

A public collection of scripts, configuration, and skills [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Plugins

Drop-in plugins that extend what Claude Code can do. Each plugin is focused on a single domain — install only what you need.

### `security` — Security Review

```
/plugin marketplace add mrgeoffrich/claude-customisation#plugins/security
/plugin install security@mrgeoffrich
```

**`security-review`** — Full security audit on demand. Detects your tech stack, then fans out parallel agents across auth, injection, cryptography, dependencies, and infrastructure — each focused on a specific attack surface. Results come back as a prioritised report (CRITICAL → LOW) with file:line references and remediation steps. Covers OWASP Top 10, supply chain risks, and platform-specific categories for web, API, CLI, and mobile projects.

### `web-dev` — Web Development

```
/plugin marketplace add mrgeoffrich/claude-customisation#plugins/web-dev
/plugin install web-dev@mrgeoffrich
```

**`nextjs-starter`** — Scaffolds a production-ready Next.js app from scratch. Wires together Next.js (App Router, Turbopack), shadcn/ui, Tailwind CSS v4, Prisma v7, and dark mode theming — everything configured and talking to each other out of the box. Asks for your project name, database (SQLite/PostgreSQL/MySQL), colour theme, and starter components, then builds the whole thing including a landing page and a `npm run dev`-ready dev server.

### `gws-skills` — Google Workspace

```
/plugin marketplace add mrgeoffrich/claude-customisation#plugins/gws-skills
/plugin install gws-skills@mrgeoffrich
```

**`gws-gmail-compose`** — Compose, reply, forward, and send Gmail messages without touching raw base64 APIs. Write your email as a plain `.eml` file or a Markdown `.md` file (auto-converted to styled HTML), and the skill handles RFC 2822 encoding, threading headers, and the Gmail API call. Supports reply, reply-all, forward, and save-as-draft workflows. Requires the [gws CLI](https://github.com/googleworkspace/cli).

### `dev-setup` — Developer Setup

```
/plugin marketplace add mrgeoffrich/claude-customisation#plugins/dev-setup
/plugin install dev-setup@mrgeoffrich
```

**`cli-tips`** — Opinionated recommendations for CLI tools worth adding to your setup, organised by what kind of work you're doing. Must-haves: **GitHub CLI** (`gh`) for managing PRs, issues, and workflows without leaving the terminal. Web dev & automation: **Playwright CLI**, including codegen, UI mode, trace viewer, and tips for writing reliable browser tests fast. Google Workspace: **gws CLI** — a Rust-built, AI-friendly tool for Drive, Gmail, Calendar, Sheets, and more.

---

## Structure

- `statusline.sh` — Bash statusline script (macOS/Linux)
- `statusline.ps1` — PowerShell statusline script (Windows)
- `plugins/` — Claude Code plugins organised by domain

## Statusline Scripts

Both scripts display: model name, working directory, git branch, context window usage bar, and Anthropic API usage limits (5-hour and 7-day) with colour-coded percentages and reset countdowns.

![Statusline screenshot](screenshot.png)

### Quick Install

Copy and paste one of the prompts below directly into Claude Code to install the statusline automatically.

#### macOS / Linux (Bash)

```
Download https://raw.githubusercontent.com/mrgeoffrich/claude-customisation/main/statusline.sh and save it to ~/.claude/statusline.sh — but before writing the file, review the script contents for any security issues and tell me what it does. If it looks safe, save it, make it executable, and add the statusline config to my ~/.claude/settings.json with: { "statusLine": { "type": "command", "command": "bash ~/.claude/statusline.sh" } } (merge with existing settings if the file already exists).
```

#### Windows (PowerShell)

```
Download https://raw.githubusercontent.com/mrgeoffrich/claude-customisation/main/statusline.ps1 and save it to ~/.claude/statusline.ps1 — but before writing the file, review the script contents for any security issues and tell me what it does. If it looks safe, save it and add the statusline config to my ~/.claude/settings.json with: { "statusLine": { "type": "command", "command": "pwsh -NoProfile -File ~/.claude/statusline.ps1" } } (merge with existing settings if the file already exists).
```

### Manual Installation

Copy the appropriate script to `~/.claude/` and add the following to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/statusline.sh"
  }
}
```

Or for PowerShell:

```json
{
  "statusLine": {
    "type": "command",
    "command": "pwsh -NoProfile -File ~/.claude/statusline.ps1"
  }
}
```
