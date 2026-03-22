---
name: security-review
allowed-tools: Agent, Glob, Grep, LS, Read, TodoWrite
description: >
  Comprehensive security review of a codebase. Use this skill whenever the user asks for a security audit, security review, vulnerability scan, security assessment, penetration test prep, threat modeling, OWASP check, or wants to find security issues, bugs, or vulnerabilities in their code. Also trigger when the user asks about secrets exposure, injection risks, authentication issues, or says things like "is this code secure?", "check for vulnerabilities", "review security", or "find security problems".
---

# Security Review

Perform a comprehensive security review of the current codebase. Auto-detect the project type and launch parallel security analysis agents covering all relevant attack surface categories.

## Phase 1: Project Detection & Scoping

**Goal**: Identify the project type, tech stack, and relevant security categories.

**Actions**:
1. Create a todo list to track progress through all phases.
2. Read key project files to determine the tech stack:
   - Package manifests: `package.json`, `Cargo.toml`, `go.mod`, `requirements.txt`, `pom.xml`, `Gemfile`, `*.csproj`
   - Config files: `CLAUDE.md`, `AGENTS.md`, `.env.example`, `docker-compose.yml`, `Dockerfile`
   - Entry points: `src/main.*`, `src/index.*`, `src/app.*`, `main.*`
   - Framework indicators: `next.config.*`, `vite.config.*`, `angular.json`, `manage.py`, `Rocket.toml`
3. Classify the project into one or many types:
   - **Web Application** (frontend): React, Vue, Angular, Svelte, Next.js, static sites
   - **API / Backend**: REST, GraphQL, gRPC servers; Express, FastAPI, Actix, Gin, Rails
   - **CLI Tool**: Command-line applications, shell utilities
   - **Library / SDK**: Published packages, reusable modules
   - **Mobile / Desktop**: React Native, Electron, Tauri, Flutter
   - **Infrastructure**: Terraform, CloudFormation, Kubernetes configs, CI/CD
4. Select the relevant investigation categories from the Category Reference below.
5. Present the detected project type, tech stack, and selected categories to the user. Ask if they want to adjust scope or focus on specific areas.

---

## Phase 2: Parallel Security Analysis

**Goal**: Launch focused security review agents in parallel, each covering a subset of categories.

**Actions**:
1. Wait for user confirmation of scope from Phase 1.
2. Partition the selected categories into 3-5 agent assignments, grouping related categories together. Recommended groupings:

   **Agent 1 — Auth & Access Control**:
   - Authentication & Credential Management
   - Authorization & Access Control (if web/API)
   - Session Security (if web)

   **Agent 2 — Input & Injection**:
   - Input Validation & Injection
   - XSS & Output Encoding (if web)
   - SSRF & Network (if API/backend)
   - Command & Path Injection (if CLI)

   **Agent 3 — Crypto, Secrets & Data**:
   - Cryptography & Secrets Management
   - Data Exposure & Privacy
   - Local Data Storage (if mobile/desktop)

   **Agent 4 — Infrastructure & Config**:
   - Dependency & Supply Chain
   - Configuration & Environment
   - HTTP Security Headers & CORS (if web)
   - File System Security (if CLI)

   **Agent 5 — API & Network** (if applicable):
   - API Security (rate limiting, mass assignment, BOLA)
   - Transport Security
   - CSRF (if web)

3. Read `references/category-reference.md` to load the full checklist for the selected categories.
4. Read `agents/security-reviewer.md` — use its contents as the system prompt for every analysis agent you launch.
5. Launch each agent with a detailed prompt specifying:
   - The exact categories to review
   - The relevant checklist items loaded from `references/category-reference.md`
   - The project-specific context (tech stack, frameworks, key files)
   - Instructions to return findings with severity, confidence (integer 0–100: how certain this is a real vulnerability vs. a false positive), file:line, and the 10 most important files reviewed
6. Run agents in the background when possible to maximize parallelism.

---

## Phase 3: Consolidation & Triage

**Goal**: Merge all agent findings into a single prioritized report.

**Actions**:
1. Collect findings from all completed agents.
2. Deduplicate — if multiple agents report the same issue, keep the most detailed version.
3. Sort by severity (CRITICAL > HIGH > MEDIUM > LOW), then by confidence score descending.
4. For any finding with confidence < 75 (out of 100), briefly verify by reading the referenced code before including in the final report.
5. Cross-reference findings against project security guidelines (CLAUDE.md, AGENTS.md) — note where findings violate documented security contracts.

---

## Phase 4: Report

**Goal**: Present a clear, actionable security report.

**Format**:
```
# Security Review Report

## Executive Summary
- Project type and tech stack
- Total findings by severity
- Overall security posture assessment (1-2 sentences)

## Critical & High Findings
[Each with: ID, title, file:line, description, attack scenario, fix]

## Medium Findings
[Same format, condensed]

## Low Findings
[Summary table only]

## Positive Observations
[Security practices done well — acknowledge good patterns]

## Recommended Priority
[Ordered list of fixes by impact/effort ratio]
```

Present the report and ask the user if they want to:
- Deep-dive on any specific finding
- Implement fixes for specific issues
- Generate a checklist for remediation tracking

