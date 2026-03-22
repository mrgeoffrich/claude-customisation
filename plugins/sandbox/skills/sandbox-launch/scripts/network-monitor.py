#!/usr/bin/env python3
"""Interactive network monitor for Docker Desktop Sandboxes.

Polls `docker sandbox network log` for blocked requests and lets the user
allow or remove domains interactively.

Usage:
    python3 network-monitor.py <sandbox-name>

Uses only Python 3 stdlib — no pip dependencies.
"""

import select
import subprocess
import sys
import time
from collections import OrderedDict


def get_network_log() -> str:
    """Run docker sandbox network log and return output."""
    try:
        result = subprocess.run(
            ["docker", "sandbox", "network", "log"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def parse_section(output: str, section: str) -> list[dict[str, str]]:
    """Parse a section (Blocked/Allowed) from network log output.

    Returns list of dicts with keys: sandbox, host, rule, last_seen, count.
    """
    entries: list[dict[str, str]] = []
    in_section = False
    for line in output.splitlines():
        if line.startswith(f"{section} requests:"):
            in_section = True
            continue
        if in_section and line.strip() and not line.startswith(f"{section}"):
            # Check if we've hit another section
            if line.endswith("requests:"):
                in_section = False
                continue
            # Skip header
            if line.startswith("SANDBOX") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                try:
                    count = int(parts[-1])
                except ValueError:
                    count = 1
                entries.append({
                    "sandbox": parts[0],
                    "host": parts[1],
                    "rule": parts[2],
                    "count": count,
                })
            elif parts:
                print(f"  Warning: could not parse network log line: {line!r}",
                      file=sys.stderr)
    return entries


def parse_allowed_hosts(output: str) -> set[str]:
    """Extract unique hosts from the allowed requests section."""
    return {entry["host"] for entry in parse_section(output, "Allowed")}


def parse_blocked(output: str) -> OrderedDict[str, int]:
    """Parse blocked requests, excluding hosts that are now allowed.

    The network log keeps historical blocked entries even after a rule
    is added. Filter those out by checking the allowed section.
    """
    allowed_hosts = parse_allowed_hosts(output)
    blocked: OrderedDict[str, int] = OrderedDict()
    for entry in parse_section(output, "Blocked"):
        if entry["host"] not in allowed_hosts:
            blocked[entry["host"]] = entry["count"]
    return blocked


def parse_allowed_rules(output: str) -> list[str]:
    """Extract unique allow rules from the allowed requests section."""
    rules: OrderedDict[str, None] = OrderedDict()
    for entry in parse_section(output, "Allowed"):
        rule = entry["rule"]
        if rule not in rules:
            rules[rule] = None
    return list(rules.keys())


def allow_host(sandbox_name: str, host: str) -> bool:
    """Add a host to the sandbox network allowlist."""
    domain = host.split(":")[0]
    try:
        result = subprocess.run(
            ["docker", "sandbox", "network", "proxy", sandbox_name,
             "--allow-host", domain],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def block_host(sandbox_name: str, rule: str) -> bool:
    """Remove a host from the allowlist by blocking it."""
    domain = rule.split(":")[0]
    try:
        result = subprocess.run(
            ["docker", "sandbox", "network", "proxy", sandbox_name,
             "--block-host", domain],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def clear_screen() -> None:
    """Clear terminal screen cross-platform."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def prompt_with_timeout(timeout: float) -> str:
    """Read input with a timeout using select."""
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.readline().strip()
    except (OSError, ValueError):
        time.sleep(timeout)
    return ""


def prompt_blocking(prompt_text: str) -> str:
    """Blocking input prompt."""
    try:
        return input(prompt_text).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


# ── Screens ──────────────────────────────────────────────────────────────


def show_blocked_screen(sandbox_name: str, blocked: OrderedDict[str, int],
                        allowed_this_session: list[str]) -> None:
    """Display the blocked domains polling screen."""
    clear_screen()
    print(f"Network Monitor: {sandbox_name}")
    print(f"Polling every 5s | {len(blocked)} blocked domain(s)")
    print("=" * 60)

    if allowed_this_session:
        print(f"\nAllowed this session: {', '.join(allowed_this_session)}")

    if not blocked:
        print("\nNo blocked requests detected.")
    else:
        print(f"\n{'#':<4} {'Host':<45} {'Count':>5}")
        print("-" * 56)
        for i, (host, count) in enumerate(blocked.items(), 1):
            print(f"{i:<4} {host:<45} {count:>5}")

    print()
    print("Commands:")
    print("  <number>    Allow that domain")
    print("  l           View allowlist")
    print("  r           Refresh now")
    print("  q           Quit")


def show_allowlist_screen(sandbox_name: str) -> str:
    """Display the current allowlist and let user remove entries.

    Returns the command to process ('b' for back, or a number to remove).
    """
    output = get_network_log()
    rules = parse_allowed_rules(output)

    clear_screen()
    print(f"Allowlist: {sandbox_name}")
    print(f"{len(rules)} allowed rule(s)")
    print("=" * 60)

    if not rules:
        print("\nNo allowed rules found.")
    else:
        print(f"\n{'#':<4} {'Rule'}")
        print("-" * 50)
        for i, rule in enumerate(rules, 1):
            print(f"{i:<4} {rule}")

    print()
    print("Commands:")
    print("  <number>    Remove that rule (block it)")
    print("  b           Back to monitor")

    while True:
        cmd = prompt_blocking("\n> ")
        if not cmd:
            continue
        if cmd.lower() == "b":
            return "back"
        try:
            idx = int(cmd)
            if 1 <= idx <= len(rules):
                rule = rules[idx - 1]
                domain = rule.split(":")[0]
                confirm = prompt_blocking(f"  Remove '{domain}'? (y/n): ")
                if confirm.lower() == "y":
                    if block_host(sandbox_name, rule):
                        print(f"  Removed: {domain}")
                    else:
                        print(f"  Failed to remove: {domain}")
                    time.sleep(1)
                    return "refresh_list"
                else:
                    print("  Cancelled.")
            else:
                print(f"  Invalid number. Enter 1-{len(rules)}.")
        except ValueError:
            print(f"  Unknown command: {cmd}")


# ── Main loop ────────────────────────────────────────────────────────────


def list_sandboxes() -> list[str]:
    """Get list of running sandbox names."""
    try:
        result = subprocess.run(
            ["docker", "sandbox", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        return [name.strip() for name in result.stdout.strip().splitlines() if name.strip()]
    except (subprocess.TimeoutExpired, OSError):
        return []


def select_sandbox() -> str:
    """Prompt the user to select a sandbox from the list."""
    sandboxes = list_sandboxes()
    if not sandboxes:
        print("No sandboxes found. Create one first with: docker sandbox run claude \"$(pwd)\"")
        sys.exit(1)
    if len(sandboxes) == 1:
        print(f"Using sandbox: {sandboxes[0]}")
        return sandboxes[0]

    print("Select a sandbox:\n")
    for i, name in enumerate(sandboxes, 1):
        print(f"  {i}) {name}")
    print()

    while True:
        choice = prompt_blocking("> ")
        try:
            idx = int(choice)
            if 1 <= idx <= len(sandboxes):
                return sandboxes[idx - 1]
            print(f"  Enter 1-{len(sandboxes)}.")
        except ValueError:
            print(f"  Enter a number.")


def main() -> None:
    if len(sys.argv) >= 2:
        sandbox_name = sys.argv[1]
    else:
        sandbox_name = select_sandbox()
    allowed_this_session: list[str] = []

    print(f"Starting network monitor for {sandbox_name}...")
    print("Fetching initial network log...\n")

    try:
        while True:
            output = get_network_log()
            blocked = parse_blocked(output)

            # Remove already-allowed domains
            for host in allowed_this_session:
                blocked.pop(host, None)

            show_blocked_screen(sandbox_name, blocked, allowed_this_session)

            cmd = prompt_with_timeout(5.0)
            if not cmd:
                continue

            if cmd.lower() == "q":
                print("\nExiting.")
                break
            elif cmd.lower() == "r":
                continue
            elif cmd.lower() == "l":
                while True:
                    result = show_allowlist_screen(sandbox_name)
                    if result == "back":
                        break
                    # "refresh_list" loops back to show updated list
            else:
                try:
                    idx = int(cmd)
                    hosts = list(blocked.keys())
                    if 1 <= idx <= len(hosts):
                        host = hosts[idx - 1]
                        domain = host.split(":")[0]
                        if allow_host(sandbox_name, host):
                            allowed_this_session.append(host)
                            print(f"  Allowed: {domain}")
                        else:
                            print(f"  Failed to allow: {domain}")
                        time.sleep(1)
                    else:
                        print(f"  Invalid number. Enter 1-{len(hosts)}.")
                        time.sleep(1)
                except ValueError:
                    print(f"  Unknown command: {cmd}")
                    time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nExiting.")


if __name__ == "__main__":
    main()
