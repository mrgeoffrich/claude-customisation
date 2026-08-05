---
name: repo-docs-setup
description: Sets up and maintains the core documentation files of a code repository — CLAUDE.md, ARCHITECTURE.md, TESTING.md, RELEASE.md and HOSTING.md — working out what belongs in each and relocating misplaced content to its proper home. Use this whenever the user wants to document a repo for humans or agents, asks to create or clean up any of these files, says their CLAUDE.md has grown bloated or is being ignored, wants to write down how the codebase is structured, how it gets tested, how a release is cut, or where the app is hosted and how it gets deployed, or asks about onboarding docs, agent instructions, or repo documentation structure — even when they only name one of the five files. Also use it to strip a CLAUDE.md of content that has rotted or will: stale numbers like test counts, coverage percentages and pinned versions; historical narration like migration notes, "we used to use X" and "recently added"; and per-package detail that should be pushed down into a nested CLAUDE.md in that project's own folder.
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
metadata:
  category: documentation
---

# Repository documentation setup

Five documents carry a repository's working knowledge: `CLAUDE.md`, `ARCHITECTURE.md`, `TESTING.md`, `RELEASE.md`, `HOSTING.md`. This skill works out which of them a given repo needs, what goes in each, and what should be pulled out into somewhere else entirely.

Most repos don't warrant all five. Deciding which to skip is as much of the job as writing the ones that stay.

## Why the split exists

