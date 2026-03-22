---
name: statusline
description: >
  Install or update the Claude Code statusline script. Use this skill whenever the user asks to
  set up, install, enable, configure, or update the Claude Code statusline, status bar, or status
  line. Also trigger when the user asks why their statusline isn't working, wants to see model
  info or context usage in the terminal, or mentions the statusline is missing or broken.
---

# Statusline Installer

Installs a cross-platform Python 3 statusline script to `~/.claude/statusline.py` and configures
Claude Code to run it. The script requires only Python 3 stdlib — no pip packages needed — and
works on macOS, Linux, and Windows.

The statusline displays:
- Model name (e.g. `claude-sonnet-4-6`)
- Current directory basename and git branch
- Context window usage bar (green → yellow → red as it fills up)
- Anthropic API usage for the current 5-hour and 7-day windows, with reset countdowns

## Installation steps

### 1. Write the script to `~/.claude/`

Read `.claude/skills/statusline/scripts/statusline.py` and write it to `~/.claude/statusline.py`.
Overwrite if it already exists (this is an update).

On macOS / Linux, make it executable:

```bash
chmod +x ~/.claude/statusline.py
```

### 3. Update `~/.claude/settings.json`

Read the existing `~/.claude/settings.json` (create it if absent) and merge in the `statusLine`
key — do not overwrite other settings.

**macOS / Linux:**
```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py"
  }
}
```

**Windows:**
```json
{
  "statusLine": {
    "type": "command",
    "command": "python ~/.claude/statusline.py"
  }
}
```

### 4. Confirm

Tell the user the statusline is now active and will appear at the bottom of the Claude Code
interface. Mention that API usage figures are cached for 2 minutes, so the first display may
show no usage data until the cache populates.
