#!/usr/bin/env python3
"""Build or rebuild the cc-sandbox Docker template image.

Checks whether the template is up-to-date by comparing the base image
digest baked into the template against the current base image digest.
Rebuilds only when needed.

Outputs key=value pairs for Claude to parse:
  action=none|built|rebuilt
  image=cc-sandbox:latest
  base_digest=sha256:...

Uses only Python 3 stdlib — no pip dependencies.
"""

import subprocess
import sys
from pathlib import Path

IMAGE_NAME = "cc-sandbox:latest"
BASE_IMAGE = "docker/sandbox-templates:claude-code"
LABEL_KEY = "cc-sandbox.base-digest"


def run(cmd: list[str], timeout: int = 300) -> tuple[int, str]:
    """Run a command and return (returncode, stdout). Never raises."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return 1, ""


def get_base_digest() -> str:
    """Get the current digest of the base image (pulls if needed)."""
    # Pull latest base image
    rc, _ = run(["docker", "pull", BASE_IMAGE], timeout=120)
    if rc != 0:
        # Try without pulling — image may already be local
        pass

    rc, digest = run([
        "docker", "inspect", "--format",
        "{{index .RepoDigests 0}}", BASE_IMAGE,
    ])
    if rc != 0 or not digest:
        # Fallback to image ID if no repo digest
        rc, digest = run([
            "docker", "inspect", "--format", "{{.Id}}", BASE_IMAGE,
        ])
    return digest if rc == 0 else ""


def get_template_base_digest() -> str:
    """Get the base digest label from the existing template image."""
    rc, digest = run([
        "docker", "inspect", "--format",
        f"{{{{index .Config.Labels \"{LABEL_KEY}\"}}}}", IMAGE_NAME,
    ])
    return digest if rc == 0 else ""


def template_exists() -> bool:
    rc, _ = run(["docker", "image", "inspect", IMAGE_NAME])
    return rc == 0


def build(dockerfile_dir: str, base_digest: str) -> bool:
    """Build the template image. Returns True on success."""
    rc, output = run(
        [
            "docker", "build",
            "--build-arg", f"BASE_DIGEST={base_digest}",
            "-t", IMAGE_NAME,
            dockerfile_dir,
        ],
        timeout=300,
    )
    if rc != 0:
        print(f"error={output}", file=sys.stderr)
        return False
    return True


def main() -> None:
    # Dockerfile lives in assets/ relative to this script
    script_dir = Path(__file__).resolve().parent
    dockerfile_dir = str(script_dir.parent / "assets")

    if not Path(dockerfile_dir, "Dockerfile").is_file():
        print(f"error=Dockerfile not found in {dockerfile_dir}", file=sys.stderr)
        sys.exit(1)

    base_digest = get_base_digest()
    if not base_digest:
        print("error=Could not determine base image digest", file=sys.stderr)
        sys.exit(1)

    exists = template_exists()
    if exists:
        template_digest = get_template_base_digest()
        if template_digest == base_digest:
            print("action=none")
            print(f"image={IMAGE_NAME}")
            print(f"base_digest={base_digest}")
            return

        # Base image changed — rebuild
        action = "rebuilt"
    else:
        action = "built"

    print(f"Building {IMAGE_NAME}...")
    if not build(dockerfile_dir, base_digest):
        sys.exit(1)

    print(f"action={action}")
    print(f"image={IMAGE_NAME}")
    print(f"base_digest={base_digest}")


if __name__ == "__main__":
    main()
