# Writing CLAUDE.md

## What this file is

Instructions loaded into context at the start of every Claude Code session, and — in practice — the first thing a new human contributor reads too. Claude Code walks up the directory tree from the working directory and concatenates every `CLAUDE.md` and `CLAUDE.local.md` it finds, root-first, so a nested file is read *after* the root one.

It is context, not enforced configuration. Claude reads it and tries to follow it; there's no guarantee of compliance. Anything that must happen at a fixed point (before every commit, after every edit) belongs in a hook, not here.

## Size

Target under 200 lines. Longer files consume more context and measurably reduce adherence — this is Anthropic's own published guidance. Most repos should land well under 100.

Note that `@path` imports do **not** help with size: imported files are expanded into context at launch, so `@ARCHITECTURE.md` costs the same as pasting the file inline. Imports help with *organisation*, not context budget. To actually reduce what loads every session, use plain markdown links (read on demand), a nested per-project `CLAUDE.md` (loads only when Claude works in that directory — see "Per-project files"), `.claude/rules/` with `paths:` frontmatter (loads only when matching files are touched), or a skill (loads only when invoked).

## Structure

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

<One paragraph: what the repo produces, who consumes it, and the single most
important thing to understand before changing anything. If the repo is a
monorepo, say so here and name the top-level pieces.>

## Commands

| Task | Command |
|------|---------|
| Install | `<...>` |
| Build | `<...>` |
| Test (all) | `<...>` |
| Test (single file) | `<...>` |
| Lint / format | `<...>` |
| Typecheck | `<...>` |
| Run locally | `<...>` |

<Monorepo: add how to scope a command to one package, e.g.
`pnpm --filter @acme/api test`. That one line saves an agent a lot of flailing.>

## Conventions

- <Only rules that differ from what a competent person would assume by default.>
- <Each one concrete enough to check against a diff.>
- <Prohibitions are especially valuable: "never edit `src/generated/` — regenerate with `<cmd>`".>

## Before you finish

<The smoke check: the 1–3 commands that must pass after any change. Cross-reference
TESTING.md for the full picture.>

## Further reading

