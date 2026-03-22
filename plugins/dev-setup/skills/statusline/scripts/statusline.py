#!/usr/bin/env python3
"""Claude Code statusline — cross-platform, stdlib only.

Reads the Claude Code statusline JSON from stdin and prints a formatted
status line with model, directory, git branch, context bar, and API usage.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Read input ────────────────────────────────────────────────────────────────
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)

model = data.get("model", {}).get("display_name", "?")
cwd   = data.get("workspace", {}).get("current_dir", "")
pct   = int(float(data.get("context_window", {}).get("used_percentage", 0)))

# ── ANSI colours ──────────────────────────────────────────────────────────────
CYAN    = "\033[36m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
RESET   = "\033[0m"
DIM     = "\033[2m"
MAGENTA = "\033[35m"
LTBLUE  = "\033[38;5;117m"

# Enable ANSI escape processing on Windows 10+
if sys.platform == "win32":
    os.system("")

# ── Context bar ───────────────────────────────────────────────────────────────
if pct >= 90:
    bar_color = RED
elif pct >= 70:
    bar_color = YELLOW
else:
    bar_color = GREEN

filled = pct // 10
bar    = "█" * filled + "░" * (10 - filled)

# ── Git branch ────────────────────────────────────────────────────────────────
branch = ""
try:
    r = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True, timeout=2,
    )
    if r.returncode == 0:
        br = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2,
        )
        bname = br.stdout.strip()
        if bname:
            branch = f"{LTBLUE}⎇ {bname}{RESET}"
except Exception:
    pass

# ── Account usage (5h + 7d) ───────────────────────────────────────────────────
CACHE_FILE = Path(tempfile.gettempdir()) / "claude-usage-cache.json"
CACHE_TTL  = 120  # seconds


def get_token() -> str | None:
    # File-based credentials (Linux / cross-platform)
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        try:
            creds = json.loads(creds_path.read_text())
            token = creds.get("claudeAiOauth", {}).get("accessToken")
            if token:
                return token
        except Exception:
            pass
    # macOS Keychain
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=4,
        )
        if r.returncode == 0 and r.stdout.strip():
            creds = json.loads(r.stdout.strip())
            token = creds.get("claudeAiOauth", {}).get("accessToken")
            if token:
                return token
    except Exception:
        pass
    return None


def fetch_usage(token: str) -> dict | None:
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization":  f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
                "Content-Type":   "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def usage_color(p: int) -> str:
    if p >= 90:
        return RED
    if p >= 70:
        return YELLOW
    return GREEN


def format_reset(iso: str) -> str:
    if not iso:
        return ""
    try:
        iso_clean  = iso.split(".")[0].rstrip("Z")
        reset_time = datetime.strptime(iso_clean, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        total_s    = int((reset_time - datetime.now(timezone.utc)).total_seconds())
        if total_s <= 0:
            return "now"
        days = total_s // 86400
        hrs  = (total_s % 86400) // 3600
        mins = (total_s % 3600)  // 60
        return f"{days}:{hrs:02d}:{mins:02d}" if days > 0 else f"{hrs}:{mins:02d}"
    except Exception:
        return ""


# Refresh cache if stale
cache_age = CACHE_TTL + 1
if CACHE_FILE.exists():
    try:
        cache_age = time.time() - CACHE_FILE.stat().st_mtime
    except Exception:
        pass

if cache_age > CACHE_TTL:
    token = get_token()
    if token:
        resp = fetch_usage(token)
        if resp and "five_hour" in resp:
            try:
                CACHE_FILE.write_text(json.dumps(resp))
            except Exception:
                pass

# Build usage segment from cache
usage_segment = ""
if CACHE_FILE.exists():
    try:
        cache        = json.loads(CACHE_FILE.read_text())
        five_h_raw   = cache.get("five_hour",  {}).get("utilization")
        seven_d_raw  = cache.get("seven_day",  {}).get("utilization")
        five_h_reset = cache.get("five_hour",  {}).get("resets_at", "")
        seven_d_reset= cache.get("seven_day",  {}).get("resets_at", "")

        if five_h_raw is not None and seven_d_raw is not None:
            fh = int(float(five_h_raw))
            sd = int(float(seven_d_raw))
            fh_eta     = format_reset(five_h_reset)
            sd_eta     = format_reset(seven_d_reset)
            fh_eta_str = f"{DIM}~{fh_eta}{RESET}" if fh_eta else ""
            sd_eta_str = f"{DIM}~{sd_eta}{RESET}" if sd_eta else ""
            usage_segment = (
                f" | {MAGENTA}5h:{RESET}{usage_color(fh)}{fh}%{RESET}{fh_eta_str}"
                f" {MAGENTA}7d:{RESET}{usage_color(sd)}{sd}%{RESET}{sd_eta_str}"
            )
    except Exception:
        pass

# ── Output ────────────────────────────────────────────────────────────────────
dir_name = Path(cwd).name if cwd else ""
print(
    f"{CYAN}[{model}]{RESET} {dir_name} {branch} | {bar_color}{bar}{RESET} {pct}%{usage_segment}",
    end="",
)
