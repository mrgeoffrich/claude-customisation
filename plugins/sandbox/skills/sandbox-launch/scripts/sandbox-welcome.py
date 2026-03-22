#!/usr/bin/env python3
"""Welcome message displayed when shelling into a Docker Desktop Sandbox.

Reads sandbox info from ~/.sandbox-info and prints a concise summary
of the sandbox environment and its controls.
"""

from pathlib import Path


def load_info(path: Path) -> dict[str, str]:
    info: dict[str, str] = {}
    if not path.is_file():
        return info
    for line in path.read_text().splitlines():
        line = line.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            info[key.strip()] = value.strip()
    return info


def main() -> None:
    info = load_info(Path.home() / ".sandbox-info")

    sandbox_name = info.get("sandbox_name", "sandbox")
    project_dir = info.get("project_dir", "")

    print()
    print(f"  Sandbox: {sandbox_name}")
    print(f"  Project: {project_dir}")
    print()
    print("  Network:      deny-by-default (allowlisted domains only)")
    print("  Credentials:  proxied (never stored in this VM)")
    print("  File sync:    bidirectional with host")
    print()
    print("  Type 'yolo' to launch Claude with --dangerously-skip-permissions")
    print()


if __name__ == "__main__":
    main()