- `ARCHITECTURE.md` — components, how they relate, and the invariants between them
- `TESTING.md` — what to test where, and how to run it
- `RELEASE.md` — how a release is cut
- `HOSTING.md` — where it runs, and how a deploy happens
```

Drop any section the repo has nothing real to put in. An empty "Conventions" heading is worse than no heading.

## What earns its place

**Yes:**
- The purpose paragraph — without it, every other instruction is uninterpretable
- Commands, especially the non-obvious ones (how to run a *single* test is worth more than how to run all of them)
- Conventions that contradict defaults: the package manager, a directory that must not be hand-edited, a required env file, a naming rule a linter doesn't catch
- Hard prohibitions and off-limits paths
- Links to the other four docs

**No:**
- Directory trees and file listings — an agent runs `ls` in a second, and the listing is wrong by next week
- Dependency lists — `package.json` is right there and always current
- Brittle values: test counts, coverage percentages, line counts, package counts, pinned tool versions, benchmark timings — see below
- History: migration notes, "recently added", "we used to use X", "changed in v2" — see below
- Architecture explanation — `ARCHITECTURE.md`
- Test conventions beyond the smoke command — `TESTING.md`
- Release steps — `RELEASE.md`
- Deploy steps, environment URLs, infrastructure detail — `HOSTING.md`
- Multi-step procedures — a skill
- Style rules a formatter already enforces — say "Prettier is authoritative, run `<cmd>`" and stop
- "Write clean code", "follow best practices", "be careful" — unfalsifiable, so they change nothing

## No brittle values

Every number in this file is loaded into every session and read as current fact. A number that has drifted is worse than a missing one: an agent will repeat it to the user, or act on it — "the suite has 47 tests" invites a report that four tests have gone missing, when four were merged last Tuesday.

Nothing catches the drift, either. No test fails when the count changes, no lint rule flags "92% coverage" after coverage slips to 71%, and the person who'd notice is the one person who no longer needs to read the file.

So, before writing any number, ask: **would this still be true after a normal week of merges?**

| Cut | Keep |
|---|---|
| "47 tests across 6 suites" | Nothing — `<test cmd>` prints the count on demand |
| "92% coverage" | "Coverage threshold enforced in CI" — the number itself belongs in `TESTING.md`, and only if something enforces it |
| "~8,000 lines, 12 packages" | "A pnpm workspace; `apps/web` and `apps/api` are the deployables" |
| "Node 20.11.1, pnpm 9.1.0" | "Node and pnpm versions are pinned in `.nvmrc` and `packageManager` — use those" |
| "Full suite: 3m12s" | "Unit tests take seconds, E2E minutes — scope while iterating" |
| "12 endpoints under `/api/v1`" | "REST endpoints live under `/api/v1`" |
| "Currently on React 18" | Nothing — that's `package.json`'s job |

Two exceptions. **Decisions aren't measurements**: a port number, a minimum supported version, a required schema version, a policy like "we support the two most recent Node LTS lines" changes only when someone changes it on purpose, and the doc is a legitimate home for it. **Orders of magnitude survive**: "seconds versus minutes" is the part a reader needs in order to decide whether to run something, and it's still true a year later when `3m12s` isn't.

When a number is genuinely load-bearing, cite where it lives rather than copying it — "the threshold is in `vitest.config.ts`" stays correct after someone changes the threshold; `92%` does not.

This applies with full force when editing an existing `CLAUDE.md`. Treat each number you find as unverified: check it against the repo, and either delete it, restate it qualitatively, or replace it with a pointer. Don't quietly refresh it to today's value — that just resets the clock on the same problem.

## A statement of now, not an audit log

Write the file entirely in the present tense. It answers "what is true about this repo?" — not "what has happened to it?" The repo already has three better records of the past: git history, `CHANGELOG.md`, and dated ADRs. Each of those carries a timestamp and an author; a line in `CLAUDE.md` carries neither, so it can't even be aged.

The lines that accumulate here look like:

- "Migrated from Webpack to Vite in March 2025"
- "We used to use `moment` — now it's `date-fns`"
- "Recently added the `packages/ui` workspace"
- "The auth rewrite landed in v3, so ignore the old middleware section"
- "Fixed the flaky login test in #482"

Nobody ever deletes these, so the file slowly becomes a diary. It costs context in every session to describe states that no longer exist, and it makes the reader adjudicate which clause is current. Relative time words are the worst of it: **"recently", "new", "currently", "as of", "still", "for now"** are all wrong within a year, and their failure mode is active — a year on, the "new" pattern is the old one, and the note now steers an agent to precisely the thing it was warning against.

Usually the fix is a rewrite, not a deletion. The fact underneath is fine; only the framing is historical:

| Cut | Keep |
|---|---|
| "Migrated from Webpack to Vite in March" | "Vite is the bundler" — or nothing, if `vite.config.ts` says so |
| "We used to use `moment`; now `date-fns`" | "Use `date-fns`; don't add `moment`" |
| "Recently added the `packages/ui` workspace" | Let `ARCHITECTURE.md`'s codemap name it, like every other package |
| "Deprecated as of last quarter" | "`legacyClient` is deprecated — new call sites use `apiClient`" |
| "Fixed the flaky login test in #482" | Nothing — git history has it |
| "New contributors should note the v2 API is gone" | "The API is `/api/v3`" |

The exception is history that still binds today. "Don't reorder the middleware — the session cookie must be set before the CSRF check reads it" reads like a war story but is a live constraint: it tells someone what not to do this afternoon. Keep it, phrased as the constraint rather than as the incident. The test is whether the sentence changes an action. If it only reports an event, it goes.

When editing an existing file, this is often the largest single cut available, and it's the safest one — the information isn't being destroyed, it's already in the git log.

## Rules should be falsifiable and enforced

For each rule, ask two questions: could someone look at a diff and say definitively whether it was followed? And is anything actually enforcing it?

A rule with an enforcement layer (hook, CI check, lint rule) is a rule. A rule with nothing behind it is advisory — either tag it as such, or cut it. Files full of unenforced rules train both people and agents to skim the whole document.

## Maintainer notes cost nothing

Block-level HTML comments are stripped before the file is loaded into context:

```markdown
<!-- Maintainer note: the pnpm pin exists because npm 10 breaks the postinstall
     patch step. Revisit when we drop patch-package. -->
