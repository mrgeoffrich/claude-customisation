---
name: dependabot-fix
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, AskUserQuestion, TodoWrite
description: >
  Fix Dependabot security alerts by updating vulnerable dependencies, running tests, and creating a PR.
  Use this skill when the user asks to fix Dependabot alerts, resolve dependency vulnerabilities,
  update vulnerable packages, handle Dependabot PRs, remediate CVEs in dependencies, or says things
  like "fix dependabot issues", "resolve dependency alerts", "update vulnerable dependencies",
  "fix security alerts", or "handle CVEs". Also triggers for "dependabot", "npm audit fix",
  "fix vulnerable packages", or "patch dependencies".
---

# Dependabot Fix

Automatically fix Dependabot security alerts on a GitHub repository by identifying vulnerable dependencies, applying version updates, verifying the fix with tests and build, then opening a PR.

**Prerequisites**: `gh` CLI authenticated, `git` available, and the relevant package manager installed (npm, pip, etc.).

## Phase 1: Target Repository

**Goal**: Determine which repository to work on and clone it if needed.

**Actions**:
1. Create a todo list to track progress through all phases.
2. Ask the user which repository to fix. Accept one of:
   - **Current directory** — if already inside a git repo with a GitHub remote, use it directly.
   - **GitHub URL or `owner/repo`** — clone it into a temporary working directory.
3. If cloning is required:
   - Run `gh repo clone <owner/repo> /tmp/dependabot-fix-<repo>` (or a platform-appropriate temp path using `python3 -c "import tempfile; print(tempfile.mkdtemp())"`)
   - `cd` into the cloned directory for all subsequent operations.
