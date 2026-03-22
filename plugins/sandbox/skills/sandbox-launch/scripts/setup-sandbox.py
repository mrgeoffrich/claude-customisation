#!/usr/bin/env python3
"""Post-launch setup for Docker Desktop Sandbox.

Runs inside the sandbox via:
  docker sandbox exec <name> python3 <project_dir>/.setup-sandbox.py <project_dir> <sandbox_name>

Handles per-project/per-sandbox dynamic config only. Static config
(yolo alias, ls colors, bypassPermissions, Starship binary) is baked
into the cc-sandbox template image via the Dockerfile.

What it does:
- Sets the default working directory for the project
- Exports GH_TOKEN and CLAUDE_CODE_OAUTH_TOKEN if provided
- Copies Starship config if .starship.toml is staged
- Writes sandbox info and adds a welcome message on shell entry

Uses only Python 3 stdlib — no pip dependencies.
"""

import os
import sys
from pathlib import Path


SETUP_MARKER = "# sandbox-launch: setup"
AUTH_MARKER = "# sandbox-launch: auth"
WELCOME_MARKER = "# sandbox-launch: welcome"
STARSHIP_CFG_MARKER = "# sandbox-launch: starship-config"


def get_shell_rc() -> Path:
    """Return the shell rc file. Sandbox VMs always run Linux/bash."""
    return Path.home() / ".bashrc"


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
    """Configure shell with cd to project dir and GitHub token."""
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    lines = [
        f'cd "{project_dir}"',
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


def setup_auth(rc_path: Path) -> None:
    """Write Claude Code OAuth token to shell profile for headless auth.

    The token is generated per-sandbox on the host via `claude setup-token`
    and passed in via the CLAUDE_CODE_OAUTH_TOKEN env var. Each sandbox
    requires its own unique token — tokens must not be reused across sandboxes.
    """
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not token:
        print("  Auth token: not provided (user will need to authenticate manually)")
        return

    lines = [
        f'export CLAUDE_CODE_OAUTH_TOKEN="{token}"',
    ]
    if append_if_missing(rc_path, AUTH_MARKER, lines):
        print("  Auth token: set in shell profile")
    else:
        print("  Auth token: already configured")


def setup_welcome(project_dir: str, sandbox_name: str, rc_path: Path) -> None:
    """Write sandbox info file and add welcome script to shell rc."""
    home = Path.home()

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
        print("  Welcome message: enabled")
    else:
        print("  Welcome message: already configured")


def setup_starship_config(project_dir: str, rc_path: Path) -> str:
    """Copy Starship config if .starship.toml is staged.

    The Starship binary is pre-installed in the template image.
    This only copies the user's config file into place.
    """
    staged = Path(project_dir) / ".starship.toml"
    if not staged.is_file():
        return "Starship config: skipped (no .starship.toml in project dir)"

    import shutil

    config_dir = Path.home() / ".config"
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(staged), str(config_dir / "starship.toml"))

    # Clean up staged file
    try:
        staged.unlink()
    except OSError:
        pass

    return "Starship config: copied from host"


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <project_dir> <sandbox_name>", file=sys.stderr)
        sys.exit(1)

    project_dir = sys.argv[1]
    sandbox_name = sys.argv[2]
    rc_path = get_shell_rc()

    print("Setting up sandbox...")
    setup_shell(project_dir, rc_path)
    setup_auth(rc_path)
    setup_welcome(project_dir, sandbox_name, rc_path)
    starship_status = setup_starship_config(project_dir, rc_path)

    print()
    print("Sandbox setup complete:")
    print(f"  Working directory: {project_dir}")
    print(f"  {starship_status}")


if __name__ == "__main__":
    main()
