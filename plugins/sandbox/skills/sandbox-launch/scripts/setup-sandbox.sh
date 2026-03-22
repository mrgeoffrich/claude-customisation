#!/usr/bin/env bash
# Post-launch setup for Docker Desktop Sandbox.
# Runs inside the sandbox via: docker sandbox exec <name> bash -c "./setup-sandbox.sh <project_dir>"
#
# What it does:
# - Sets the default working directory so `docker sandbox exec` sessions
#   land in the project folder, not the workspace root
# - Adds a `yolo` alias for `claude --dangerously-skip-permissions`
# - Configures Claude Code with bypassPermissions mode
# - Installs and configures Starship prompt if ~/.config/starship.toml exists on the host

set -euo pipefail

PROJECT_DIR="${1:?Usage: setup-sandbox.sh <project_dir>}"

# --- 1. Default shell working directory ---
# Append cd to .bashrc so interactive exec sessions start in the project dir
BASHRC="${HOME}/.bashrc"
MARKER="# sandbox-launch: setup"
if ! grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "$MARKER" >> "$BASHRC"
    echo "cd \"$PROJECT_DIR\"" >> "$BASHRC"
    echo "alias yolo='claude --dangerously-skip-permissions'" >> "$BASHRC"
fi

# --- 2. Claude Code permissions ---
# Ensure bypassPermissions is set and the one-time warning is suppressed
CLAUDE_DIR="${HOME}/.claude"
SETTINGS_FILE="${CLAUDE_DIR}/settings.json"
mkdir -p "$CLAUDE_DIR"

if command -v python3 &>/dev/null; then
    python3 - "$SETTINGS_FILE" << 'PYEOF'
import json, sys
path = sys.argv[1]
try:
    with open(path) as f:
        settings = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    settings = {}
settings.setdefault("permissions", {})["defaultMode"] = "bypassPermissions"
settings["skipDangerousModePermissionPrompt"] = True
with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
PYEOF
else
    cat > "$SETTINGS_FILE" << 'JSONEOF'
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  },
  "skipDangerousModePermissionPrompt": true
}
JSONEOF
fi

# --- 3. Starship prompt ---
# Look for starship.toml copied into the project dir by the skill
STAGED_STARSHIP="${PROJECT_DIR}/.starship.toml"
STARSHIP_SETUP=""
if [ -f "$STAGED_STARSHIP" ]; then
    # Move config into place
    mkdir -p "${HOME}/.config"
    cp "$STAGED_STARSHIP" "${HOME}/.config/starship.toml"

    if ! command -v starship &>/dev/null; then
        echo "Installing Starship prompt..."
        mkdir -p "${HOME}/.local/bin"
        curl -sS https://starship.rs/install.sh | sh -s -- --yes --bin-dir "${HOME}/.local/bin" >/dev/null 2>&1
    fi
    if command -v starship &>/dev/null || [ -x "${HOME}/.local/bin/starship" ]; then
        STARSHIP_MARKER="# sandbox-launch: starship"
        if ! grep -qF "$STARSHIP_MARKER" "$BASHRC" 2>/dev/null; then
            echo "$STARSHIP_MARKER" >> "$BASHRC"
            echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "$BASHRC"
            echo 'eval "$(starship init bash)"' >> "$BASHRC"
        fi
        STARSHIP_SETUP="Starship prompt configured"
    else
        STARSHIP_SETUP="Starship install failed (check network allowlist for starship.rs)"
    fi
    # Clean up staged file so it doesn't pollute the project
    rm -f "$STAGED_STARSHIP"
else
    STARSHIP_SETUP="Starship skipped (no .starship.toml in project dir)"
fi

echo "Sandbox setup complete:"
echo "  Working directory: $PROJECT_DIR"
echo "  Alias: yolo → claude --dangerously-skip-permissions"
echo "  Permissions: bypassPermissions (skip prompt suppressed)"
echo "  $STARSHIP_SETUP"