4. Verify the repo has a GitHub remote: `gh repo view --json nameWithOwner -q .nameWithOwner`
5. Detect the default branch: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name`

---

## Phase 2: Discover Dependabot Alerts

**Goal**: Retrieve and present all open Dependabot alerts for the repository.

**Actions**:
1. Fetch open Dependabot vulnerability alerts:
   ```
   gh api repos/{owner}/{repo}/dependabot/alerts --jq '[.[] | select(.state=="open") | {number, state, dependency: .dependency.package.name, manifest: .dependency.manifest_path, ecosystem: .dependency.package.ecosystem, severity: .security_advisory.severity, summary: .security_advisory.summary, vulnerable_range: .security_vulnerability.vulnerable_version_range, first_patched: .security_vulnerability.first_patched_version.identifier, cve: (.security_advisory.cve_id // "N/A"), ghsa: .security_advisory.ghsa_id, url: .html_url}]'
   ```
2. If no alerts are found, inform the user and stop.
3. Present the alerts in a summary table sorted by severity (critical > high > medium > low):
   ```
   | # | Severity | Package | Vulnerable Range | Fix Version | CVE | Summary |
   ```
4. Ask the user which alerts to fix:
   - **All** — fix every open alert.
   - **By severity** — e.g. "critical and high only".
   - **By number** — e.g. "1, 3, 7".
5. Group the selected alerts by manifest file (e.g. `package.json`, `requirements.txt`, `pom.xml`) — fixes will be applied per manifest.

---

## Phase 3: Fix Dependencies

**Goal**: Apply dependency updates for each selected alert.

**Actions**:
1. Check out a new branch from the default branch:
   ```
   git checkout -b dependabot-fix/<short-description>
   ```
   Use a descriptive branch name based on the alerts being fixed (e.g. `dependabot-fix/update-lodash-express` or `dependabot-fix/critical-vulns-2026-03`).

2. For each manifest file group, apply fixes using the appropriate strategy:

   **npm / yarn / pnpm** (`package.json`):
   - Read `package.json` (and `package-lock.json` if present) to understand current pinned versions.
   - For each alert, update the dependency version in `package.json` to the `first_patched` version or newer using Edit.
   - If the vulnerable dependency is a **transitive** dependency (not in `package.json`), check if a top-level version bump resolves it. If not, add a `resolutions` (yarn) or `overrides` (npm) entry to force the patched version.
   - Run `npm install` (or `yarn install` / `pnpm install`) to regenerate the lockfile.
   - Verify the vulnerability is resolved: `npm audit --json` and confirm the specific CVEs no longer appear.

   **pip** (`requirements.txt`, `setup.py`, `pyproject.toml`):
   - Read the manifest to find the current version constraint.
   - Update the version pin to `>= first_patched_version`.
   - Run `pip install -r requirements.txt` (or equivalent) to verify resolution.
   - If using `pyproject.toml` with optional dependencies, update the appropriate section.

   **Go** (`go.mod`):
   - Run `go get <module>@v<first_patched>` for each vulnerable module.
   - Run `go mod tidy` to clean up.

   **Ruby** (`Gemfile`):
   - Update the version constraint in `Gemfile`.
   - Run `bundle update <gem-name>` to regenerate `Gemfile.lock`.

   **Maven / Gradle** (`pom.xml`, `build.gradle`):
   - Update the `<version>` tag or dependency declaration to the patched version.
   - For Maven: `mvn versions:use-latest-versions` can help with batch updates.

   **Cargo** (`Cargo.toml`):
   - Update the version in `Cargo.toml`.
   - Run `cargo update -p <crate>` to update `Cargo.lock`.

   **General fallback**:
   - If the ecosystem is unrecognized, read the manifest, apply the version bump via Edit, and ask the user to verify.

3. After all updates, stage the changed files:
   ```
   git add <manifest-files> <lockfiles>
   ```

---

## Phase 4: Verify the Fix

**Goal**: Ensure the dependency update does not break the project.

**Actions**:
1. Detect the build and test commands by checking (in order):
   - `CLAUDE.md` or `AGENTS.md` for documented commands.
   - `package.json` scripts (`build`, `test`), `Makefile` targets, `pyproject.toml` scripts, `Cargo.toml`, etc.
   - CI config files: `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile` — extract the build/test steps.
2. Run the **build** command. If it fails:
   - Read the error output carefully.
   - Determine if the failure is caused by the version bump (breaking API change).
   - If the failure is fixable (e.g. a renamed import, changed function signature), apply the code fix.
   - If the failure requires significant refactoring, inform the user and ask how to proceed.
   - Re-run the build to confirm the fix.
3. Run the **test suite**. If tests fail:
   - Analyze failures to distinguish between pre-existing failures and ones caused by the update.
   - Fix test failures caused by the update (e.g. updated API, changed behavior).
   - If tests were already failing before the update, note this in the PR description but do not block on them.
   - Re-run tests to confirm.
4. If both build and tests pass (or pre-existing failures are documented), proceed. Otherwise, ask the user for guidance.

---

## Phase 5: Commit and Create PR

**Goal**: Commit the fix, push the branch, and open a pull request.

**Actions**:
1. Commit all changes with a clear message:
   ```
   git commit -m "fix: update vulnerable dependencies

   Fixes Dependabot alerts: #<alert1>, #<alert2>, ...

   Updated packages:
   - <package>: <old-version> -> <new-version> (CVE-XXXX-YYYY)
   - ...

   Build and tests verified."
   ```
2. Push the branch:
   ```
   git push -u origin dependabot-fix/<branch-name>
   ```
3. Create the PR using `gh`:
   ```
   gh pr create --title "fix: resolve Dependabot security alerts" --body "..."
   ```
   The PR body should include:
   - **Summary** — what was fixed and why.
   - **Alerts resolved** — table of alert numbers, packages, severities, and CVEs, each linking to the alert URL.
   - **Changes made** — list of version bumps and any code changes required for compatibility.
   - **Verification** — confirmation that build and tests pass (or note pre-existing failures).
   - A footer: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

4. Present the PR URL to the user.
5. Optionally, dismiss the corresponding Dependabot alerts via the API if the user requests it:
   ```
   gh api --method PATCH repos/{owner}/{repo}/dependabot/alerts/{number} -f state=dismissed -f dismissed_reason=fix_started
   ```

---

## Error Handling

- **No `gh` CLI**: Tell the user to install and authenticate `gh` (`gh auth login`).
- **No Dependabot access**: The repo may not have Dependabot enabled or the user may lack permissions. Suggest enabling it via `Settings > Code security and analysis > Dependabot alerts`.
- **Rate limiting**: If the GitHub API rate-limits requests, wait and retry, or ask the user to provide a token with higher limits.
- **Merge conflicts**: If the default branch has moved ahead, rebase the fix branch before pushing.
- **Unsupported ecosystem**: If the package ecosystem is not covered above, inform the user and provide manual guidance.
