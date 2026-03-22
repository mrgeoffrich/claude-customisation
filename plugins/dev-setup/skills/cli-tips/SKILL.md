---
name: cli-tips
description: >
  This skill should be used when the user asks about installing, setting up, or authenticating
  CLI developer tools — specifically gws (Google Workspace CLI) initial setup, authentication,
  or installation, or Playwright CLI installation, codegen, UI mode, and test running, or GitHub
  CLI (gh) setup and usage. Also trigger when the user asks what CLI tools are recommended, asks
  about useful developer tools, or says things like "how do I set up gws", "install Playwright",
  "install gh", or "what tools do you use".
  Note: for composing or sending Gmail messages use the gws-gmail-compose skill instead.
---

# CLI Tips

Organised by what kind of work you're doing.

---

## Must-haves (general development)

### GitHub CLI (gh)

The official GitHub CLI — create PRs, manage issues, trigger workflows, and clone repos without leaving the terminal. Essential for any project hosted on GitHub.

#### Install

```bash
# Homebrew (macOS)
brew install gh
```

#### Auth setup

```bash
gh auth login
```

Follow the prompts — it opens a browser to authenticate. After login, `gh` automatically configures git to use HTTPS credentials.

#### Key commands

```bash
# Create a pull request
gh pr create

# List open PRs
gh pr list

# Merge a PR (squash)
gh pr merge --squash

# View PR details
gh pr view <number>

# Create an issue
gh issue create

# List issues
gh issue list

# Trigger a GitHub Actions workflow
gh workflow run <workflow>

# Clone a repo
gh repo clone OWNER/REPO

# See an overview of your open work
gh status
```

---

## Web development & browser automation

### Playwright CLI

Microsoft's end-to-end browser testing framework, supporting Chromium, Firefox, and WebKit. Useful for writing automated tests and for scripting browser interactions (scraping, automation, form filling).

#### Install

```bash
# Quick start (scaffolds a new project)
npm init playwright@latest

# Add to an existing project
npm i -D @playwright/test
npx playwright install
```

#### Key commands

```bash
# Run all tests
npx playwright test

# Run with a visible browser window
npx playwright test --headed

# Run in interactive UI mode (with watch + time-travel debugging)
npx playwright test --ui

# Filter tests by name
npx playwright test -g "login"

# Target a specific browser
npx playwright test --project=firefox

# Debug a specific test with the inspector
npx playwright test --debug

# Record a test by clicking through the browser
npx playwright codegen https://example.com

# Open the HTML test report
npx playwright show-report

# Inspect a trace file (screenshots, DOM snapshots, network)
npx playwright show-trace trace.zip
```

#### Tips

- **`codegen` is the fastest way to write tests** — it records your interactions and generates the test code. Works for TypeScript, JavaScript, Python, Java, and .NET.
- **`--ui` mode** gives you a live test runner with time-travel debugging — great for figuring out why a test is flaky.
- Auto-wait means you rarely need `sleep()` or artificial timeouts; Playwright waits for elements to be ready before acting.
- Tests run in isolated browser contexts that spin up in milliseconds, so parallelism is fast and reliable.
- Requires Node.js 20+.

---

## Google Workspace (Gmail, Calendar, Drive, Sheets)

### Google Workspace CLI (gws)

A unified command-line tool for Google Workspace services — Drive, Gmail, Calendar, Sheets, Docs, and more. Built in Rust, returns structured JSON, and works well with AI agents. Dynamically generates commands from Google's Discovery API, so it always reflects the latest endpoints.

#### Install

```bash
# npm
npm install -g @googleworkspace/cli

# Homebrew
brew install googleworkspace-cli

# Cargo (from source)
cargo install --git https://github.com/googleworkspace/cli --locked
```

#### Auth setup

The interactive setup creates a Google Cloud project for you (requires `gcloud` CLI):

```bash
gws auth setup
```

For re-authentication with specific scopes, use `gws auth login`. The scopes below give access to Gmail, Calendar, and Drive — but note that **`drive.file` is intentionally limited**: it only grants access to files and folders that the app itself creates, not your entire Drive. This is a good security boundary.

```bash
gws auth login --scopes 'https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/calendar,openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile'
```

#### Key commands

```bash
# List Drive files
gws drive files list --params '{"pageSize": 10}'

# Send an email
gws gmail +send --to someone@example.com --subject "Hello" --body "Message"

# View your calendar agenda
gws calendar +agenda

# Append to a spreadsheet
gws sheets +append --spreadsheet SHEET_ID --values "data"
```

Commands prefixed with `+` are helper shortcuts for common workflows. Use `--dry-run` to preview any operation before running it.

Credentials are encrypted at rest with AES-256-GCM backed by the OS keyring.
