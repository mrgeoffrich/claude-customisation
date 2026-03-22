#!/usr/bin/env python3
"""Post-launch setup for Docker Desktop Sandbox.

Runs inside the sandbox via:
  docker sandbox exec <name> python3 <project_dir>/.../scripts/setup-sandbox.py <project_dir>

What it does:
- Sets the default working directory so `docker sandbox exec` sessions
  land in the project folder, not the workspace root
- Adds a `yolo` alias for `claude --dangerously-skip-permissions`
- Configures Claude Code with bypassPermissions mode
- Installs and configures Starship prompt if .starship.toml is staged
- Writes sandbox info and adds a welcome message on shell entry

Uses only Python 3 stdlib — no pip dependencies.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


SETUP_MARKER = "# sandbox-launch: setup"
WELCOME_MARKER = "# sandbox-launch: welcome"
STARSHIP_MARKER = "# sandbox-launch: starship"


def get_shell_rc() -> Path:
    """Return the appropriate shell rc file for the current platform."""
    home = Path.home()
    if platform.system() == "Windows":
        # PowerShell profile
        ps_dir = home / "Documents" / "PowerShell"
        ps_dir.mkdir(parents=True, exist_ok=True)
        return ps_dir / "Microsoft.PowerShell_profile.ps1"
    # Linux/macOS — sandbox VMs use bash
    return home / ".bashrc"


def append_if_missing(path: Path, marker: str, lines: list[str]) -> bool:
    """Append lines to a file if the marker is not already present."""
    content = ""
    if path.is_file():
        content = path.read_text()
    if marker in content:
        return False
    with open(path, "a") as f:
        f.write("\n" + marker + "\n")
        for line in lines:
            f.write(line + "\n")
    return True


def setup_shell(project_dir: str, rc_path: Path) -> None:
    """Configure shell with cd to project dir, yolo alias, and GitHub token."""
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    if platform.system() == "Windows":
        lines = [
            f'Set-Location "{project_dir}"',
            'function yolo {{ claude --dangerously-skip-permissions @args }}',
        ]
        if gh_token:
            lines.append(f'$env:GH_TOKEN = "{gh_token}"')
    else:
        lines = [
            f'cd "{project_dir}"',
            "alias yolo='claude --dangerously-skip-permissions'",
        ]
        if gh_token:
            lines.append(f'export GH_TOKEN="{gh_token}"')

    if append_if_missing(rc_path, SETUP_MARKER, lines):
        print(f"  Shell configured: {rc_path}")
        if gh_token:
            print("  GitHub token: set in shell profile")
        else:
            print("  GitHub token: not found in environment (gh/git push won't work)")
    else:
        print(f"  Shell already configured: {rc_path}")


def setup_permissions() -> None:
    """Write bypassPermissions mode to Claude Code settings."""
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_file = claude_dir / "settings.json"

    settings: dict = {}
    if settings_file.is_file():
        try:
            settings = json.loads(settings_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    settings.setdefault("permissions", {})["defaultMode"] = "bypassPermissions"
    settings["skipDangerousModePermissionPrompt"] = True

    settings_file.write_text(json.dumps(settings, indent=2) + "\n")
    print("  Permissions: bypassPermissions (skip prompt suppressed)")


def setup_welcome(project_dir: str, sandbox_name: str, rc_path: Path) -> None:
    """Write sandbox info file and add welcome script to shell rc."""
    home = Path.home()

    # Write ~/.sandbox-info for the welcome script to read
    info_file = home / ".sandbox-info"
    info_file.write_text(
        f"sandbox_name={sandbox_name}\n"
        f"project_dir={project_dir}\n"
    )

    # Path to the welcome script (synced into sandbox at same absolute path)
    welcome_script = (
        Path(project_dir)
        / "plugins/sandbox/skills/sandbox-launch/scripts/sandbox-welcome.py"
    )

    lines = [f'python3 "{welcome_script}" 2>/dev/null']
    if append_if_missing(rc_path, WELCOME_MARKER, lines):
        print(f"  Welcome message: enabled")
    else:
        print(f"  Welcome message: already configured")


def setup_starship(project_dir: str, rc_path: Path) -> str:
    """Install and configure Starship if .starship.toml is staged."""
    staged = Path(project_dir) / ".starship.toml"
    if not staged.is_file():
        return "Starship skipped (no .starship.toml in project dir)"

    # Copy config into place
    config_dir = Path.home() / ".config"
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(staged), str(config_dir / "starship.toml"))

    # Install Starship if not present
    starship_bin = shutil.which("starship")
    local_bin = Path.home() / ".local" / "bin"
    local_starship = local_bin / "starship"

    if not starship_bin and not local_starship.is_file():
        print("  Installing Starship prompt...")
        local_bin.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ["sh", "-c",
                 f"curl -sS https://starship.rs/install.sh | "
                 f"sh -s -- --yes --bin-dir {local_bin}"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                return f"Starship install failed: {result.stderr.strip()}"
        except (subprocess.TimeoutExpired, OSError) as e:
            return f"Starship install failed: {e}"

    # Verify installation
    starship_bin = shutil.which("starship")
    if not starship_bin and not local_starship.is_file():
        return "Starship install failed (check network allowlist for starship.rs)"

    # Configure shell
    if platform.system() == "Windows":
        lines = [
            f'$env:PATH = "{local_bin};$env:PATH"',
            'Invoke-Expression (&starship init powershell)',
        ]
    else:
        lines = [
            f'export PATH="{local_bin}:$PATH"',
            'eval "$(starship init bash)"',
        ]
    append_if_missing(rc_path, STARSHIP_MARKER, lines)

    # Clean up staged file
    try:
        staged.unlink()
    except OSError:
        pass

    return "Starship prompt configured"


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <project_dir> <sandbox_name>", file=sys.stderr)
        sys.exit(1)

    project_dir = sys.argv[1]
    sandbox_name = sys.argv[2]
    rc_path = get_shell_rc()

    print("Setting up sandbox...")
    setup_shell(project_dir, rc_path)
    setup_permissions()
    setup_welcome(project_dir, sandbox_name, rc_path)
    starship_status = setup_starship(project_dir, rc_path)

    print()
    print("Sandbox setup complete:")
    print(f"  Working directory: {project_dir}")
    print("  Alias: yolo -> claude --dangerously-skip-permissions")
    print(f"  {starship_status}")


if __name__ == "__main__":
    main()
