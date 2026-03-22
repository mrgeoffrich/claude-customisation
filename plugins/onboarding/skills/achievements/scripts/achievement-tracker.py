#!/usr/bin/env python3
"""
Achievement tracker for Claude Code onboarding.

Tracks user progress through beginner and intermediate achievements
by listening to hook events (SessionStart, PostToolUse, Stop).

State is persisted to ${CLAUDE_PLUGIN_DATA}/achievements.json.
Newly unlocked achievements are announced via stdout (shown to user as context).
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Achievement definitions
# ---------------------------------------------------------------------------

ACHIEVEMENTS = {
    # ── Beginner ──────────────────────────────────────────────────────────
    "first-session": {
        "tier": "beginner",
        "title": "Hello, Claude!",
        "description": "Start your first Claude Code session",
        "hint": "Just launch `claude` in your terminal — you've already begun!",
        "detect": "session-start",
    },
    "file-reader": {
        "tier": "beginner",
        "title": "Curious Eyes",
        "description": "Ask Claude to read a file",
        "hint": "Try asking Claude to look at a file: \"read src/index.ts\"",
        "detect": "tool:Read",
    },
    "code-editor": {
        "tier": "beginner",
        "title": "First Edit",
        "description": "Have Claude edit a file for you",
        "hint": "Ask Claude to make a change: \"add a comment to the top of main.py\"",
        "detect": "tool:Edit",
    },
    "file-creator": {
        "tier": "beginner",
        "title": "From Nothing",
        "description": "Have Claude create a new file",
        "hint": "Ask Claude to create something: \"create a hello.py that prints hello world\"",
        "detect": "tool:Write",
    },
    "command-runner": {
        "tier": "beginner",
        "title": "Terminal Tamer",
        "description": "Have Claude run a shell command",
        "hint": "Ask Claude to run something: \"run the tests\" or \"check git status\"",
        "detect": "tool:Bash",
    },
    "code-searcher": {
        "tier": "beginner",
        "title": "Code Detective",
        "description": "Have Claude search your codebase",
        "hint": "Ask Claude to find something: \"find all TODO comments\" or \"where is the login function?\"",
        "detect": "tool:Grep|Glob",
    },
    "project-memory": {
        "tier": "beginner",
        "title": "Ground Rules",
        "description": "Create a CLAUDE.md file to give Claude project instructions",
        "hint": "Run `/init` to create a CLAUDE.md, or ask Claude to create one for your project",
        "detect": "claude-md-exists",
    },
    "session-counter-3": {
        "tier": "beginner",
        "title": "Regular",
        "description": "Start 3 separate Claude Code sessions",
        "hint": "Keep using Claude Code across different sessions — you're building a habit!",
        "detect": "session-count:3",
    },
    "multi-tool": {
        "tier": "beginner",
        "title": "Multi-Tool",
        "description": "Use 4 different tool types in a single session",
        "hint": "In one conversation, have Claude read, edit, search, and run a command",
        "detect": "tools-in-session:4",
    },
    "five-prompts": {
        "tier": "beginner",
        "title": "Conversationalist",
        "description": "Have a back-and-forth conversation with 5+ turns in one session",
        "hint": "Keep the conversation going — ask follow-ups, refine requests, dig deeper",
        "detect": "stop-count:5",
    },

    # ── Intermediate ──────────────────────────────────────────────────────
    "web-researcher": {
        "tier": "intermediate",
        "title": "Web Wanderer",
        "description": "Have Claude search the web or fetch a URL",
        "hint": "Ask Claude to research something: \"look up the latest React docs for useEffect\"",
        "detect": "tool:WebSearch|WebFetch",
    },
    "subagent-user": {
        "tier": "intermediate",
        "title": "Delegation Master",
        "description": "Have Claude spawn a subagent to handle a task",
        "hint": "Ask Claude to explore your codebase or plan an implementation — it will use subagents for complex research",
        "detect": "tool:Agent",
    },
    "session-counter-10": {
        "tier": "intermediate",
        "title": "Power User",
        "description": "Start 10 separate Claude Code sessions",
        "hint": "You're becoming a regular — keep going!",
        "detect": "session-count:10",
    },
    "multi-file-edit": {
        "tier": "intermediate",
        "title": "Refactorer",
        "description": "Have Claude edit 3 or more different files in one session",
        "hint": "Ask for a change that spans multiple files: \"rename the User class to Account everywhere\"",
        "detect": "unique-edits:3",
    },
    "long-session": {
        "tier": "intermediate",
        "title": "Deep Work",
        "description": "Have a session with 15+ turns",
        "hint": "Tackle a meaty task — build a feature, debug a tricky issue, or do a thorough review",
        "detect": "stop-count:15",
    },
    "rules-creator": {
        "tier": "intermediate",
        "title": "Rule Writer",
        "description": "Create a .claude/rules/ file with path-specific instructions",
        "hint": "Create `.claude/rules/testing.md` with frontmatter like `paths: [\"tests/**\"]` to give Claude context-specific rules",
        "detect": "rules-dir-exists",
    },
    "git-workflow": {
        "tier": "intermediate",
        "title": "Git Apprentice",
        "description": "Have Claude run a git commit",
        "hint": "After making changes, ask Claude to \"commit these changes\" — it handles staging and message writing",
        "detect": "bash-pattern:git commit",
    },
    "test-runner": {
        "tier": "intermediate",
        "title": "Quality Guard",
        "description": "Have Claude run your test suite",
        "hint": "Ask Claude to \"run the tests\" or \"check if the tests pass\"",
        "detect": "bash-pattern:test",
    },
    "compact-user": {
        "tier": "intermediate",
        "title": "Context Ninja",
        "description": "Let Claude know you understand context management by mentioning /compact or /context",
        "hint": "When your session gets long, use `/compact` to compress the conversation or `/context` to check usage",
        "detect": "context-awareness",
    },
    "skill-invoker": {
        "tier": "intermediate",
        "title": "Skill Seeker",
        "description": "Invoke the /achievements skill to check your progress",
        "hint": "Type `/achievements` to see your current achievement progress!",
        "detect": "achievements-invoked",
    },
}

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """Return the plugin data directory, creating it if needed."""
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if not data_dir:
        # Fallback for local testing
        data_dir = os.path.expanduser("~/.claude/plugins/onboarding")
    p = Path(data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_state() -> dict:
    """Load achievement state from disk."""
    state_file = get_data_dir() / "achievements.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "unlocked": {},          # id -> {timestamp, session_id}
        "session_count": 0,
        "current_session": {
            "id": "",
            "tools_used": [],    # unique tool names
            "files_edited": [],  # unique file paths
            "stop_count": 0,
            "bash_commands": [],
        },
    }


def save_state(state: dict) -> None:
    """Persist achievement state to disk."""
    state_file = get_data_dir() / "achievements.json"
    state_file.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Achievement checking
# ---------------------------------------------------------------------------

def check_and_unlock(state: dict, achievement_id: str, session_id: str) -> bool:
    """Unlock an achievement if not already unlocked. Returns True if newly unlocked."""
    if achievement_id in state["unlocked"]:
        return False
    state["unlocked"][achievement_id] = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
    }
    return True


def evaluate_achievements(state: dict, event: str, hook_input: dict) -> list[str]:
    """Evaluate which achievements should be unlocked given current state and event."""
    newly_unlocked = []
    session_id = hook_input.get("session_id", "unknown")
    session = state["current_session"]
    cwd = hook_input.get("cwd", os.getcwd())

    for aid, adef in ACHIEVEMENTS.items():
        if aid in state["unlocked"]:
            continue

        detect = adef["detect"]
        unlocked = False

        # Session start
        if detect == "session-start" and event == "session-start":
            unlocked = True

        # Tool usage
        elif detect.startswith("tool:"):
            tools = detect.split(":", 1)[1].split("|")
            if any(t in session["tools_used"] for t in tools):
                unlocked = True

        # Session count
        elif detect.startswith("session-count:"):
            threshold = int(detect.split(":")[1])
            if state["session_count"] >= threshold:
                unlocked = True

        # Tools in session (unique count)
        elif detect.startswith("tools-in-session:"):
            threshold = int(detect.split(":")[1])
            if len(session["tools_used"]) >= threshold:
                unlocked = True

        # Stop count (proxy for conversation turns)
        elif detect.startswith("stop-count:"):
            threshold = int(detect.split(":")[1])
            if session["stop_count"] >= threshold:
                unlocked = True

        # Unique files edited
        elif detect.startswith("unique-edits:"):
            threshold = int(detect.split(":")[1])
            if len(session["files_edited"]) >= threshold:
                unlocked = True

        # CLAUDE.md exists
        elif detect == "claude-md-exists":
            if (Path(cwd) / "CLAUDE.md").exists() or (Path(cwd) / ".claude" / "CLAUDE.md").exists():
                unlocked = True

        # .claude/rules/ exists
        elif detect == "rules-dir-exists":
            rules_dir = Path(cwd) / ".claude" / "rules"
            if rules_dir.is_dir() and any(rules_dir.iterdir()):
                unlocked = True

        # Bash command pattern
        elif detect.startswith("bash-pattern:"):
            pattern = detect.split(":", 1)[1]
            if any(pattern in cmd for cmd in session["bash_commands"]):
                unlocked = True

        # Context awareness (detected at stop — Claude mentioned compact/context)
        elif detect == "context-awareness":
            last_msg = hook_input.get("last_assistant_message", "")
            if "/compact" in last_msg or "/context" in last_msg or "context window" in last_msg.lower():
                unlocked = True

        # Achievements invoked (set externally by the skill)
        elif detect == "achievements-invoked":
            # Checked via a marker file the skill creates
            marker = get_data_dir() / ".achievements-invoked"
            if marker.exists():
                unlocked = True

        if unlocked and check_and_unlock(state, aid, session_id):
            newly_unlocked.append(aid)

    return newly_unlocked


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def handle_session_start(hook_input: dict) -> None:
    """Handle SessionStart hook event."""
    state = load_state()
    session_id = hook_input.get("session_id", f"session-{int(time.time())}")

    # Increment session count on fresh startup (not resume/compact)
    source = hook_input.get("source", "startup")
    if source == "startup":
        state["session_count"] = state.get("session_count", 0) + 1

    # Reset current session tracking
    state["current_session"] = {
        "id": session_id,
        "tools_used": [],
        "files_edited": [],
        "stop_count": 0,
        "bash_commands": [],
    }

    newly = evaluate_achievements(state, "session-start", hook_input)
    save_state(state)
    announce(state, newly)


def handle_tool_use(hook_input: dict) -> None:
    """Handle PostToolUse hook event."""
    state = load_state()
    session = state["current_session"]

    tool_name = hook_input.get("tool_name", "")

    # Track unique tools
    if tool_name and tool_name not in session["tools_used"]:
        session["tools_used"].append(tool_name)

    # Track edited files
    tool_input = hook_input.get("tool_input", {})
    if tool_name in ("Edit", "Write"):
        fpath = tool_input.get("file_path", "")
        if fpath and fpath not in session["files_edited"]:
            session["files_edited"].append(fpath)

    # Track bash commands
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if cmd:
            session["bash_commands"].append(cmd)

    newly = evaluate_achievements(state, "tool-use", hook_input)
    save_state(state)
    announce(state, newly)


def handle_stop(hook_input: dict) -> None:
    """Handle Stop hook event."""
    state = load_state()
    session = state["current_session"]

    # Don't re-trigger on stop hook's own stop
    if hook_input.get("stop_hook_active", False):
        return

    session["stop_count"] = session.get("stop_count", 0) + 1

    newly = evaluate_achievements(state, "stop", hook_input)
    save_state(state)
    announce(state, newly)


def handle_show() -> None:
    """Show current achievement progress (called by the skill)."""
    state = load_state()

    # Mark the achievements-invoked marker
    marker = get_data_dir() / ".achievements-invoked"
    marker.touch()

    # Re-evaluate in case the marker unlocks something
    newly = evaluate_achievements(state, "show", {"session_id": "manual"})
    save_state(state)

    print(format_progress(state, newly))


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def announce(state: dict, newly_unlocked: list[str]) -> None:
    """Print newly unlocked achievements as JSON context for Claude."""
    if not newly_unlocked:
        return

    announcements = []
    for aid in newly_unlocked:
        adef = ACHIEVEMENTS[aid]
        announcements.append(
            f"Achievement unlocked: {adef['title']} — {adef['description']}"
        )

    total = len(ACHIEVEMENTS)
    done = len(state["unlocked"])
    tier_counts = get_tier_counts(state)

    msg_parts = ["\n".join(announcements)]
    msg_parts.append(f"\nProgress: {done}/{total} achievements unlocked")
    for tier, (complete, of_total) in tier_counts.items():
        msg_parts.append(f"  {tier.title()}: {complete}/{of_total}")

    # Find next hint
    hint = get_next_hint(state)
    if hint:
        msg_parts.append(f"\nNext up: {hint}")

    output = {
        "systemMessage": "\n".join(msg_parts),
    }
    print(json.dumps(output))


def get_tier_counts(state: dict) -> dict:
    """Return {tier: (unlocked, total)} counts."""
    counts = {}
    for aid, adef in ACHIEVEMENTS.items():
        tier = adef["tier"]
        if tier not in counts:
            counts[tier] = [0, 0]
        counts[tier][1] += 1
        if aid in state["unlocked"]:
            counts[tier][0] += 1
    return {t: tuple(c) for t, c in counts.items()}


def get_next_hint(state: dict) -> str | None:
    """Return a hint for the next locked achievement, preferring the current tier."""
    for tier in ("beginner", "intermediate"):
        for aid, adef in ACHIEVEMENTS.items():
            if adef["tier"] == tier and aid not in state["unlocked"]:
                return f"{adef['title']} — {adef['hint']}"
    return None


def format_progress(state: dict, newly_unlocked: list[str]) -> str:
    """Format full progress report for the /achievements command."""
    lines = []
    total = len(ACHIEVEMENTS)
    done = len(state["unlocked"])

    # Progress bar
    bar_len = 20
    filled = int(bar_len * done / total) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    lines.append(f"# Achievement Progress  [{bar}] {done}/{total}\n")

    for tier in ("beginner", "intermediate"):
        tier_achievements = {k: v for k, v in ACHIEVEMENTS.items() if v["tier"] == tier}
        tier_done = sum(1 for k in tier_achievements if k in state["unlocked"])
        tier_total = len(tier_achievements)

        lines.append(f"## {tier.title()} ({tier_done}/{tier_total})\n")

        for aid, adef in tier_achievements.items():
            if aid in state["unlocked"]:
                ts = state["unlocked"][aid]["timestamp"]
                date_str = ts[:10]
                new_tag = " ← NEW!" if aid in newly_unlocked else ""
                lines.append(f"  ✅ **{adef['title']}** — {adef['description']} (unlocked {date_str}){new_tag}")
            else:
                lines.append(f"  🔒 **{adef['title']}** — {adef['description']}")
                lines.append(f"     💡 {adef['hint']}")

        lines.append("")

    # Stats
    lines.append("## Stats\n")
    lines.append(f"  Sessions started: {state.get('session_count', 0)}")
    session = state.get("current_session", {})
    lines.append(f"  Tools used this session: {', '.join(session.get('tools_used', [])) or 'none yet'}")
    lines.append(f"  Files edited this session: {len(session.get('files_edited', []))}")
    lines.append(f"  Turns this session: {session.get('stop_count', 0)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: achievement-tracker.py <session-start|tool-use|stop|show>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    # Read hook input from stdin (hooks pass JSON on stdin)
    hook_input = {}
    if not sys.stdin.isatty():
        try:
            raw = sys.stdin.read()
            if raw.strip():
                hook_input = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            pass

    if command == "session-start":
        handle_session_start(hook_input)
    elif command == "tool-use":
        handle_tool_use(hook_input)
    elif command == "stop":
        handle_stop(hook_input)
    elif command == "show":
        handle_show()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
