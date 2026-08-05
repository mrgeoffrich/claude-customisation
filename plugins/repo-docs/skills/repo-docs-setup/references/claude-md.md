# Writing CLAUDE.md

## What this file is

Instructions loaded into context at the start of every Claude Code session, and — in practice — the first thing a new human contributor reads too. Claude Code walks up the directory tree from the working directory and concatenates every `CLAUDE.md` and `CLAUDE.local.md` it finds, root-first, so a nested file is read *after* the root one.

It is context, not enforced configuration. Claude reads it and tries to follow it; there's no guarantee of compliance. Anything that must happen at a fixed point (before every commit, after every edit) belongs in a hook, not here.

## Size

Target under 200 lines. Longer files consume more context and measurably reduce adherence — this is Anthropic's own published guidance. Most repos should land well under 100.

Note that `@path` imports do **not** help with size: imported files are expanded into context at launch, so `@ARCHITECTURE.md` costs the same as pasting the file inline. Imports help with *organisation*, not context budget. To actually reduce what loads every session, use plain markdown links (read on demand), `.claude/rules/` with `paths:` frontmatter (loads only when matching files are touched), or a skill (loads only when invoked).

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
```

Drop any section the repo has nothing real to put in. An empty "Conventions" heading is worse than no heading.

## What earns its place

**Yes:**
- The purpose paragraph — without it, every other instruction is uninterpretable
- Commands, especially the non-obvious ones (how to run a *single* test is worth more than how to run all of them)
- Conventions that contradict defaults: the package manager, a directory that must not be hand-edited, a required env file, a naming rule a linter doesn't catch
- Hard prohibitions and off-limits paths
- Links to the other three docs

**No:**
- Directory trees and file listings — an agent runs `ls` in a second, and the listing is wrong by next week
- Dependency lists — `package.json` is right there and always current
- Architecture explanation — `ARCHITECTURE.md`
- Test conventions beyond the smoke command — `TESTING.md`
- Release steps — `RELEASE.md`
- Multi-step procedures — a skill
- Style rules a formatter already enforces — say "Prettier is authoritative, run `<cmd>`" and stop
- "Write clean code", "follow best practices", "be careful" — unfalsifiable, so they change nothing

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

**Nested `CLAUDE.md`** — files in subdirectories load on demand when Claude reads files in that directory, not at launch. In a monorepo, a short per-package `CLAUDE.md` is often better than stuffing per-package detail into the root file.

**`/init`** — generates a starting `CLAUDE.md` from the codebase, or suggests improvements if one exists. Reasonable to suggest to the user afterwards, but it discovers what's derivable from code; the value you add is the part that isn't.
