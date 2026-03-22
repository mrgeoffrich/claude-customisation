"""Tests for network-monitor.py parsing functions.

Uses real `docker sandbox network log` output to verify column-position
parsing handles multi-word fields (e.g. '<default policy>', timestamps).
"""

import importlib.util
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "network_monitor",
    Path(__file__).parent / "network-monitor.py",
)
mod = importlib.util.module_from_spec(spec)
mod.__spec__ = spec
spec.loader.exec_module(mod)

parse_section = mod.parse_section
parse_allowed_hosts = mod.parse_allowed_hosts
parse_allowed_rules = mod.parse_allowed_rules
parse_blocked = mod.parse_blocked
parse_last_seen = mod.parse_last_seen

# Real output captured from `docker sandbox network log`
REAL_LOG = """\
Blocked requests:
SANDBOX                       HOST                                                                               RULE               LAST SEEN         COUNT
claude-claude-customisation   example.com:443                                                                    <default policy>   20:33:18 22-Mar   1
claude-claude-customisation   docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com:443   <default policy>   20:03:15 22-Mar   1

Allowed requests:
SANDBOX                       HOST                                                                               RULE                            LAST SEEN         COUNT
claude-GeneralClaude          release-assets.githubusercontent.com:443                                           <default policy>                21:09:47 22-Mar   1
claude-GeneralClaude          github.com:443                                                                     github.com:443                  21:09:47 22-Mar   2
claude-GeneralClaude          starship.rs:443                                                                    <default policy>                21:09:45 22-Mar   1
claude-GeneralClaude          api.anthropic.com:443                                                              api.anthropic.com:443           21:05:35 22-Mar   2
claude-claude-customisation   registry-1.docker.io:443                                                           *.docker.io:443                 20:03:15 22-Mar   28
"""


# ---------------------------------------------------------------------------
# parse_section — Blocked
# ---------------------------------------------------------------------------


def test_parse_blocked_section_count():
    entries = parse_section(REAL_LOG, "Blocked")
    assert len(entries) == 2


def test_parse_blocked_default_policy_rule():
    """<default policy> is two words — must not be split."""
    entries = parse_section(REAL_LOG, "Blocked")
    assert entries[0]["rule"] == "<default policy>"
    assert entries[1]["rule"] == "<default policy>"


def test_parse_blocked_fields():
    entries = parse_section(REAL_LOG, "Blocked")
    e = entries[0]
    assert e["sandbox"] == "claude-claude-customisation"
    assert e["host"] == "example.com:443"
    assert e["last_seen"] == "20:33:18 22-Mar"
    assert e["count"] == 1


def test_parse_blocked_long_host():
    """Very long hostnames must not be truncated."""
    entries = parse_section(REAL_LOG, "Blocked")
    e = entries[1]
    assert e["host"] == "docker-images-prod.6aa30f8b08e16409b46e0173d6de2f56.r2.cloudflarestorage.com:443"
    assert e["last_seen"] == "20:03:15 22-Mar"


# ---------------------------------------------------------------------------
# parse_section — Allowed
# ---------------------------------------------------------------------------


def test_parse_allowed_section_count():
    entries = parse_section(REAL_LOG, "Allowed")
    assert len(entries) == 5


def test_parse_allowed_wildcard_rule():
    entries = parse_section(REAL_LOG, "Allowed")
    docker_io = [e for e in entries if "docker.io" in e["host"]]
    assert len(docker_io) == 1
    assert docker_io[0]["rule"] == "*.docker.io:443"
    assert docker_io[0]["count"] == 28


def test_parse_allowed_default_policy_rule():
    entries = parse_section(REAL_LOG, "Allowed")
    defaults = [e for e in entries if e["rule"] == "<default policy>"]
    assert len(defaults) == 2


def test_parse_allowed_timestamps():
    entries = parse_section(REAL_LOG, "Allowed")
    for e in entries:
        # All timestamps should match HH:MM:SS DD-Mon format
        parts = e["last_seen"].split()
        assert len(parts) == 2, f"Unexpected timestamp format: {e['last_seen']}"


# ---------------------------------------------------------------------------
# parse_allowed_hosts / parse_allowed_rules
# ---------------------------------------------------------------------------


def test_parse_allowed_hosts():
    hosts = parse_allowed_hosts(REAL_LOG)
    assert "github.com:443" in hosts
    assert "api.anthropic.com:443" in hosts
    assert "registry-1.docker.io:443" in hosts
    # Blocked-only hosts should not appear
    assert "example.com:443" not in hosts


def test_parse_allowed_rules():
    rules = parse_allowed_rules(REAL_LOG)
    assert "github.com:443" in rules
    assert "*.docker.io:443" in rules
    assert "<default policy>" in rules


# ---------------------------------------------------------------------------
# parse_blocked (top-level, filters out now-allowed hosts)
# ---------------------------------------------------------------------------


def _make_timestamp(dt: datetime) -> str:
    """Format a datetime as 'HH:MM:SS DD-Mon' to match docker log output."""
    return dt.strftime("%H:%M:%S %d-%b")