```

Use these for TODOs and rationale that humans need but agents don't. They stay visible when the file is opened with the Read tool, and cost zero tokens at session start.

## Claude Code specifics worth knowing

**`.claude/rules/`** — topic files that load with the same priority as `CLAUDE.md`. Add `paths:` frontmatter to scope a rule to a subtree so it loads only when Claude touches matching files:

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API rules

- Every endpoint validates input with the shared `zod` schemas in `src/api/schemas`.
- Errors use the `ApiError` envelope; never return a bare string body.
```

This is the right home for instructions that are important but only apply to part of the repo — they'd otherwise bloat `CLAUDE.md` for every session that never goes near that code.

**`CLAUDE.local.md`** — same directory, gitignored, loaded after `CLAUDE.md`. Personal sandbox URLs, preferred test data, local overrides. If you create one, add it to `.gitignore` in the same change.

**`AGENTS.md`** — Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If a repo already has `AGENTS.md`, don't fork the content. Create:

```markdown
@AGENTS.md

## Claude Code

<Claude-specific additions here.>
```

A symlink (`ln -s AGENTS.md CLAUDE.md`) also works when there's nothing Claude-specific to add, though it needs Administrator or Developer Mode on Windows.

**Nested `CLAUDE.md`** — files in subdirectories load on demand when Claude reads files in that directory, not at launch. See "Per-project files" below; in a monorepo this is the highest-leverage structural move available.

**`/init`** — generates a starting `CLAUDE.md` from the codebase, or suggests improvements if one exists. Reasonable to suggest to the user afterwards, but it discovers what's derivable from code; the value you add is the part that isn't.

## Per-project files

Everything above is about *what* goes in the file. This is about *where* — and in a repo with more than one project it's the biggest single reduction available in what each session pays.

Loading works in two directions. At launch, Claude Code walks from the working directory up to the repo root and concatenates every `CLAUDE.md` it passes, root-first. Below the working directory, nested files load on demand, when Claude reads a file in that directory. So `apps/api/CLAUDE.md` is free for a session working in `apps/web`, arrives automatically the moment Claude opens something under `apps/api`, and is there from launch for someone who started their session inside `apps/api` — which is how people actually work on one package.

The root file has no such escape: every line is loaded by every session in the repo, whatever it's about. That's what makes a monorepo root file bloat so reliably — it becomes the union of every package's quirks, and each session pays for all of them to get the one it needs.

### What goes down

For each project directory, ask what a session working *only* there needs, and what every other session would be carrying for no reason.

| Push down to `<project>/CLAUDE.md` | Keep at the root |
|---|---|
| That project's build, test and run commands | How to scope any command to one package (`pnpm --filter @acme/api test`) |
| Framework conventions true of one stack — the Next.js app's route conventions, the Rust crate's feature flags, the Django app's settings module | The package manager, commit format, the "never hand-edit `gen/`" rule |
| Env vars, ports, local services, seed data for one service | Anything needed to interpret the repo at all |
| Paths, generated directories and off-limits files inside that project | Cross-package invariants (which packages may depend on which) |
| Gotchas an agent would only ever hit while working in there | The smoke check that gates any change anywhere |

### Writing the child file

Same rules as the root, scaled down. It's loaded *after* the root file, so don't restate what the root already establishes — no repeated purpose paragraph, no repeated package manager note. Open with what this project is and how it relates to the rest of the repo, then its commands, then its conventions. A dozen lines is a perfectly good per-package `CLAUDE.md`. The brittle-values and present-tense rules apply exactly as they do at the root; child files rot faster, if anything, because fewer people read them.

### When not to

- **One file per project, not per folder.** A project is something with its own build, test cycle or deployable. A `CLAUDE.md` in `src/utils/` is noise that will never be read at a useful moment.
- **Rules about a subtree belong in `.claude/rules/` with `paths:` frontmatter**, not a nested `CLAUDE.md`. The distinction: a nested `CLAUDE.md` orients someone *working in* a directory; a path-scoped rule fires whenever matching files are touched, from anywhere in the repo. "Every endpoint validates with the shared zod schemas" is the latter — it should apply to an agent editing `src/api/` from the repo root.
- **Single-project repos.** There's nothing to push down; splitting a small root file into two smaller files just adds a hop.
- **Don't split for the sake of it.** If a package has nothing to say that the root doesn't already cover, it doesn't need a file.
