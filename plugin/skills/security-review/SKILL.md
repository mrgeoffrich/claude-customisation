---
name: security-review
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

3. Launch each agent with a detailed prompt specifying:
   - The exact categories to review
   - The relevant checklist items from the Category Reference
   - The project-specific context (tech stack, frameworks, key files)
   - Instructions to return findings with severity, confidence, file:line, and the 10 most important files reviewed
4. Run agents in the background when possible to maximize parallelism.

---

## Phase 3: Consolidation & Triage

**Goal**: Merge all agent findings into a single prioritized report.

**Actions**:
1. Collect findings from all completed agents.
2. Deduplicate — if multiple agents report the same issue, keep the most detailed version.
3. Sort by severity (CRITICAL > HIGH > MEDIUM > LOW), then by confidence score descending.
4. For any finding with confidence < 75, briefly verify by reading the referenced code before including in the final report.
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

---

## Category Reference

### Universal Categories (all projects)

**1. Authentication & Credential Management**
- Hardcoded secrets, API keys, tokens in source
- Password hashing algorithm and configuration
- Token generation entropy and lifetime
- OAuth/OIDC implementation correctness
- Credential storage (plaintext, encryption, keyring)
- Multi-factor authentication implementation
- Brute-force protection and account lockout
- Token revocation and session invalidation

**2. Input Validation & Injection**
- SQL injection (parameterized queries, ORM safety)
- Command injection (shell execution with user input)
- Path traversal (directory escape, symlink following)
- Template injection (server-side template engines)
- LDAP/XML/XPath injection
- Deserialization of untrusted data
- Regex denial of service (ReDoS)
- Integer overflow/underflow in security-critical math

**3. Cryptography & Secrets Management**
- Algorithm choices (deprecated: MD5, SHA1, DES, RC4)
- Key size and generation (entropy source quality)
- Nonce/IV reuse in symmetric encryption
- Proper use of authenticated encryption (GCM, ChaCha20-Poly1305)
- Key storage and rotation
- Certificate validation (pinning, chain verification)
- Constant-time comparison for secrets
- Random number generation (CSPRNG vs PRNG)

**4. Error Handling & Information Disclosure**
- Stack traces or debug info in production responses
- Verbose error messages revealing internals (paths, versions, SQL)
- Sensitive data in logs (tokens, passwords, PII)
- Different error responses for valid vs invalid users (enumeration)
- Unhandled exceptions causing undefined behavior
- Error messages containing secrets or credentials

**5. Dependency & Supply Chain**
- Known CVEs in direct dependencies
- Outdated dependencies with security patches available
- Unused dependencies increasing attack surface
- Dependency confusion risk (private package names)
- Lock file integrity and presence
- Post-install scripts in dependencies
- Typosquatting risk on package names

**6. Configuration & Environment**
- Insecure default settings
- Debug mode enabled in production configs
- Environment variable handling for secrets
- File permissions on config and secret files
- .env files or secrets in version control
- Feature flags and kill switches
- CORS configuration permissiveness

### Web Application Categories

**7. XSS & Output Encoding**
- Reflected XSS (user input in HTML response)
- Stored XSS (persisted user content rendered without encoding)
- DOM-based XSS (client-side JavaScript sinks)
- Template engine auto-escaping configuration
- Dangerous APIs: innerHTML, document.write, eval, v-html, dangerouslySetInnerHTML
- SVG/MathML injection vectors
- Content-Type sniffing (X-Content-Type-Options)

**8. CSRF & Session Security**
- CSRF token validation on state-changing requests
- SameSite cookie attribute configuration
- Session fixation protection
- Cookie flags: Secure, HttpOnly, SameSite
- Session timeout and idle timeout
- Session ID entropy and predictability
- Concurrent session controls

**9. CORS & HTTP Security Headers**
- Access-Control-Allow-Origin configuration (wildcard risks)
- Access-Control-Allow-Credentials with permissive origins
- Content-Security-Policy (CSP) presence and strictness
- Strict-Transport-Security (HSTS) configuration
- X-Frame-Options / frame-ancestors CSP directive
- Referrer-Policy configuration
- Permissions-Policy (camera, microphone, geolocation)

**10. Authorization & Access Control**
- Insecure Direct Object References (IDOR)
- Horizontal and vertical privilege escalation
- Missing authorization checks on endpoints
- Role/permission enforcement consistency
- JWT validation (signature, expiry, issuer, audience)
- Path-based authorization bypass (trailing slash, case, encoding)
- GraphQL authorization on nested resolvers

### API / Backend Categories

**11. API Security**
- Rate limiting and throttling
- Mass assignment / over-posting
- Broken Object Level Authorization (BOLA)
- Broken Function Level Authorization (BFLA)
- GraphQL: depth limiting, introspection in production, batching attacks
- Pagination and resource exhaustion
- API versioning and deprecation security
- Request size limits

**12. SSRF & Network Security**
- URL validation before server-side requests
- DNS rebinding protection
- Internal network access from user-supplied URLs
- Redirect following to internal resources
- Cloud metadata endpoint access (169.254.169.254)
- Protocol restrictions (file://, gopher://, dict://)
- Webhook URL validation

**13. Data Exposure & Privacy**
- Over-fetching in API responses (exposing internal fields)
- PII in logs, error messages, URLs
- Sensitive data in GET parameters (logged by proxies)
- Data retention and deletion capabilities
- Backup and cache exposure
- Response filtering based on authorization

### CLI Tool Categories

**14. Command & Path Injection**
- Shell command execution with user-supplied arguments
- Path traversal in file arguments (--input, --output, --config)
- Symlink following and TOCTOU races
- Argument injection via filenames (e.g., `--malicious-flag` as filename)
- Environment variable injection
- Glob injection in file operations

**15. File System Security**
- File permissions on created files (credentials, config, temp)
- Atomic file writes for sensitive data
- Temp file predictability and cleanup
- Directory permissions (0o700 for sensitive dirs)
- File locking for concurrent access
- Secure deletion of sensitive files
- Cache file integrity and permissions

**16. Privilege & Process Security**
- Unnecessary elevated privileges
- Signal handling security
- Process environment sanitization
- Core dump prevention for sensitive operations
- Resource limits (file descriptors, memory)
- Subprocess environment inheritance

### Mobile / Desktop Categories

**17. Local Data Storage**
- Keychain/Keystore usage for secrets
- Plaintext sensitive data on filesystem
- Backup inclusion of sensitive data
- Clipboard data exposure
- Screenshot/screen recording of sensitive views
- Shared preferences/UserDefaults for secrets

**18. Transport & Platform Security**
- Certificate pinning implementation
- Cleartext traffic configuration
- WebView security (JavaScript interface, URL loading)
- Deep link and URI scheme validation
- Inter-process communication security
- Binary protections (obfuscation, anti-tampering)
