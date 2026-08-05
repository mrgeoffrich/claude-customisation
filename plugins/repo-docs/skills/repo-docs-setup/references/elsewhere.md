# Where content goes when it belongs in none of the five

Most of the work of tidying repo documentation is deciding what to *remove*. These are the destinations, roughly in order of how often they come up.

## Delete it

The most common correct answer, and the one people are most reluctant to reach for. Delete when:

- **It's derivable from the codebase in seconds.** Directory trees, dependency lists, file inventories, "the project uses TypeScript and React". An agent runs `ls` or reads `package.json` faster than it reads your description, and gets an answer that's actually current.
- **It's unfalsifiable.** "Write clean, maintainable code." "Follow best practices." "Be mindful of performance." Nobody can point at a diff and say whether it complied, so nothing changes — except that the file got longer and less likely to be read.
- **A tool already enforces it.** A page of formatting rules under a repo with Prettier config is dead weight. Replace with: "Prettier is authoritative; run `pnpm format`."
- **It's stale and nobody can say what the current truth is.** Wrong documentation is worse than absent documentation, because it's trusted. Cut it and flag the gap to the user.

When deleting something non-obvious, say what you removed and why, so the user can push back.

## `docs/adr/NNNN-title.md` — Architecture Decision Records

For *why* a decision was made, what alternatives were rejected, and what the trade-off was. The distinction from `ARCHITECTURE.md` is tense: architecture describes the present, an ADR records a dated decision. That's what lets a decision be superseded by a later ADR without rewriting anything else, and it's why decision history in `ARCHITECTURE.md` makes that file grow without bound.

Minimal shape — context, decision, consequences, status:

```markdown
# 0007. Use Postgres row-level security for tenant isolation

Date: 2026-03-14
Status: Accepted (supersedes 0004)

## Context
<The forces in play. What made this decision necessary.>

## Decision
<What was decided, stated plainly.>

## Consequences
<What this makes easy, what it makes hard, what it commits us to.>
```

## `CONTRIBUTING.md`

Aimed at people contributing, not at agents mid-task: PR process, commit message convention, review expectations, DCO/CLA, how to get a dev environment up, code of conduct pointer. Overlaps `TESTING.md` and `RELEASE.md` at the edges — cross-link rather than duplicate, and let each fact live in exactly one place.

## `.claude/rules/*.md`

For agent instructions that are genuinely important but only apply to part of the repo. With `paths:` frontmatter they load only when Claude touches matching files, so they cost nothing in sessions that go nowhere near that code:

```markdown
---
paths:
  - "migrations/**/*.sql"
---

# Migrations

- Migrations are append-only; never edit an applied migration, add a new one.
- Every migration needs a tested `down`.
```

Rules without `paths:` load every session at the same priority as `CLAUDE.md` — so a rule file with no `paths:` is just `CLAUDE.md` content in a different location, and should be justified on organisation grounds or not split out at all.

## A skill

For a repeatable multi-step procedure — a deployment runbook, a scaffolding workflow, a data migration, an audit. Skills load only when invoked or when their description matches the task, can bundle scripts and templates, and can carry far more detail than any always-loaded file could justify.

Rule of thumb: if you're writing numbered steps into `CLAUDE.md`, it wants to be a skill.

## `docs/runbooks/*.md`

Operational procedures for running systems: incident response, on-call playbooks, scaling, backup and restore. Different audience and different urgency from everything else here, and worth keeping separate for that reason alone.

The boundary with `HOSTING.md` is routine versus emergency. A deploy is routine and belongs in `HOSTING.md`, along with the rollback that follows a bad one; diagnosing an outage at 3am is a runbook. If a procedure runs to numbered steps someone follows under pressure, it wants a runbook or a skill, linked from `HOSTING.md`.

## Module-level `README.md`

How one component works *internally* — its design, its key types, its quirks. Keeps `ARCHITECTURE.md` at the map altitude where it stays stable, while giving detail a home next to the code it describes, where it's most likely to be updated alongside it. Link to it from the component's codemap entry.

## `CLAUDE.local.md`

Personal, project-specific, gitignored. Sandbox URLs, preferred test data, local overrides, individual workflow preferences. If you create one, add it to `.gitignore` in the same change.

Note that a gitignored file only exists in the worktree where it was created. To carry personal instructions across worktrees, import from the home directory instead: `@~/.claude/my-project-instructions.md`.

## `SECURITY.md`

Vulnerability reporting, supported versions, disclosure policy. GitHub surfaces it in the repo's Security tab, which is the main reason to use the conventional filename.

## Never in any document

Secrets, tokens, keys, connection strings with credentials, internal URLs that are only "secret" by obscurity. Reference them by name — `NPM_TOKEN`, `DATABASE_URL` — and say where they're configured. Anything committed to a repo is permanent in its history, and documentation is the easiest place for a secret to get pasted "temporarily".
