#!/usr/bin/env python3
"""Network firewall for Claude Code devcontainer sandbox.

Drops all traffic by default, allowlists only essential domains.
Must be run as root (or via sudo) inside the devcontainer.

The sandbox-launch skill customises the PROJECT_DOMAINS list below
based on detected package managers before writing this file.

Uses only Python 3 stdlib — no pip dependencies.
"""

import re
import socket
import subprocess
import sys
import urllib.request


def run(cmd: list[str]) -> int:
    """Run a command, print it, return the exit code."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print(f"  warning: {' '.join(cmd)}: {result.stderr.strip()}", file=sys.stderr)
    return result.returncode


def iptables(*args: str) -> int:
    return run(["iptables", *args])


def resolve_domain(domain: str) -> list[str]:
    """Resolve a domain to IPv4 addresses. Returns empty list on failure."""
    try:
        results = socket.getaddrinfo(domain, None, socket.AF_INET, socket.SOCK_STREAM)
        return list({r[4][0] for r in results})
    except (socket.gaierror, OSError):
        return []


def verify_firewall() -> bool:
    """Verify that non-allowlisted domains are blocked."""
    try:
        urllib.request.urlopen("https://example.com", timeout=3)
        return False  # Should have been blocked
    except Exception:
        return True  # Blocked as expected


def main():
    print("Configuring network firewall...")

    # --- Default policy: drop everything ---
    iptables("-P", "INPUT", "DROP")
    iptables("-P", "OUTPUT", "DROP")
    iptables("-P", "FORWARD", "DROP")

    # --- Allow loopback (needed for local dev servers) ---
    iptables("-A", "INPUT", "-i", "lo", "-j", "ACCEPT")
    iptables("-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT")

    # --- Allow established/related connections ---
    iptables("-A", "INPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT")
    iptables("-A", "OUTPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT")

    # --- Allow DNS resolution ---
    iptables("-A", "OUTPUT", "-p", "udp", "--dport", "53", "-j", "ACCEPT")
    iptables("-A", "OUTPUT", "-p", "tcp", "--dport", "53", "-j", "ACCEPT")

    # --- Required domains (Claude Code infrastructure) ---
    required_domains = [
        "api.anthropic.com",
        "statsig.anthropic.com",
        "statsig.com",
        "sentry.io",
    ]

    # --- Project-specific domains ---
    # The sandbox-launch skill replaces this list with domains detected
    # from the project's package managers and configuration.
    project_domains: list[str] = [
        # PLACEHOLDER: skill will insert detected domains here
    ]

    # --- Resolve and allow all domains ---
    all_domains = required_domains + project_domains
    ipv4_pattern = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

    for domain in all_domains:
        ips = resolve_domain(domain)
        for ip in ips:
            if ipv4_pattern.match(ip):
                iptables("-A", "OUTPUT", "-d", ip, "-j", "ACCEPT")

    # --- GitHub IPs (if GitHub access is needed) ---
    # Uncomment the following block if the project uses GitHub:
    # try:
    #     req = urllib.request.urlopen("https://api.github.com/meta", timeout=10)
    #     import json
    #     meta = json.loads(req.read())
    #     github_cidrs = meta.get("git", []) + meta.get("api", []) + meta.get("web", [])
    #     # ipset provides efficient CIDR matching — fall back to individual rules
    #     if subprocess.run(["which", "ipset"], capture_output=True).returncode == 0:
    #         run(["ipset", "create", "github", "hash:net"])
    #         for cidr in github_cidrs:
    #             run(["ipset", "add", "github", cidr])
    #         iptables("-A", "OUTPUT", "-m", "set", "--match-set", "github", "dst", "-j", "ACCEPT")
    #     else:
    #         for cidr in github_cidrs:
    #             iptables("-A", "OUTPUT", "-d", cidr, "-j", "ACCEPT")
    # except Exception as e:
    #     print(f"  warning: could not fetch GitHub IPs: {e}", file=sys.stderr)

    # --- Verification ---
    print("Verifying firewall blocks non-allowlisted domains...")
    if not verify_firewall():
        print("ERROR: Firewall verification FAILED — example.com is reachable", file=sys.stderr)
        print("The firewall is not working correctly. Aborting.", file=sys.stderr)
        sys.exit(1)

    print("Firewall configured and verified.")
    print(f"Allowed domains: {', '.join(all_domains)}")
    print()
    print("Claude Code can now be started with: claude --dangerously-skip-permissions")


if __name__ == "__main__":
    main()
