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
from datetime import datetime, timedelta


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

    Uses column positions from the header line to correctly handle
    multi-word fields like '<default policy>' and 'HH:MM:SS DD-Mon'.

    Returns list of dicts with keys: sandbox, host, rule, last_seen, count.
    """
    entries: list[dict[str, str]] = []
    in_section = False
    col_starts: dict[str, int] | None = None
    for line in output.splitlines():
        if line.startswith(f"{section} requests:"):
            in_section = True
            col_starts = None
            continue
        if not in_section or not line.strip():
            continue
        if line.endswith("requests:"):
            in_section = False
            continue
        # Parse header to determine column positions
        if line.startswith("SANDBOX"):
            col_starts = {
                "sandbox": line.index("SANDBOX"),
                "host": line.index("HOST"),
                "rule": line.index("RULE"),
                "last_seen": line.index("LAST SEEN"),
                "count": line.index("COUNT"),
            }
            continue
        if col_starts is None:
            continue
        try:
            sandbox = line[col_starts["sandbox"]:col_starts["host"]].strip()
            host = line[col_starts["host"]:col_starts["rule"]].strip()
            rule = line[col_starts["rule"]:col_starts["last_seen"]].strip()
            last_seen = line[col_starts["last_seen"]:col_starts["count"]].strip()
            count_str = line[col_starts["count"]:].strip()
            count = int(count_str)
        except (ValueError, IndexError):
            print(f"  Warning: could not parse network log line: {line!r}",
                  file=sys.stderr)
            continue
        entries.append({
            "sandbox": sandbox,
            "host": host,
            "rule": rule,
            "last_seen": last_seen,
            "count": count,
        })
    return entries


def parse_allowed_hosts(output: str) -> set[str]:
    """Extract unique hosts from the allowed requests section."""
    return {entry["host"] for entry in parse_section(output, "Allowed")}


def parse_last_seen(last_seen: str) -> datetime | None:
    """Parse 'HH:MM:SS DD-Mon' timestamp as local-timezone-aware datetime.

    Docker Desktop logs timestamps in the host's local timezone.
    """
    try:
        now = datetime.now().astimezone()  # tz-aware local time
        local_tz = now.tzinfo
        # Append current year so strptime has a full date (avoids Python 3.15
        # deprecation warning about yearless day-of-month parsing).
        dt = datetime.strptime(f"{last_seen} {now.year}", "%H:%M:%S %d-%b %Y")
        dt = dt.replace(tzinfo=local_tz)
        # If parsed date is in the future, it's from last year
        if dt > now:
            dt = dt.replace(year=now.year - 1)
        return dt
    except ValueError:
        return None


def parse_blocked(output: str, max_age: timedelta | None = None) -> OrderedDict[str, dict]:
    """Parse blocked requests, excluding hosts that are now allowed.

    The network log keeps historical blocked entries even after a rule
    is added. Filter those out by checking the allowed section.
    Entries older than max_age (default 1 hour) are also excluded.

    Returns OrderedDict mapping host -> {"count": int, "last_seen": str}.
    """
    if max_age is None:
        max_age = timedelta(hours=1)
    cutoff = datetime.now().astimezone() - max_age
    allowed_hosts = parse_allowed_hosts(output)
    blocked: OrderedDict[str, dict] = OrderedDict()
    for entry in parse_section(output, "Blocked"):
        if entry["host"] in allowed_hosts:
            continue
        dt = parse_last_seen(entry["last_seen"])
        if dt is not None and dt < cutoff:
            continue
        blocked[entry["host"]] = {
            "count": entry["count"],
            "last_seen": entry["last_seen"],
        }
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


def show_blocked_screen(sandbox_name: str, blocked: OrderedDict[str, dict],
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
        print(f"\n{'#':<4} {'Host':<45} {'Last seen':<16} {'Count':>5}")
        print("-" * 72)
        for i, (host, info) in enumerate(blocked.items(), 1):
            print(f"{i:<4} {host:<45} {info['last_seen']:<16} {info['count']:>5}")

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
        print("No sandboxes found. Create one first with: docker sandbox run --name \"$(basename $(pwd))-cc\" claude \"$(pwd)\"")
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
