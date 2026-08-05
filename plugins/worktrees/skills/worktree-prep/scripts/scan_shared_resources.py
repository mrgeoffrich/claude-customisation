#!/usr/bin/env python3
"""Scan a repository for resources that two concurrent git worktrees would fight over.

Git worktrees isolate *files*. They isolate nothing else. Everything the repo
reaches for outside its own working tree -- a TCP port, a container name, a
sqlite file in the home directory, a lockfile in /tmp, a launchd job, an S3
bucket -- is still a single shared thing that every worktree will grab at once.
This script enumerates those grab points so the isolation design can start from
evidence rather than guesswork.

Usage:
    scan_shared_resources.py [REPO_ROOT] [--json] [--max-per-category N]
                             [--include-ignored]

Output (default): a human-readable report, ordered so the highest-signal
findings come first. With --json: the same data as a JSON document, for
programmatic consumption.

Stdlib only. Cross-platform. Never writes anything.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# --------------------------------------------------------------------------
# What to walk
# --------------------------------------------------------------------------

PRUNE_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "out", "target",
    ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".next", ".nuxt", ".svelte-kit", ".turbo", ".parcel-cache",
    ".gradle", ".idea", ".vscode", "coverage", ".nyc_output", "bin", "obj",
    ".terraform", ".serverless", ".cache", ".playwright-cli", ".pnpm-store",
    "Pods", "DerivedData", ".tox", "site-packages", ".worktrees",
}

# Directories that are worktrees themselves -- scanning them double-reports
# everything in the main checkout.
PRUNE_PATH_SUFFIXES = (
    os.path.join(".claude", "worktrees"),
)

TEXT_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".py", ".rs", ".rb",
    ".java", ".kt", ".cs", ".php", ".swift", ".c", ".h", ".cpp", ".hpp",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1", ".bat", ".cmd",
    ".yml", ".yaml", ".json", ".jsonc", ".toml", ".ini", ".cfg", ".conf",
    ".env", ".properties", ".xml", ".plist", ".service", ".tf", ".tfvars",
    ".md", ".mdx", ".sql", ".tmpl", ".gotmpl", ".hcl", ".gradle", ".make",
}

# Extensionless / oddly-named files that still matter.
TEXT_NAMES = {
    "Dockerfile", "Makefile", "makefile", "GNUmakefile", "Procfile",
    "justfile", "Justfile", "Taskfile", "Caddyfile", "Vagrantfile",
    "docker-compose", "compose", ".env", ".envrc", ".tool-versions",
}

MAX_FILE_BYTES = 512 * 1024

# Files where a finding is near-certainly a real dev-environment resource
# rather than an incidental string, so they sort to the top of the report.
HIGH_SIGNAL_PATTERNS = (
    "docker-compose", "compose.y", "dockerfile", "makefile", "justfile",
    "taskfile", "procfile", "package.json", ".env", "skaffold", "tilt",
    "devcontainer", "vite.config", "next.config", "webpack.config",
    "nodemon.json", "wrangler.", "serverless.", "app.yaml", "fly.toml",
    "launchsettings.json", "settings.py", "config.",
)


# Docs and tests mention ports and paths constantly without ever binding them.
# They still matter -- stale docs are how a hardcoded port survives a migration --
# but they belong at the bottom of the report, not the top.
LOW_SIGNAL_PATTERNS = (
    ".md", ".mdx", "_test.", ".test.", ".spec.", "/testdata/", "/fixtures/",
    "/examples/", "/docs/", "changelog", "readme",
)


def is_high_signal(rel_path: str) -> bool:
    base = os.path.basename(rel_path.lower())
    return any(p in base for p in HIGH_SIGNAL_PATTERNS)


def is_low_signal(rel_path: str) -> bool:
    lowered = rel_path.lower().replace(os.sep, "/")
    return any(p in lowered for p in LOW_SIGNAL_PATTERNS)


# --------------------------------------------------------------------------
# Detection rules
#
# Each rule is (category, compiled regex, why-it-clashes). `capture` names
# which group holds the interesting value; None means use the whole match.
# `files` optionally restricts a rule to filenames containing that substring.
# --------------------------------------------------------------------------

Rule = tuple  # (category, regex, capture_group, file_filter)

RULES: list[Rule] = [
    # ---- Host ports: the first thing that breaks, and the most visible. ----
    ("host-port", re.compile(r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\s*:\s*(\d{2,5})\b"), 1, None),
    ("host-port", re.compile(r"(?i)\b([A-Z][A-Z0-9_]*PORT)\s*[:=]\s*[\"']?(\d{2,5})\b"), 2, None),
    ("host-port", re.compile(r"(?im)^\s*-\s*[\"']?(\d{2,5})\s*:\s*\d{2,5}"), 1, "compose"),
    ("host-port", re.compile(r"(?im)^\s*-\s*[\"']?(\d{2,5})\s*:\s*\d{2,5}"), 1, "docker-compose"),
    ("host-port", re.compile(r"(?i)\bEXPOSE\s+(\d{2,5})"), 1, "dockerfile"),
    ("host-port", re.compile(r"(?i)\.listen\(\s*[\"']?(\d{2,5})"), 1, None),
    ("host-port", re.compile(r"(?i)\b--port[= ](\d{2,5})\b"), 1, None),
    ("host-port", re.compile(r"(?im)^\s*port\s*[:=]\s*[\"']?(\d{2,5})\b"), 1, None),

    # ---- Docker/OCI object names: global per daemon, not per directory. ----
    ("container-name", re.compile(r"(?im)^\s*container_name\s*:\s*[\"']?([^\s\"']+)"), 1, None),
    ("container-name", re.compile(r"(?i)docker\s+run\b[^\n]*?--name[= ]([A-Za-z0-9._-]+)"), 1, None),
    ("container-name", re.compile(r"(?i)\bCOMPOSE_PROJECT_NAME\s*[:=]\s*[\"']?([^\s\"']+)"), 1, None),
    ("container-name", re.compile(r"(?i)docker\s+(?:volume|network)\s+create\s+([A-Za-z0-9._-]+)"), 1, None),
    ("container-name", re.compile(r"(?i)-[pt]\s+([a-z0-9][a-z0-9._/-]*:[a-z0-9._-]+)\b"), 1, "makefile"),

    # ---- Host filesystem outside the repo: shared by definition. ----
    ("host-path", re.compile(r"(?:os\.homedir\(\)|Path\.home\(\)|os\.path\.expanduser|UserHomeDir\(\)|dirs::home_dir)"), 0, None),
    ("host-path", re.compile(r"[\"'](~/[A-Za-z0-9._\-/]+)"), 1, None),
    ("host-path", re.compile(r"\$\{?HOME\}?/([A-Za-z0-9._\-/]+)"), 0, None),
    ("host-path", re.compile(r"(%APPDATA%|%LOCALAPPDATA%|%USERPROFILE%)"), 1, None),
    ("host-path", re.compile(r"\bXDG_(?:CONFIG|DATA|CACHE|STATE)_HOME\b"), 0, None),
    ("host-path", re.compile(r"[\"'](/tmp/[A-Za-z0-9._\-/]+)"), 1, None),
    ("host-path", re.compile(r"[\"'](/var/(?:run|lib|log)/[A-Za-z0-9._\-/]+)"), 1, None),
    ("host-path", re.compile(r"[\"'](/usr/local/(?:var|etc)/[A-Za-z0-9._\-/]+)"), 1, None),

    # ---- Single-holder files: whoever grabs it first wins. ----
    ("lock-socket-pid", re.compile(r"[\"'{$]([A-Za-z0-9._\-/${}~]*\.(?:sock|pid|lock))[\"'}]"), 1, None),
    ("lock-socket-pid", re.compile(r"(?i)\b(flock|LockFile|O_EXLOCK|fcntl\.lockf|proper-lockfile)\b"), 1, None),

    # ---- Stateful stores: cross-contamination is silent, which is worse. ----
    ("datastore", re.compile(r"(?i)\b(DATABASE_URL|DB_NAME|POSTGRES_DB|MYSQL_DATABASE|REDIS_URL|MONGO_URI|MONGODB_URI|DB_PATH)\s*[:=]\s*[\"']?([^\s\"',]+)"), 2, None),
    ("datastore", re.compile(r"[\"']([A-Za-z0-9._\-/${}~]*\.(?:sqlite3?|db))[\"']"), 1, None),
    ("datastore", re.compile(r"(?i)\bredis://[^\s\"']+"), 0, None),
    ("datastore", re.compile(r"(?i)\bpostgres(?:ql)?://[^\s\"']+"), 0, None),

    # ---- Host-global daemons and OS registrations: one per machine. ----
    ("os-service", re.compile(r"(?i)\b(launchctl|launchd|systemctl|systemd|schtasks|sc\.exe create|brew services)\b"), 1, None),
    ("os-service", re.compile(r"[\"']?([A-Za-z0-9._-]+\.(?:plist|service))[\"']?"), 1, None),
    ("os-service", re.compile(r"(?i)(/etc/hosts|dscacheutil|resolvectl)"), 1, None),
    ("os-service", re.compile(r"(?i)\b(colima|minikube|kind\s+create|multipass|lima|wsl\s+--import|vagrant\s+up)\b"), 1, None),
    ("os-service", re.compile(r"(?i)(security add-generic-password|keytar|keyring\.set_password|libsecret|credential[- ]manager)"), 1, None),

    # ---- Namespaces in systems you do not control locally. ----
    ("external-namespace", re.compile(r"(?im)^\s*namespace\s*:\s*[\"']?([A-Za-z0-9._-]+)"), 1, None),
    ("external-namespace", re.compile(r"(?i)\b(bucket|topic|subject|queue_name|stream_name|index_name|table_name)\s*[:=]\s*[\"']([A-Za-z0-9._-]{3,})"), 2, None),
    ("external-namespace", re.compile(r"(?i)\b(ngrok|cloudflared|tailscale funnel|localtunnel)\b"), 1, None),
    ("external-namespace", re.compile(r"(?i)\bs3://([A-Za-z0-9._-]+)"), 1, None),

    # ---- Signals the repo already has worktree tooling to extend, not replace. ----
    ("existing-worktree-tooling", re.compile(r"(?i)\bgit\s+worktree\b"), 0, None),
    ("existing-worktree-tooling", re.compile(r"(?i)worktree[-_](?:env|init|setup|start|delete|list|slot)"), 0, None),
]

CATEGORY_ORDER = [
    "host-port",
    "container-name",
    "datastore",
    "host-path",
    "os-service",
    "lock-socket-pid",
    "external-namespace",
    "existing-worktree-tooling",
]

CATEGORY_BLURB = {
    "host-port": "Bound on the host, so the second worktree gets EADDRINUSE. Offset every one of these by the worktree slot.",
    "container-name": "Docker object names are global per daemon. Prefix with the slug, or set COMPOSE_PROJECT_NAME and drop explicit names entirely.",
    "datastore": "Shared state is the dangerous class: no error, just two worktrees quietly writing to each other's data. Decide per store -- isolate, isolate-and-seed, or declare it shared.",
    "host-path": "Paths outside the working tree are shared by construction. Either move them under the worktree or key them by slug.",
    "os-service": "One per machine. Either run a per-worktree instance (named by slug) or accept it as shared and say so out loud.",
    "lock-socket-pid": "Single-holder resources -- first worktree in wins, the rest fail or hang. Key the path by slug.",
    "external-namespace": "Often cannot be isolated locally. Prefix by slug where the system allows it; where it does not, record it as a known-shared resource so whoever works in the worktree knows their writes are global.",
    "existing-worktree-tooling": "The repo has some worktree support already. Read it before designing anything -- extend it rather than laying a second scheme alongside.",
}


# --------------------------------------------------------------------------
# Repo profile
# --------------------------------------------------------------------------

def profile_repo(root: Path) -> dict:
    def has(*names: str) -> bool:
        return any((root / n).exists() for n in names)

    languages = []
    if has("package.json"):
        languages.append("javascript/typescript")
    if has("go.mod", "go.work"):
        languages.append("go")
    if has("pyproject.toml", "requirements.txt", "setup.py", "Pipfile"):
        languages.append("python")
    if has("Cargo.toml"):
        languages.append("rust")
    if has("Gemfile"):
        languages.append("ruby")
    if has("pom.xml", "build.gradle", "build.gradle.kts"):
        languages.append("jvm")
    if list(root.glob("*.csproj")) or list(root.glob("*.sln")):
        languages.append("dotnet")

    package_manager = None
    for lock, name in (
        ("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"), ("package-lock.json", "npm"),
        ("uv.lock", "uv"), ("poetry.lock", "poetry"),
        ("Pipfile.lock", "pipenv"), ("Cargo.lock", "cargo"),
    ):
        if (root / lock).exists():
            package_manager = name
            break
    if package_manager is None and (root / "package.json").exists():
        # A lockfile may be gitignored or simply absent on a fresh clone; the
        # declared packageManager field is the more reliable signal.
        try:
            declared = json.loads((root / "package.json").read_text(encoding="utf-8", errors="replace"))
            if isinstance(declared.get("packageManager"), str):
                package_manager = declared["packageManager"].split("@")[0] + " (declared)"
        except Exception:
            pass
    if package_manager is None:
        for marker, name in (
            ("go.mod", "go modules"), ("pyproject.toml", "python/pyproject"),
            ("requirements.txt", "pip"), ("Cargo.toml", "cargo"), ("Gemfile", "bundler"),
        ):
            if (root / marker).exists():
                package_manager = name
                break

    compose_files = sorted(
        str(p.relative_to(root))
        for p in list(root.glob("**/docker-compose*.y*ml")) + list(root.glob("**/compose.y*ml"))
        if not any(part in PRUNE_DIRS for part in p.parts)
        and "worktrees" not in p.relative_to(root).parts
    )[:10]

    task_runners = [n for n in ("Makefile", "justfile", "Justfile", "Taskfile.yml", "Taskfile.yaml") if (root / n).exists()]
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8", errors="replace"))
            if isinstance(pkg.get("scripts"), dict):
                task_runners.append("package.json scripts")
        except Exception:
            pass

    agent_docs = [n for n in ("CLAUDE.md", "AGENTS.md", "AGENT.md", ".cursorrules") if (root / n).exists()]

    worktree_dirs = []
    for candidate in (".claude/worktrees", ".worktrees", "worktrees"):
        if (root / candidate).is_dir():
            entries = sorted(p.name for p in (root / candidate).iterdir() if p.is_dir())
            worktree_dirs.append({
                "path": candidate,
                "count": len(entries),
                "existing": entries[:8],
            })

    gitignore = ""
    if (root / ".gitignore").exists():
        gitignore = (root / ".gitignore").read_text(encoding="utf-8", errors="replace")

    return {
        "root": str(root),
        "languages": languages or ["unknown"],
        "package_manager": package_manager,
        "containerised": bool(compose_files) or (root / "Dockerfile").exists(),
        "compose_files": compose_files,
        "dockerfile": (root / "Dockerfile").exists(),
        "task_runners": task_runners,
        "agent_docs": agent_docs,
        "worktree_dirs": worktree_dirs,
        "gitignores_claude_worktrees": "worktrees" in gitignore,
    }


# --------------------------------------------------------------------------
# Walk + match
# --------------------------------------------------------------------------

def should_read(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTS:
        return True
    if path.name in TEXT_NAMES:
        return True
    if path.name.startswith(".env"):
        return True
    if path.name.startswith("Dockerfile"):
        return True
    return False


def walk_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if any(rel_dir.endswith(s) for s in PRUNE_PATH_SUFFIXES):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS and not d.startswith(".git")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if not should_read(p):
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield p


def scan(root: Path, max_per_category: int) -> dict:
    findings: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple] = set()
    port_counter: Counter = Counter()
    files_scanned = 0

    for path in walk_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files_scanned += 1
        rel = str(path.relative_to(root))
        lowered_name = path.name.lower()
        lines = text.splitlines()

        for category, regex, group, file_filter in RULES:
            if file_filter and file_filter not in lowered_name:
                continue
            for m in regex.finditer(text):
                try:
                    value = m.group(group) if group else m.group(0)
                except IndexError:
                    continue
                if not value:
                    continue
                value = value.strip().strip("\"'")
                line_no = text.count("\n", 0, m.start()) + 1
                key = (category, rel, line_no, value)
                if key in seen:
                    continue
                seen.add(key)
                snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                findings[category].append({
                    "file": rel,
                    "line": line_no,
                    "value": value,
                    "snippet": snippet[:180],
                    "high_signal": is_high_signal(rel),
                    "low_signal": is_low_signal(rel),
                })
                if category == "host-port" and value.isdigit():
                    port_counter[int(value)] += 1

    # Rank: dev entrypoints first, docs and tests last, then by file path.
    trimmed: dict[str, dict] = {}
    for category, items in findings.items():
        items.sort(key=lambda f: (not f["high_signal"], f["low_signal"], f["file"], f["line"]))
        trimmed[category] = {
            "total": len(items),
            "shown": items[:max_per_category],
            "truncated": max(0, len(items) - max_per_category),
        }

    distinct_ports = sorted(
        (p for p in port_counter if 1 <= p <= 65535),
        key=lambda p: (-port_counter[p], p),
    )

    return {
        "profile": profile_repo(root),
        "files_scanned": files_scanned,
        "distinct_ports": [{"port": p, "occurrences": port_counter[p]} for p in distinct_ports[:40]],
        "findings": trimmed,
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def render(result: dict) -> str:
    p = result["profile"]
    out: list[str] = []
    add = out.append

    add("=" * 74)
    add("SHARED-RESOURCE SCAN")
    add("=" * 74)
    add(f"repo             : {p['root']}")
    add(f"languages        : {', '.join(p['languages'])}")
    add(f"package manager  : {p['package_manager'] or '(none detected)'}")
    add(f"containerised    : {'yes' if p['containerised'] else 'no'}"
        + (f"  ({', '.join(p['compose_files'][:3])})" if p["compose_files"] else ""))
    add(f"task runners     : {', '.join(p['task_runners']) or '(none detected)'}")
    add(f"agent docs       : {', '.join(p['agent_docs']) or '(none)'}")
    if p["worktree_dirs"]:
        for wd in p["worktree_dirs"]:
            existing = ", ".join(wd["existing"]) or "(empty)"
            if wd["count"] > len(wd["existing"]):
                existing += f", ... ({wd['count']} total)"
            add(f"worktree dir     : {wd['path']} -> {existing}")
    else:
        add("worktree dir     : (none yet)")
    add(f"files scanned    : {result['files_scanned']}")
    add("")

    if result["distinct_ports"]:
        add("-" * 74)
        add("DISTINCT PORTS REFERENCED  (each needs a per-worktree offset)")
        add("-" * 74)
        row = []
        for entry in result["distinct_ports"]:
            row.append(f"{entry['port']} x{entry['occurrences']}")
        for i in range(0, len(row), 6):
            add("  " + "   ".join(row[i:i + 6]))
        add("")

    for category in CATEGORY_ORDER:
        bucket = result["findings"].get(category)
        if not bucket or not bucket["shown"]:
            continue
        add("-" * 74)
        add(f"{category.upper()}  ({bucket['total']} match{'es' if bucket['total'] != 1 else ''})")
        add("-" * 74)
        add(f"  {CATEGORY_BLURB[category]}")
        add("")
        for f in bucket["shown"]:
            marker = "*" if f["high_signal"] else " "
            add(f" {marker} {f['file']}:{f['line']}  ->  {f['value']}")
            if f["snippet"] and f["snippet"] != f["value"]:
                add(f"       {f['snippet']}")
        if bucket["truncated"]:
            add(f"   ... and {bucket['truncated']} more (raise --max-per-category to see them)")
        add("")

    add("=" * 74)
    add("'*' marks findings in dev-entrypoint files -- start there.")
    add("This scan is a starting inventory, not a complete one. Regex cannot see")
    add("resources named at runtime. Read the dev entrypoints yourself and check")
    add("what the app actually binds while it runs.")
    add("=" * 74)
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo_root", nargs="?", default=".", help="repository to scan (default: cwd)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    ap.add_argument("--max-per-category", type=int, default=15, help="findings shown per category (default: 15)")
    args = ap.parse_args(argv)

    root = Path(args.repo_root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    if not (root / ".git").exists():
        print(f"warning: {root} has no .git -- scanning anyway", file=sys.stderr)

    result = scan(root, max(1, args.max_per_category))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
