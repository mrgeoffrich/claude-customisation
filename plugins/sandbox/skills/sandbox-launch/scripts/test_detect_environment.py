"""Tests for detect-environment.py.

All external commands (docker, git) are mocked so tests run anywhere
without Docker or a git repo.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

# Import the module under test
import importlib.util

spec = importlib.util.spec_from_file_location(
    "detect_environment",
    Path(__file__).parent / "detect-environment.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

run = mod.run
detect_os = mod.detect_os
detect_docker = mod.detect_docker
detect_sandbox = mod.detect_sandbox
detect_credentials = mod.detect_credentials
detect_project = mod.detect_project
detect_package_managers = mod.detect_package_managers
main = mod.main


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


def test_run_success():
    rc, out = run(["echo", "hello"])
    assert rc == 0
    assert out == "hello"


def test_run_missing_command():
    rc, out = run(["__nonexistent_command_xyz__"])
    assert rc == 1
    assert out == ""


def test_run_timeout():
    rc, out = run(["sleep", "10"], timeout=1)
    assert rc == 1
    assert out == ""


# ---------------------------------------------------------------------------
# detect_os()
# ---------------------------------------------------------------------------


def test_detect_os_returns_string():
    result = detect_os()
    assert result in ("Darwin", "Linux", "Windows")


# ---------------------------------------------------------------------------
# detect_docker()
# ---------------------------------------------------------------------------


def _mock_run_docker_full(cmd, **kwargs):
    """Simulates Docker installed, running, with platform info."""
    joined = " ".join(cmd)
    result = subprocess.CompletedProcess(cmd, 0, "", "")
    if cmd == ["docker", "--version"]:
        result.stdout = "Docker version 27.5.1, build 9f9e405"
    elif cmd == ["docker", "info"]:
        result.stdout = "Server Version: 27.5.1"
    elif "Platform" in joined:
        result.stdout = "Docker Desktop 4.40.0 (187762)"
    return result


def _mock_run_docker_not_installed(cmd, **kwargs):
    raise FileNotFoundError("docker not found")


def _mock_run_docker_not_running(cmd, **kwargs):
    result = subprocess.CompletedProcess(cmd, 0, "", "")
    if cmd == ["docker", "--version"]:
        result.stdout = "Docker version 27.5.1, build 9f9e405"
    elif cmd == ["docker", "info"]:
        result.returncode = 1
        result.stderr = "Cannot connect to the Docker daemon"
    return result


def test_detect_docker_full():
    with patch("subprocess.run", side_effect=_mock_run_docker_full):
        info = detect_docker()
    assert info["docker_installed"] is True
    assert info["docker_running"] is True
    assert "27.5.1" in info["docker_version"]
    assert "Docker Desktop" in info["docker_platform"]


def test_detect_docker_not_installed():
    with patch("subprocess.run", side_effect=_mock_run_docker_not_installed):
        info = detect_docker()
    assert info["docker_installed"] is False
    assert info["docker_running"] is False
    assert info["docker_version"] == "none"


def test_detect_docker_not_running():
    with patch("subprocess.run", side_effect=_mock_run_docker_not_running):
        info = detect_docker()
    assert info["docker_installed"] is True
    assert info["docker_running"] is False


# ---------------------------------------------------------------------------
# detect_sandbox()
# ---------------------------------------------------------------------------


def _mock_run_sandbox_available(cmd, **kwargs):
    result = subprocess.CompletedProcess(cmd, 0, "", "")
    if cmd == ["docker", "sandbox", "ls"]:
        result.stdout = "NAME\nmy-project"
    elif cmd == ["docker", "sandbox", "ls", "--format", "{{.Name}}"]:
        result.stdout = "my-project\nother-sandbox"
    return result


def _mock_run_sandbox_unavailable(cmd, **kwargs):
    return subprocess.CompletedProcess(cmd, 1, "", "unknown flag: sandbox")


def test_detect_sandbox_available():
    with patch("subprocess.run", side_effect=_mock_run_sandbox_available):
        info = detect_sandbox()
    assert info["sandbox_available"] is True
    assert info["existing_sandboxes"] == "my-project,other-sandbox"


def test_detect_sandbox_unavailable():
    with patch("subprocess.run", side_effect=_mock_run_sandbox_unavailable):
        info = detect_sandbox()
    assert info["sandbox_available"] is False
    assert info["existing_sandboxes"] == ""


def test_detect_sandbox_available_but_empty():
    def mock(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd == ["docker", "sandbox", "ls", "--format", "{{.Name}}"]:
            result.stdout = ""
        return result

    with patch("subprocess.run", side_effect=mock):
        info = detect_sandbox()
    assert info["sandbox_available"] is True
    assert info["existing_sandboxes"] == ""


# ---------------------------------------------------------------------------
# detect_credentials()
# ---------------------------------------------------------------------------


def test_detect_credentials_all_set():
    env = {"ANTHROPIC_API_KEY": "sk-test", "GITHUB_TOKEN": "ghp-test"}
    with patch.dict(os.environ, env, clear=False):
        info = detect_credentials()
    assert info["api_key_set"] is True
    assert info["github_token_set"] is True


def test_detect_credentials_none_set():
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("GITHUB_TOKEN", None)
    env.pop("GH_TOKEN", None)
    with patch.dict(os.environ, env, clear=True):
        info = detect_credentials()
    assert info["api_key_set"] is False
    assert info["github_token_set"] is False


def test_detect_credentials_gh_token_fallback():
    env = {"GH_TOKEN": "ghp-test"}
    with patch.dict(os.environ, env, clear=True):
        info = detect_credentials()
    assert info["api_key_set"] is False
    assert info["github_token_set"] is True


# ---------------------------------------------------------------------------
# detect_package_managers()
# ---------------------------------------------------------------------------


def test_detect_package_managers_node(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "yarn.lock").write_text("")
    monkeypatch.chdir(tmp_path)
    result = detect_package_managers()
    assert "npm" in result
    assert "yarn" in result


def test_detect_package_managers_python(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("flask")
    monkeypatch.chdir(tmp_path)
    result = detect_package_managers()
    assert result == "pip"


def test_detect_package_managers_multiple(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "go.mod").write_text("")
    monkeypatch.chdir(tmp_path)
    result = detect_package_managers()
    managers = result.split(",")
    assert "npm" in managers
    assert "pip" in managers
    assert "go" in managers


def test_detect_package_managers_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = detect_package_managers()
    assert result == ""


def test_detect_package_managers_cargo(tmp_path, monkeypatch):
    (tmp_path / "Cargo.toml").write_text("")
    monkeypatch.chdir(tmp_path)
    assert detect_package_managers() == "cargo"


def test_detect_package_managers_bundler(tmp_path, monkeypatch):
    (tmp_path / "Gemfile").write_text("")
    monkeypatch.chdir(tmp_path)
    assert detect_package_managers() == "bundler"


# ---------------------------------------------------------------------------
# main() output format
# ---------------------------------------------------------------------------


def test_main_output_format(capsys, tmp_path, monkeypatch):
    """Verify main() outputs valid key=value pairs with boolean formatting."""
    monkeypatch.chdir(tmp_path)

    # Mock all docker/git commands to fail (simplest case)
    def mock_fail(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, "", "")

    with patch("subprocess.run", side_effect=mock_fail):
        main()

    output = capsys.readouterr().out
    lines = [line for line in output.strip().split("\n") if line]

    # Every line should be key=value
    for line in lines:
        assert "=" in line, f"Line missing '=': {line}"
        key, _, value = line.partition("=")
        assert key.isidentifier(), f"Invalid key: {key}"

    # Check expected keys exist
    keys = {line.partition("=")[0] for line in lines}
    assert "os" in keys
    assert "docker_installed" in keys
    assert "sandbox_available" in keys
    assert "api_key_set" in keys
    assert "package_managers" in keys

    # Booleans should be lowercase strings
    kv = dict(line.partition("=")[::2] for line in lines)
    assert kv["docker_installed"] in ("true", "false")
    assert kv["sandbox_available"] in ("true", "false")
    assert kv["api_key_set"] in ("true", "false")
