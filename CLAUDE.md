# Claude Customisation

A public collection of scripts and configuration for customising [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## Structure

- `statusline/` — Custom statusline scripts for Claude Code's terminal status bar
  - `statusline.sh` — Bash version (macOS/Linux)
  - `statusline.ps1` — PowerShell version (Windows)

## Statusline Scripts

Both scripts display: model name, working directory, git branch, context window usage bar, and Anthropic API usage limits (5-hour and 7-day) with colour-coded percentages and reset countdowns.

### Installation

Copy the appropriate script to `~/.claude/` and configure Claude Code to use it:

```json
{
  "statusline": {
    "command": "bash ~/.claude/statusline.sh"
  }
}
```

Or for PowerShell:

```json
{
  "statusline": {
    "command": "pwsh -NoProfile -File ~/.claude/statusline.ps1"
  }
}
```