`CLAUDE.md` is loaded into every agent session and skimmed by every new contributor on day one, so everything in it is paid for continuously — in context tokens, in reading time, and in dilution (a long file gets followed less reliably than a short one; Anthropic's own guidance targets under 200 lines). The other four are read on demand, at the moment someone needs to find a component, add a test, cut a release, or work out where the thing runs.

So the routing principle is: **`CLAUDE.md` holds only what's needed in *every* session. Everything durable but occasional goes in one of the other four. Everything else goes somewhere outside these five.**

A corollary worth internalising: pointing at the other files with plain markdown links (`See ARCHITECTURE.md`) is what you want. Claude Code's `@path` import syntax expands the target into context at launch, which defeats the entire point — an `@ARCHITECTURE.md` import costs exactly as much as pasting the file in. Use `@`-imports only when the content genuinely must be present every session.

## The rule that matters most: don't invent

You are not verifying anything by running it. That makes sourcing discipline the difference between a useful document and an actively harmful one — a `RELEASE.md` describing a release process this repo doesn't have is worse than no `RELEASE.md`, because people will follow it.

So: every command, path, module name and claim you write must trace to something you actually read in this repository. When you can't determine something, say so in the document rather than filling the gap with what a repo like this usually does:

```markdown
<!-- TODO: confirm — no release automation found in .github/workflows/;
     tags v0.1.0–v0.4.2 exist but the tagging command wasn't documented anywhere -->
```

An HTML comment is the right container for these in `CLAUDE.md` specifically, because Claude Code strips block-level HTML comments before loading the file — the note reaches human maintainers at zero context cost. In the other four files, a visible `> **TODO:**` blockquote is better, since those are read by people.

At the end, tell the user plainly which parts are inferred and need a human eye. That list is often the most valuable thing you hand back.

## Workflow

### 1. Survey the repository

Read before you write. You are looking for evidence, not impressions.

- **Shape**: root listing; monorepo markers (`pnpm-workspace.yaml`, `package.json` workspaces, `turbo.json`, `nx.json`, `lerna.json`, Cargo `[workspace]`, `go.work`, `pyproject.toml` with sub-packages, Gradle `settings.gradle`, `.sln`). A monorepo changes every one of the five documents. Note the project boundaries as you go — they're what step 4 pushes content down into, and the workspace config is a more reliable source for them than the directory names.
- **Commands**: `package.json` scripts, `Makefile`, `justfile`, `Taskfile.yml`, `pyproject.toml` / `tox.ini` / `noxfile.py`, `Cargo.toml`, `go.mod`, `composer.json`, `mise.toml`, `.tool-versions`.
- **CI**: `.github/workflows/*`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`. CI is the most reliable source of truth in the repo — it's the one place where commands are known to work, because they run.
- **Tests**: test directories and file-naming patterns, test runner config, fixtures, `docker-compose*.yml` used by tests, coverage config and thresholds.
- **Releases**: `git tag --sort=-creatordate | head -20`, `git log --oneline -30` (do commits follow Conventional Commits?), release automation config (`release-please-config.json`, `.releaserc`, `.changeset/`, `cliff.toml`, `semantic-release` in devDeps), publish steps in CI, `CHANGELOG.md` format.
- **Hosting**: platform config (`vercel.json`, `netlify.toml`, `fly.toml`, `render.yaml`, `railway.json`, `app.yaml`, `Procfile`, `wrangler.toml`/`.jsonc`), infrastructure as code (`*.tf`, `terraform/`, CDK app, `template.yaml`, `serverless.yml`, `*.bicep`, Pulumi), container and orchestration config (`Dockerfile`, `docker-compose.prod.yml`, `k8s/`, `helm/`, `kustomization.yaml`), deploy jobs in CI and their `environment:` keys, `.env.example`. Also check whether `README.md` links to a dashboard or a separate infra repo — hosting is the one subject that routinely lives outside the repo entirely.
- **Existing docs**: `README.md`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/`, `.claude/rules/`, `.cursorrules`, `.github/copilot-instructions.md`.

For a large repo, sample rather than exhaustively read — the goal is a correct coarse-grained picture, not a complete one.

### 2. Decide which files this repo warrants

A stub file nobody maintains is worse than no file: it looks authoritative and goes stale silently. Propose a file only when the repo has something real to put in it.

| File | Warranted when | Skip when |
|---|---|---|
| `CLAUDE.md` | Essentially always — any repo an agent will work in | Never skip, but keep it tiny for a small repo |
| `ARCHITECTURE.md` | More than one component, service, package or deployable; or non-obvious internal structure; or shared code that constrains how things may depend on each other | Single small module where the file tree *is* the architecture |
| `TESTING.md` | Tests exist across more than one layer or project, or there's setup a newcomer wouldn't guess (containers, seeded data, env vars) | One test dir, one runner, `npm test` and you're done — a line in `CLAUDE.md` covers it |
| `RELEASE.md` | The repo ships a *version*: tags, GitHub releases, a published package or image | Nothing is versioned or published; no tags, no registry |
| `HOSTING.md` | The repo *runs* somewhere: a deployed app or service, environments, infrastructure config, a deploy job in CI | A library, CLI or config repo that's published but never deployed; nothing runs anywhere the team owns |

`RELEASE.md` and `HOSTING.md` are commonly confused, and a repo can warrant either, both, or neither. The split is that a release makes a version *exist*; hosting is where it *runs* and how it gets there. A library published to npm has releases and no hosting. A web app on continuous deploy has hosting and, often, no release process worth documenting — merging is the whole ceremony. If a single pipeline genuinely covers both, write one file under whichever name the team uses and link across from the other rather than splitting a process nobody experiences as two things. `references/hosting-md.md` has the full boundary table.

If a repo doesn't warrant a file, say why rather than silently omitting it — the user may know about a release or deploy process that leaves no trace in the repo. Hosting especially: it's the one most likely to live in a separate infra repo or entirely in a platform dashboard, so absence of evidence here is weak evidence of absence. Ask rather than concluding.

### 3. Triage what's already there

If `CLAUDE.md` (or `AGENTS.md`) already exists, read it and classify every section against the placement table below. This is usually where most of the value is: existing agent-instruction files accumulate architecture notes, testing lore and deploy steps that nobody ever moved out.

Sweep the same pass for the two things that rot in place rather than sitting in the wrong file — both covered in "Keeping the documents honest" below:

- **Brittle values.** Every number in an existing `CLAUDE.md` is a claim that was true on the day someone typed it. Check each against the repo, then strike it or restate it in a form that stays true.
- **Historical narration.** Anything phrased as *what changed* rather than *what is* — migrations, rewrites, "recently", "we used to", "as of v2". Rewrite it in the present tense or cut it.

Both are easy to miss because they read as informative rather than as clutter, and neither shows up as a section you'd think to move.

Note also that Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If the repo has `AGENTS.md` and no `CLAUDE.md`, don't duplicate the content — create a `CLAUDE.md` whose first line is `@AGENTS.md`, then add Claude-specific content beneath it.

### 4. Push project-specific content down

Splitting content across the five documents is only one of the two axes. The other is *depth*: in any repo with more than one project — a monorepo, a workspace, `apps/` and `packages/`, a `backend/` and `frontend/` pair, a repo with a subdirectory that's really its own thing — instructions that apply to exactly one of them do not belong in the root file.

The mechanics make this worth doing. Claude Code concatenates the `CLAUDE.md` files from the working directory up to the repo root at launch, and loads *nested* ones on demand, when Claude reads files in that directory. So a rule sitting in `apps/api/CLAUDE.md`:

- costs nothing in sessions that never touch `apps/api`
- loads automatically as soon as Claude opens a file there
- loads at launch anyway for someone working from inside `apps/api`, which is how people work on one package

Root-level content, by contrast, is paid for by every session in the repo regardless of what it's about. In a monorepo that's the single biggest source of bloat: the root file ends up holding the union of every package's quirks, and each session pays for all of them to get the one that's relevant.

**Do the pass like this.** For each project directory, ask what a session working *only* there needs, and what a session working *anywhere else* would be paying for needlessly:

| Signal it belongs in the child | Signal it stays at the root |
|---|---|
| Names one package's paths, scripts or config | Applies across packages, or to the workspace itself |
| A framework convention true only of that stack (the Next.js app's routing rules, the Rust crate's feature flags) | The package manager, the commit convention, the "never edit `gen/`" rule |
| That project's own build/test/run commands | How to scope any command to one package |
| Env vars, ports, seed data specific to that service | Shared tooling everyone hits |
| An agent working elsewhere would never act on it | An agent needs it to interpret anything in the repo |

A child file should be short and follow the same rules as the root — same falsifiable-rules bar, same no-brittle-values and present-tense rules, plus its own commands. Don't repeat what the root already says; the root is loaded too, and the child is read after it.

Two cautions. Don't create a child file per directory as a matter of course — one per *project* (something with its own build, test cycle or deployable), not one per folder; a `CLAUDE.md` in `src/utils/` is noise. And when the content is a rule about a subtree rather than orientation for working in it, `.claude/rules/*.md` with `paths:` frontmatter is the better instrument — it targets file globs rather than directories and applies whenever matching files are touched from anywhere.

If nothing in the root file is project-specific, say so and skip the step rather than manufacturing a split.

### 5. Propose, then confirm

Show the user, briefly:

- which of the five files you'll create or edit, and which you're skipping with the reason
- what you'll move *out* of any existing `CLAUDE.md`, and where each piece is going
- which per-project `CLAUDE.md` files you'll create, and what moves down into each
- anything you plan to delete outright (with justification — see the table)
- what you couldn't determine and will mark TODO

Get agreement before writing. Moving someone's documentation around without asking is the kind of change that's annoying to undo. If there's a genuine fork — say, the repo has both a `Makefile` and npm scripts and you can't tell which is canonical — ask.

### 6. Write

Read the reference for each file as you write it. They contain the section-by-section guidance and a template:

- `references/claude-md.md` — purpose, commands, repo-wide rules, links; what to keep out (brittle values, history); nested per-project files; plus Claude Code specifics (`.claude/rules/`, path-scoped rules, `CLAUDE.local.md`, imports)
- `references/architecture-md.md` — bird's-eye view, codemap, component relationships, shared-library rules, cross-cutting concerns, invariants and gotchas
- `references/testing-md.md` — test layers per project, where tests live, how to run them, and the post-change smoke test
- `references/release-md.md` — versioning, the release command sequence, changelog policy, artifacts, hotfix and rollback
- `references/hosting-md.md` — environments, what runs where, provisioning, deploy triggers, config and secrets, rollback; and the boundary with `RELEASE.md`
- `references/elsewhere.md` — where content goes when it belongs in none of the five (ADRs, `CONTRIBUTING.md`, path-scoped rules, skills, runbooks, module READMEs)

Match the repo's existing documentation voice and formatting where it has one.

### 7. Report

State what was written, what moved where — including anything pushed down into a per-project `CLAUDE.md` — and the list of gaps you marked TODO. Suggest `/init` afterwards only if a `CLAUDE.md` didn't previously exist and the user wants Claude's own read on it.

## Placement table

This is the core of the skill: given a piece of knowledge, where does it live?

| Content | Home | Why |
|---|---|---|
| What this repo is and who it's for (1 paragraph) | `CLAUDE.md` | Needed to interpret everything else, every session |
| Build, test, lint, typecheck, run commands | `CLAUDE.md` | Typed constantly; the highest-value lines in the file |
| Repo-wide conventions that differ from tool defaults ("pnpm not npm", "never edit `gen/`") | `CLAUDE.md` | Cheap to state, expensive to get wrong |
| Links to the other four documents | `CLAUDE.md` | Plain markdown links, not `@`-imports |
| Commands, conventions or quirks true of exactly one package or service | That project's own `<path>/CLAUDE.md` | Loads on demand when Claude works there, and at launch for someone working from inside it — free for every other session |
| How to scope a command to one package in a monorepo | Root `CLAUDE.md` | The one piece of per-package knowledge every session needs |
| Directory tree, file listings, dependency lists | **Delete** | Derivable in seconds with `ls`/`Glob`; goes stale immediately |
| Counts, sizes and versions — "47 tests", "92% coverage", "~8k LOC", "Node 20.11.1", "12 packages" | **Delete**, or restate qualitatively | True the day it was typed, wrong within weeks, and nothing fails when it drifts |
| What changed and when — migrations, rewrites, "recently added", "we used to use X" | **Rewrite in the present tense**, or delete | `CLAUDE.md` states what is true now; git history and `CHANGELOG.md` already record what happened, with dates attached |
| A past decision that still constrains what you may do today | `ARCHITECTURE.md` gotchas (or `CLAUDE.md` if repo-wide) | Stated as a live constraint, not as an event: it changes what someone does now |
| What each component does and how they relate | `ARCHITECTURE.md` | Read when navigating, not every session |
| Which module owns what; where to make a given change | `ARCHITECTURE.md` | This is the codemap's whole job |
| Shared-library rules, allowed dependency directions | `ARCHITECTURE.md` | Constraints belong next to the structure they constrain |
| Architectural invariants, especially "must *not*" ones | `ARCHITECTURE.md` | Invisible in code; the highest-value thing in the file |
| Gotchas, historical accidents, why-it's-like-this | `ARCHITECTURE.md` | Prevents "helpful" changes that break things |
| How one module works internally | Module `README.md` or code comments | Too volatile for a repo-level doc |
| Which test layers exist and what each is for here | `TESTING.md` | Needed when writing tests, not before |
| Where tests live, naming, how to run one test | `TESTING.md` | |
| Fixtures, test data, what's mocked vs real | `TESTING.md` | The stuff newcomers get wrong |
| The smoke test to run after a change | `TESTING.md`, with the command echoed in `CLAUDE.md` | The one testing fact worth paying session cost for |
| Versioning scheme, tagging, `gh release`, publish steps | `RELEASE.md` | Occasional, procedural, must be exact |
| Changelog policy and format | `RELEASE.md` | |
| Hotfix path, rollback, yanking a bad release | `RELEASE.md` | Needed under pressure — write it before you need it |
| Which environments exist, their URLs, what each is for | `HOSTING.md` | The orientation a reader needs before any other hosting fact means anything |
| What production runs on; how infrastructure is provisioned | `HOSTING.md` | Occasional, and invisible from the code |
| What triggers a deploy, and how to verify it landed | `HOSTING.md` | The highest-consequence fact in the file — people ship accidents by getting it wrong |
| Whether migrations run automatically or are a separate step | `HOSTING.md` | The most dangerous ambiguity in a deploy |
| Environments that secretly share a database, cache or account | `HOSTING.md` | Nothing in the code reveals it; costs an incident to learn |
| How to roll back what's serving traffic | `HOSTING.md` | Read under pressure; distinct from un-publishing a version |
| Env var and secret *names*, and where they're configured | `HOSTING.md` (or `RELEASE.md` for publish-time ones) | Names and locations only — never values |
| Incident response, on-call, backup and restore | `docs/runbooks/` | Different reader, different urgency than routine deploys |
| Why a design decision was made, alternatives rejected | `docs/adr/NNNN-*.md` | Decisions are dated records; architecture is current state |
| PR process, commit format, code review expectations | `CONTRIBUTING.md` | Aimed at contributors, not at agents mid-task |
| Instructions that only apply to one subtree | `.claude/rules/*.md` with `paths:` frontmatter | Loads on demand when matching files are touched |
| A repeatable multi-step procedure | A skill | Loads only when invoked; can carry scripts |
| Personal preferences, local URLs, sandbox creds | `CLAUDE.local.md` (gitignored) | Not the team's business |
| Secrets and tokens | Secret manager — **never a document** | |
| Aspirational rules with nothing enforcing them | **Delete**, or mark advisory | An unenforced rule trains people to ignore the file |

When something doesn't fit any row, prefer the most specific home that will actually be read, and default to leaving it out of `CLAUDE.md`.

## Keeping the documents honest

Four failure modes to design against as you write:

**Staleness.** Anything that mirrors code (file trees, function names, exact line counts, exhaustive lists) will drift within weeks and nobody will notice. Write at the altitude that survives refactors: name modules and directories, don't link to files or line numbers; describe responsibilities, not signatures. If a sentence would be wrong after a routine refactor, raise its altitude or cut it.

**Brittle values.** The sharpest form of staleness is a number. "The suite has 47 tests", "coverage sits at 92%", "the repo is ~8k lines across 12 packages", "we're on Node 20.11.1", "the build takes 3 minutes" — each is a measurement of a moment, invalidated by the next merge, and nothing anywhere fails when it goes wrong. In `CLAUDE.md` the cost compounds: a stale number is read into every session and treated as current, so an agent will confidently repeat it, or "fix" a suite it thinks has lost tests.

Apply this test as you write, and to every number already in an existing file: **would this still be true after a normal week of merges?** If not, it doesn't go in. The usual offenders:

| Instead of | Write |
|---|---|
| "47 tests across 6 suites" | "Unit tests per package, one E2E suite" — or nothing; `<test cmd>` reports the count |
| "92% coverage" | "Coverage threshold enforced in CI" (`TESTING.md`, only if a threshold is actually configured) |
| "~8,000 lines across 12 packages" | "A pnpm workspace; the deployables are `apps/web` and `apps/api`" |
| "Node 20.11.1, pnpm 9.1.0" | "Node and pnpm versions are pinned in `.nvmrc` / `packageManager`" |
| "The suite takes 3m12s" | "Unit tests take seconds; E2E takes minutes — scope it while iterating" |
| "12 endpoints under `/api/v1`" | "REST endpoints live under `/api/v1`" |

Two things this rule is not. It doesn't ban numbers that a document is the source of truth for — a coverage threshold you're documenting *because* CI enforces it, a supported-version policy, a port number, a required schema version. Those are decisions, not measurements: they change only when someone changes them deliberately, and the doc is where that decision lives. And it doesn't ban orders of magnitude — "seconds" versus "tens of minutes" is what a reader actually needs to decide whether to run something, and it stays true across a year of growth in a way that `3m12s` doesn't.

When a number really is load-bearing, don't retype it — point at whatever holds it ("the threshold is the `coverage` block in `vitest.config.ts`"), so there's one copy and it's the copy that's enforced.

**Audit-log creep.** `CLAUDE.md` describes the repository as it is right now. It is not a changelog, a migration diary or a record of what the team has been up to. Yet it accretes one, because every migration ends with someone adding a line about it and nobody ever deletes those lines:

- "Migrated from Webpack to Vite in March 2025"
- "We used to use `moment`; now it's `date-fns`"
- "Note: the auth rewrite landed in v3, so ignore the old middleware docs"
- "Recently added: the `packages/ui` workspace"
- "Deprecated as of last quarter — will be removed"

Each one costs context in every session to describe a state that no longer exists, and the reader has to work out which half of the sentence is current. "Recently" and "new" rot the fastest: a year on, the new thing is the old thing, and the note now points an agent at exactly the wrong pattern.

The fix is nearly always a rewrite into the present tense, not a deletion — the fact underneath is usually worth keeping, and only the framing is historical:

| Instead of | Write |
|---|---|
| "Migrated from Webpack to Vite in March" | "Vite is the bundler" — or nothing, if `vite.config.ts` makes it obvious |
| "We used to use `moment`; now `date-fns`" | "Use `date-fns` for date handling; don't add `moment`" |
| "Recently added the `packages/ui` workspace" | Name it in `ARCHITECTURE.md`'s codemap like any other package |
| "Deprecated as of last quarter" | "`legacyClient` is deprecated — new call sites use `apiClient`" |
| "Fixed the flaky login test in #482" | Nothing — that's git history |

The exception is history that is still load-bearing *today*: the reason a strange thing must stay strange. "Don't reorder the middleware — the session cookie has to be set before the CSRF check reads it" is a constraint, not a record, and it earns its place (in `ARCHITECTURE.md` under gotchas, or in `CLAUDE.md` if it's a genuine repo-wide prohibition). The test is whether the sentence changes what someone does now. If it only tells them what happened, it belongs in git history, `CHANGELOG.md`, or a dated ADR — all three of which already record it better, with timestamps and authors attached.

**Unfalsifiable filler.** "Write clean, maintainable code" and "follow best practices" occupy space and change no behaviour. Every rule you write should be concrete enough that someone could point at a diff and say whether it complied. If you can't make it falsifiable, it's not a rule — it's a mood, and it should be cut.
