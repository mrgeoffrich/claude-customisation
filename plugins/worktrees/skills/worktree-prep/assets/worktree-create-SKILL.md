---
name: worktree-create
description: >
  Creates a fresh, fully isolated git worktree for {{PROJECT_NAME}} — pre-flights the main
  checkout, pulls the latest {{DEFAULT_BRANCH}}, creates the worktree at
  {{WORKTREE_DIR}}/<slug> on branch {{BRANCH_PREFIX}}<slug>, {{INSTALL_STEP_SUMMARY}}, and runs
  `{{ENV_COMMAND}} start` to allocate this worktree's own ports, {{ISOLATED_RESOURCES_SUMMARY}}
  so it cannot collide with any other worktree. Takes an optional short slug (e.g.
  `/worktree-create tunnel-retry`); generates a random `adjective-animal` slug when omitted. Pass
  `--no-env` to create the worktree without starting the environment — useful for docs-only
  changes. Use this skill whenever the user says "set up a worktree", "create a worktree", "spin
  up a worktree", "new worktree for X", "make me a worktree", "I want to work on this in
  parallel", or any equivalent ask for an isolated checkout. Do not trigger when the user is
  already inside a worktree and wants to keep working there.
---

# Worktree Create — {{PROJECT_NAME}}

Creates an isolated worktree and brings up its own environment. This is scaffolding, not an
execution agent: it hands back a ready worktree and stops.

Isolation comes from `{{ENV_COMMAND}} start`, which assigns this worktree a slot and derives
every shared resource from it. Without that step the worktree shares {{PROJECT_NAME}}'s ports
and state with every other checkout, which is the problem worktrees are supposed to solve.

## Arguments

- **`<slug>`** *(optional)* — short kebab-case name (e.g. `tunnel-retry`). Sanitised to
  `[a-z0-9-]`. When omitted, generate a random `<adjective>-<animal>` slug (`swift-otter`,
  `bold-lynx`), both words ≤8 characters. State the chosen slug up front so the user can `cd`
  to it.
- **`--no-env`** *(optional)* — skip the environment start. Say explicitly that you skipped it.
- **`--description "<text>"`** *(optional)* — ≤10 words, stored in the registry so
  `{{ENV_COMMAND}} list` is readable later.

---

## Phase 1 — Pre-flight

Run from the **main checkout**, on {{DEFAULT_BRANCH}}, with a clean tree:

```bash
pwd
git rev-parse --abbrev-ref HEAD
git status --porcelain
```

If the working tree is dirty, the branch is not {{DEFAULT_BRANCH}}, or you are already inside a
worktree — **stop and say so**. Do not auto-stash or auto-checkout; the user's work in progress
matters more than this skill finishing.

```bash
git pull --ff-only origin {{DEFAULT_BRANCH}}
```

`--ff-only` surfaces a diverged local branch as an error instead of silently merging.

---

## Phase 2 — Create the worktree

Check for collisions first:

```bash
ls {{WORKTREE_DIR}}/<slug> 2>/dev/null
git rev-parse --verify --quiet refs/heads/{{BRANCH_PREFIX}}<slug>
```

- **Random slug collides** → regenerate silently, up to 3 attempts, then ask.
- **User-supplied slug collides** → stop and ask. The existing worktree may hold real work;
  recreating it silently is how that gets lost.

```bash
git worktree add {{WORKTREE_DIR}}/<slug> -b {{BRANCH_PREFIX}}<slug>
cd {{WORKTREE_DIR}}/<slug>
```

Everything after this runs from inside the worktree.

---

## Phase 3 — Install dependencies

{{INSTALL_STEP}}

A fresh worktree has no dependencies installed — worktrees share git objects, not build
artifacts. Run this synchronously; the environment step below depends on it.

If it fails, stop and surface the output rather than working around it with force flags.

---

## Phase 4 — Start the isolated environment (skip if `--no-env`)

```bash
{{ENV_COMMAND}} start --description "<short summary>"
```

This allocates the worktree's slot and materialises its resources: {{ISOLATED_RESOURCES_LIST}}.
It writes `{{DESCRIPTOR_FILE}}` at the worktree root — read ports and URLs from there rather
than assuming any value, because they differ per worktree.

{{BACKGROUND_NOTE}}

If no `--description` was supplied, ask the user once for one (≤10 words).

---

## Phase 5 — Report

State plainly:

- Worktree path and branch
- Dependency install: done
- Environment: started (with the allocated URLs from `{{DESCRIPTOR_FILE}}`), or skipped
- **Any resources this worktree still shares** — read the `shared_resources` block in
  `{{DESCRIPTOR_FILE}}` and repeat it. Writes to those escape the worktree, and whoever works
  here needs to know before they make one.
- Current working directory

Then stop. The caller takes it from here.

---

## Hard rules

- **Never run on a dirty tree or a non-default branch.** Stop instead; do not auto-stash.
- **Never silently reuse an existing worktree or branch.** Ask.
- **Never skip the environment step without saying so.** A worktree with no allocated slot
  collides with every other checkout, and the failure looks like an unrelated bug.
- **Never hardcode a port when reporting URLs.** Read `{{DESCRIPTOR_FILE}}`.
- **Never produce an ExitPlanMode block.** This is scaffolding, not planning.

---

## Example

> User: `/worktree-create tunnel-retry`
>
> *Pre-flight passes: main checkout, on {{DEFAULT_BRANCH}}, clean. Pulls latest.*
>
> *Creates `{{WORKTREE_DIR}}/tunnel-retry` on `{{BRANCH_PREFIX}}tunnel-retry`, cds in.*
>
> *Runs the install step, then `{{ENV_COMMAND}} start --description "tunnel reconciler retry budget"`.*
>
> Skill: "Worktree ready at `{{WORKTREE_DIR}}/tunnel-retry` on `{{BRANCH_PREFIX}}tunnel-retry`.
> Slot 3 — web on http://localhost:3103, API on http://localhost:4103, database
> `myapp_tunnel_retry` seeded from dev. Still shared: the Stripe test account — test charges
> made here are visible to the whole team."
