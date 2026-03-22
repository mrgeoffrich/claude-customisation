#!/usr/bin/env python3
"""Detect Docker environment for the sandbox-launch skill.

Outputs structured key=value pairs for Claude to parse.
Uses only Python 3 stdlib — no pip dependencies.
"""

import os
import platform
import subprocess
from pathlib import Path


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    """Run a command and return (returncode, stdout). Never raises."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return 1, ""


def detect_os() -> str:
    return platform.system()  # Darwin, Linux, Windows


def detect_docker() -> dict:
    info = {
        "docker_installed": False,
        "docker_version": "none",
        "docker_running": False,
        "docker_platform": "none",
    }

    rc, version = run(["docker", "--version"])
    if rc != 0:
        return info

    info["docker_installed"] = True
    info["docker_version"] = version.split("\n")[0] if version else "unknown"

    rc, _ = run(["docker", "info"])
    if rc != 0:
        return info

    info["docker_running"] = True
    rc, plat = run(["docker", "version", "--format", "{{.Server.Platform.Name}}"])
    info["docker_platform"] = plat if rc == 0 and plat else "unknown"

    return info


def detect_sandbox() -> dict:
    info = {"sandbox_available": False, "existing_sandboxes": ""}

    rc, output = run(["docker", "sandbox", "ls"])
    if rc != 0:
        return info

    info["sandbox_available"] = True
    rc, names = run(["docker", "sandbox", "ls", "--format", "{{.Name}}"])
    if rc == 0 and names:
        info["existing_sandboxes"] = ",".join(names.splitlines())

    return info


def _token_in_shell_profile(token_name: str) -> bool:
    """Check if a token is exported in the user's shell profile."""
    home = Path.home()
    for rc in (".zshrc", ".bashrc", ".bash_profile", ".profile"):
        rc_path = home / rc
        if rc_path.is_file():
            try:
                content = rc_path.read_text()
                if f"export {token_name}=" in content:
                    return True
            except OSError:
                continue
    return False


def detect_credentials() -> dict:
    gh_token_env = bool(
        os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    )
    gh_token_profile = _token_in_shell_profile(
        "GH_TOKEN"
    ) or _token_in_shell_profile("GITHUB_TOKEN")
    return {
        "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "github_token_set": gh_token_env,
        "github_token_in_profile": gh_token_profile,
    }


def detect_project() -> dict:
    cwd = Path.cwd()
    info = {
        "project_dir": str(cwd),
        "git_repo": False,
        "git_branch": "",
    }

    rc, _ = run(["git", "rev-parse", "--is-inside-work-tree"])
    if rc == 0:
        info["git_repo"] = True
        rc, branch = run(["git", "branch", "--show-current"])
        info["git_branch"] = branch if rc == 0 and branch else "detached"

    return info


def detect_package_managers() -> str:
    cwd = Path.cwd()
    managers = []

    if (cwd / "package.json").exists():
        managers.append("npm")
    if (cwd / "yarn.lock").exists():
        managers.append("yarn")
    if (cwd / "pnpm-lock.yaml").exists():
        managers.append("pnpm")
    if any(
        (cwd / f).exists() for f in ("requirements.txt", "pyproject.toml", "Pipfile")
    ):
        managers.append("pip")
    if (cwd / "Gemfile").exists():
        managers.append("bundler")
    if (cwd / "go.mod").exists():
        managers.append("go")
    if (cwd / "Cargo.toml").exists():
        managers.append("cargo")
    if (cwd / ".git").is_dir():
        managers.append("github")

    return ",".join(managers)


def main():
    results = {"os": detect_os()}

    docker = detect_docker()
    results.update(docker)

    if docker["docker_running"]:
        results.update(detect_sandbox())
    else:
        results["sandbox_available"] = False
        results["existing_sandboxes"] = ""

    results.update(detect_credentials())
    results.update(detect_project())
    results["package_managers"] = detect_package_managers()

    # Output as key=value pairs (booleans as lowercase strings)
    for key, value in results.items():
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
