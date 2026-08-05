---
name: repo-docs-setup
description: Sets up and maintains the core documentation files of a code repository — CLAUDE.md, ARCHITECTURE.md, TESTING.md and RELEASE.md — working out what belongs in each and relocating misplaced content to its proper home. Use this whenever the user wants to document a repo for humans or agents, asks to create or clean up any of these files, says their CLAUDE.md has grown bloated or is being ignored, wants to write down how the codebase is structured, how it gets tested, or how a release is cut, or asks about onboarding docs, agent instructions, or repo documentation structure — even when they only name one of the four files.
allowed-tools: Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion
metadata:
  category: documentation
---

# Repository documentation setup

Four documents carry a repository's working knowledge: `CLAUDE.md`, `ARCHITECTURE.md`, `TESTING.md`, `RELEASE.md`. This skill works out which of them a given repo needs, what goes in each, and what should be pulled out into somewhere else entirely.

## Why the split exists

`CLAUDE.md` is loaded into every agent session and skimmed by every new contributor on day one, so everything in it is paid for continuously — in context tokens, in reading time, and in dilution (a long file gets followed less reliably than a short one; Anthropic's own guidance targets under 200 lines). The other three are read on demand, at the moment someone needs to find a component, add a test, or cut a release.

So the routing principle is: **`CLAUDE.md` holds only what's needed in *every* session. Everything durable but occasional goes in one of the other three. Everything else goes somewhere outside these four.**

A corollary worth internalising: pointing at the other files with plain markdown links (`See ARCHITECTURE.md`) is what you want. Claude Code's `@path` import syntax expands the target into context at launch, which defeats the entire point — an `@ARCHITECTURE.md` import costs exactly as much as pasting the file in. Use `@`-imports only when the content genuinely must be present every session.

## The rule that matters most: don't invent

You are not verifying anything by running it. That makes sourcing discipline the difference between a useful document and an actively harmful one — a `RELEASE.md` describing a release process this repo doesn't have is worse than no `RELEASE.md`, because people will follow it.

So: every command, path, module name and claim you write must trace to something you actually read in this repository. When you can't determine something, say so in the document rather than filling the gap with what a repo like this usually does:

```markdown
<!-- TODO: confirm — no release automation found in .github/workflows/;
     tags v0.1.0–v0.4.2 exist but the tagging command wasn't documented anywhere -->
```

An HTML comment is the right container for these in `CLAUDE.md` specifically, because Claude Code strips block-level HTML comments before loading the file — the note reaches human maintainers at zero context cost. In the other three files, a visible `> **TODO:**` blockquote is better, since those are read by people.

At the end, tell the user plainly which parts are inferred and need a human eye. That list is often the most valuable thing you hand back.

## Workflow

### 1. Survey the repository

Read before you write. You are looking for evidence, not impressions.

- **Shape**: root listing; monorepo markers (`pnpm-workspace.yaml`, `package.json` workspaces, `turbo.json`, `nx.json`, `lerna.json`, Cargo `[workspace]`, `go.work`, `pyproject.toml` with sub-packages, Gradle `settings.gradle`, `.sln`). A monorepo changes every one of the four documents.
- **Commands**: `package.json` scripts, `Makefile`, `justfile`, `Taskfile.yml`, `pyproject.toml` / `tox.ini` / `noxfile.py`, `Cargo.toml`, `go.mod`, `composer.json`, `mise.toml`, `.tool-versions`.
- **CI**: `.github/workflows/*`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`. CI is the most reliable source of truth in the repo — it's the one place where commands are known to work, because they run.
- **Tests**: test directories and file-naming patterns, test runner config, fixtures, `docker-compose*.yml` used by tests, coverage config and thresholds.
- **Releases**: `git tag --sort=-creatordate | head -20`, `git log --oneline -30` (do commits follow Conventional Commits?), release automation config (`release-please-config.json`, `.releaserc`, `.changeset/`, `cliff.toml`, `semantic-release` in devDeps), publish steps in CI, `CHANGELOG.md` format.
- **Existing docs**: `README.md`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/`, `.claude/rules/`, `.cursorrules`, `.github/copilot-instructions.md`.

For a large repo, sample rather than exhaustively read — the goal is a correct coarse-grained picture, not a complete one.

### 2. Decide which files this repo warrants

A stub file nobody maintains is worse than no file: it looks authoritative and goes stale silently. Propose a file only when the repo has something real to put in it.

| File | Warranted when | Skip when |
|---|---|---|
| `CLAUDE.md` | Essentially always — any repo an agent will work in | Never skip, but keep it tiny for a small repo |
| `ARCHITECTURE.md` | More than one component, service, package or deployable; or non-obvious internal structure; or shared code that constrains how things may depend on each other | Single small module where the file tree *is* the architecture |
| `TESTING.md` | Tests exist across more than one layer or project, or there's setup a newcomer wouldn't guess (containers, seeded data, env vars) | One test dir, one runner, `npm test` and you're done — a line in `CLAUDE.md` covers it |
| `RELEASE.md` | The repo ships something: tags, GitHub releases, a published package, a container image, a deployment | Nothing is versioned or published; no tags, no registry |

If a repo doesn't warrant a file, say why rather than silently omitting it — the user may know about a release process that leaves no trace in the repo.

### 3. Triage what's already there

If `CLAUDE.md` (or `AGENTS.md`) already exists, read it and classify every section against the placement table below. This is usually where most of the value is: existing agent-instruction files accumulate architecture notes, testing lore and deploy steps that nobody ever moved out.

Note also that Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If the repo has `AGENTS.md` and no `CLAUDE.md`, don't duplicate the content — create a `CLAUDE.md` whose first line is `@AGENTS.md`, then add Claude-specific content beneath it.

### 4. Propose, then confirm

Show the user, briefly:

- which of the four files you'll create or edit, and which you're skipping with the reason
- what you'll move *out* of any existing `CLAUDE.md`, and where each piece is going
- anything you plan to delete outright (with justification — see the table)
- what you couldn't determine and will mark TODO

Get agreement before writing. Moving someone's documentation around without asking is the kind of change that's annoying to undo. If there's a genuine fork — say, the repo has both a `Makefile` and npm scripts and you can't tell which is canonical — ask.

### 5. Write

Read the reference for each file as you write it. They contain the section-by-section guidance and a template:

- `references/claude-md.md` — purpose, commands, repo-wide rules, links; plus Claude Code specifics (`.claude/rules/`, path-scoped rules, `CLAUDE.local.md`, imports)
- `references/architecture-md.md` — bird's-eye view, codemap, component relationships, shared-library rules, cross-cutting concerns, invariants and gotchas
- `references/testing-md.md` — test layers per project, where tests live, how to run them, and the post-change smoke test
- `references/release-md.md` — versioning, the release command sequence, changelog policy, artifacts, hotfix and rollback
- `references/elsewhere.md` — where content goes when it belongs in none of the four (ADRs, `CONTRIBUTING.md`, path-scoped rules, skills, runbooks, module READMEs)

Match the repo's existing documentation voice and formatting where it has one.

### 6. Report

State what was written, what moved where, and the TODO list from step 2's gaps. Suggest `/init` afterwards only if a `CLAUDE.md` didn't previously exist and the user wants Claude's own read on it.

## Placement table

This is the core of the skill: given a piece of knowledge, where does it live?

| Content | Home | Why |
|---|---|---|
| What this repo is and who it's for (1 paragraph) | `CLAUDE.md` | Needed to interpret everything else, every session |
| Build, test, lint, typecheck, run commands | `CLAUDE.md` | Typed constantly; the highest-value lines in the file |
| Repo-wide conventions that differ from tool defaults ("pnpm not npm", "never edit `gen/`") | `CLAUDE.md` | Cheap to state, expensive to get wrong |
| Links to the other three documents | `CLAUDE.md` | Plain markdown links, not `@`-imports |
| Directory tree, file listings, dependency lists | **Delete** | Derivable in seconds with `ls`/`Glob`; goes stale immediately |
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
| Why a design decision was made, alternatives rejected | `docs/adr/NNNN-*.md` | Decisions are dated records; architecture is current state |
| PR process, commit format, code review expectations | `CONTRIBUTING.md` | Aimed at contributors, not at agents mid-task |
| Instructions that only apply to one subtree | `.claude/rules/*.md` with `paths:` frontmatter | Loads on demand when matching files are touched |
| A repeatable multi-step procedure | A skill | Loads only when invoked; can carry scripts |
| Personal preferences, local URLs, sandbox creds | `CLAUDE.local.md` (gitignored) | Not the team's business |
| Secrets and tokens | Secret manager — **never a document** | |
| Aspirational rules with nothing enforcing them | **Delete**, or mark advisory | An unenforced rule trains people to ignore the file |

When something doesn't fit any row, prefer the most specific home that will actually be read, and default to leaving it out of `CLAUDE.md`.

## Keeping the documents honest

Two failure modes to design against as you write:

**Staleness.** Anything that mirrors code (file trees, function names, exact line counts, exhaustive lists) will drift within weeks and nobody will notice. Write at the altitude that survives refactors: name modules and directories, don't link to files or line numbers; describe responsibilities, not signatures. If a sentence would be wrong after a routine refactor, raise its altitude or cut it.

**Unfalsifiable filler.** "Write clean, maintainable code" and "follow best practices" occupy space and change no behaviour. Every rule you write should be concrete enough that someone could point at a diff and say whether it complied. If you can't make it falsifiable, it's not a rule — it's a mood, and it should be cut.