def _make_blocked_log(entries: list[tuple[str, str]],
                      allowed: list[tuple[str, str]] | None = None) -> str:
    """Build a fake network log with given blocked (host, timestamp) pairs."""
    header = "SANDBOX       HOST                  RULE               LAST SEEN         COUNT"
    lines = [header]
    for host, ts in entries:
        lines.append(f"my-sandbox    {host:<22}{'<default policy>':<19}{ts:<18}1")
    blocked_section = "Blocked requests:\n" + "\n".join(lines)

    allowed_section = "Allowed requests:\n"
    if allowed:
        a_header = "SANDBOX       HOST                  RULE                  LAST SEEN         COUNT"
        a_lines = [a_header]
        for host, ts in allowed:
            a_lines.append(f"my-sandbox    {host:<22}{host:<22}{ts:<18}1")
        allowed_section += "\n".join(a_lines)
    else:
        allowed_section += header

    return blocked_section + "\n\n" + allowed_section + "\n"


def test_parse_blocked_excludes_allowed():
    """Hosts that appear in both blocked and allowed should be filtered out."""
    now = datetime.now()
    ts = _make_timestamp(now - timedelta(minutes=5))
    log = _make_blocked_log(
        [("example.com:443", ts), ("now-allowed.com:443", ts)],
        allowed=[("now-allowed.com:443", ts)],
    )
    blocked = parse_blocked(log)
    assert "example.com:443" in blocked
    assert "now-allowed.com:443" not in blocked


def test_parse_blocked_returns_last_seen():
    now = datetime.now()
    ts = _make_timestamp(now - timedelta(minutes=5))
    log = _make_blocked_log([("example.com:443", ts)])
    blocked = parse_blocked(log)
    assert "example.com:443" in blocked
    info = blocked["example.com:443"]
    assert info["count"] == 1
    assert info["last_seen"] == ts


# ---------------------------------------------------------------------------
# parse_last_seen
# ---------------------------------------------------------------------------


def test_parse_last_seen_recent():
    now = datetime.now().astimezone()
    ts = _make_timestamp(now - timedelta(minutes=30))
    dt = parse_last_seen(ts)
    assert dt is not None
    assert dt.tzinfo is not None
    assert abs((now - dt).total_seconds() - 30 * 60) < 60


def test_parse_last_seen_invalid():
    assert parse_last_seen("garbage") is None
    assert parse_last_seen("") is None


def test_parse_last_seen_year_rollover():
    """A timestamp that would be in the future gets assigned to last year."""
    now = datetime.now()
    future = now + timedelta(days=10)
    ts = _make_timestamp(future)
    dt = parse_last_seen(ts)
    assert dt is not None
    assert dt.year == now.year - 1


# ---------------------------------------------------------------------------
# Time-based filtering
# ---------------------------------------------------------------------------


def test_parse_blocked_filters_old_entries():
    """Entries older than 1 hour should be excluded by default."""
    now = datetime.now()
    recent_ts = _make_timestamp(now - timedelta(minutes=30))
    old_ts = _make_timestamp(now - timedelta(hours=2))
    log = _make_blocked_log([
        ("recent.com:443", recent_ts),
        ("old.com:443", old_ts),
    ])
    blocked = parse_blocked(log)
    assert "recent.com:443" in blocked
    assert "old.com:443" not in blocked


def test_parse_blocked_custom_max_age():
    """max_age parameter controls the cutoff."""
    now = datetime.now()
    ts = _make_timestamp(now - timedelta(minutes=10))
    log = _make_blocked_log([("example.com:443", ts)])
    # 5-minute window — 10-minute-old entry should be excluded
    blocked = parse_blocked(log, max_age=timedelta(minutes=5))
    assert "example.com:443" not in blocked
    # 20-minute window — same entry should be included
    blocked = parse_blocked(log, max_age=timedelta(minutes=20))
    assert "example.com:443" in blocked


def test_parse_blocked_unparseable_timestamp_kept():
    """If timestamp can't be parsed, entry is kept (fail-open)."""
    header = "SANDBOX       HOST                RULE               LAST SEEN         COUNT"
    line =   "my-sandbox    bad-ts.com:443      <default policy>   not-a-date        1"
    log = f"Blocked requests:\n{header}\n{line}\n\nAllowed requests:\n{header}\n"
    blocked = parse_blocked(log)
    assert "bad-ts.com:443" in blocked


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_output():
    assert parse_section("", "Blocked") == []
    assert parse_section("", "Allowed") == []
    blocked = parse_blocked("")
    assert len(blocked) == 0


def test_section_with_no_entries():
    log = """\
Blocked requests:
SANDBOX   HOST   RULE   LAST SEEN   COUNT

Allowed requests:
SANDBOX   HOST   RULE   LAST SEEN   COUNT
"""
    assert parse_section(log, "Blocked") == []
    assert parse_section(log, "Allowed") == []
