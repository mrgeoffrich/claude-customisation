# Claude Customisation

A public collection of scripts and configuration for customising [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Structure

- `statusline/` — Custom statusline scripts for Claude Code's terminal status bar
  - `statusline.sh` — Bash version (macOS/Linux)
  - `statusline.ps1` — PowerShell version (Windows)

## Statusline Scripts

Both scripts display: model name, working directory, git branch, context window usage bar, and Anthropic API usage limits (5-hour and 7-day) with colour-coded percentages and reset countdowns.

### Quick Install

Copy and paste one of the prompts below directly into Claude Code to install the statusline automatically.

#### macOS / Linux (Bash)

```
Download https://raw.githubusercontent.com/mrgeoffrich/claude-customisation/main/statusline/statusline.sh and save it to ~/.claude/statusline.sh — but before writing the file, review the script contents for any security issues and tell me what it does. If it looks safe, save it, make it executable, and add the statusline config to my ~/.claude/settings.json with: { "statusLine": { "type": "command", "command": "bash ~/.claude/statusline.sh" } } (merge with existing settings if the file already exists).
```

#### Windows (PowerShell)

```
Download https://raw.githubusercontent.com/mrgeoffrich/claude-customisation/main/statusline/statusline.ps1 and save it to ~/.claude/statusline.ps1 — but before writing the file, review the script contents for any security issues and tell me what it does. If it looks safe, save it and add the statusline config to my ~/.claude/settings.json with: { "statusLine": { "type": "command", "command": "pwsh -NoProfile -File ~/.claude/statusline.ps1" } } (merge with existing settings if the file already exists).
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
