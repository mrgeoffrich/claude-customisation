---
name: worktree-remove
description: >
  Tears down a finished {{PROJECT_NAME}} worktree — checks for unsaved work, runs
  `{{ENV_COMMAND}} delete <slug>` to destroy the worktree's isolated environment (containers,
  volumes, database, allocated ports, registry entry), then `git worktree remove
  {{WORKTREE_DIR}}/<slug>`. The remote branch is left alone because the PR points at it. Takes
  the worktree slug as its argument (e.g. `/worktree-remove tunnel-retry`). Use this skill
  whenever the user says "finish worktree", "clean up worktree", "tear down worktree", "remove
  worktree", "done with worktree", "delete worktree <slug>", or "free up that worktree's slot".
  Do not trigger while there is still active work in the worktree, or when the run failed —
  leaving it alive is the right answer in those cases.
---

# Worktree Remove — {{PROJECT_NAME}}

Destroys a finished worktree and frees its slot so the next worktree can take it. Both halves
are needed: `{{ENV_COMMAND}} delete` releases the environment, `git worktree remove` releases
the directory. Skipping the first leaks containers, volumes, and a held slot; skipping the
second leaves a stale directory and a dangling `git worktree list` entry.

The remote branch is **left alone** — that is where the PR points.

## Arguments

- **`<slug>`** *(required)* — the worktree slug. Extract it from surrounding text if needed.

With no argument, **stop and ask**. Never auto-pick "the most recent worktree"; that is how
someone's work in progress gets destroyed.

---

## Phase 1 — Resolve the target

```bash
git worktree list
{{ENV_COMMAND}} list
```

Cross-check both. Partial states are common and each needs different handling:

- **Directory gone, registry entry remains** → run only `{{ENV_COMMAND}} delete <slug>`. This is
  the usual case when someone ran `git worktree remove` by hand first.
- **Directory remains, no registry entry** → run only `git worktree remove`.
- **Neither** → already cleaned up, or the slug is wrong. Say so and stop.

---

## Phase 2 — Defensive checks

Run these from inside the worktree, then return to the repo root. Each one stops the skill and
asks; the cost of an unnecessary confirmation is far below the cost of destroying real work.

1. **Uncommitted changes** — `git status --porcelain`. Any output means work would be lost.
2. **Unpushed commits** — `git log @{u}..HEAD --oneline 2>/dev/null || git log --oneline`. The
   fallback fires when the branch was never pushed, which is itself a stop signal.
3. **PR open** — `gh pr view --json url,state -q '.url + " (" + .state + ")"' 2>/dev/null`. No
   PR usually means the work has not shipped yet.

All three clear → proceed silently.

---

## Phase 3 — Tear down

From the **repo root** — you cannot remove the worktree you are standing in:

```bash
cd <repo-root>
{{ENV_COMMAND}} delete <slug> --force
git worktree remove {{WORKTREE_DIR}}/<slug>
```

`{{ENV_COMMAND}} delete` destroys {{ISOLATED_RESOURCES_LIST}} and frees the slot. It works from
the registry alone, so it is still correct if the directory is already gone.

The two `--force` flags here are not the same flag, and the difference is worth holding onto:

- **`{{ENV_COMMAND}} delete --force` is fine.** It only skips an interactive "are you sure?"
  prompt. Phase 2 already did the checking that prompt exists for.
- **`git worktree remove --force` is not.** It overrides git's refusal to delete a worktree
  with uncommitted or untracked files — and that refusal is real signal, not an obstacle.

So if `git worktree remove` refuses because the worktree is dirty, **stop and look**. It means
Phase 2 missed something: usually a build artifact, sometimes a local config the user wants.

---

## Phase 4 — Verify and report

```bash
{{ENV_COMMAND}} doctor
```

A clean `doctor` confirms nothing leaked. Then report:

```
✓ Removed {{WORKTREE_DIR}}/<slug> and freed slot <N>.
  Branch {{BRANCH_PREFIX}}<slug> remains on the remote (PR points at it).
```

If the user is mid-review-cycle, mention that the worktree can be recreated from the same
branch: `git worktree add {{WORKTREE_DIR}}/<slug> {{BRANCH_PREFIX}}<slug>`, then the install
step and `{{ENV_COMMAND}} start`. (`/worktree-create` always branches from
{{DEFAULT_BRANCH}}, so it is the wrong tool for resuming an existing branch.)

---

## Hard rules

- **Never clean up on a failure path.** Failed smoke, no PR, mid-investigation — leave it alive.
- **Never delete the remote branch.** The PR points at it. Cleanup is local only.
- **Never delete a worktree you are standing in.** `cd` to the repo root first.
- **Never auto-pick a worktree to delete.** Require an explicit slug.
- **Never pass `--force` to `git worktree remove` automatically.** Git refusing is signal. (This
  does not apply to `{{ENV_COMMAND}} delete --force`, which only skips a confirmation prompt.)
- **Never skip `{{ENV_COMMAND}} delete`.** Removing only the directory leaks the environment
  and holds the slot, and the leak is invisible until slots run out.
- **Never produce an ExitPlanMode block.** This is cleanup, not planning.

---

## Example

> User: `/worktree-remove tunnel-retry`
>
> *`git worktree list` shows `{{WORKTREE_DIR}}/tunnel-retry` on `{{BRANCH_PREFIX}}tunnel-retry`;
> `{{ENV_COMMAND}} list` shows it holding slot 3.*
>
> *Defensive checks from inside the worktree: clean tree, nothing unpushed, PR #412 open.*
>
> *Back at the repo root: `{{ENV_COMMAND}} delete tunnel-retry --force`, then
> `git worktree remove {{WORKTREE_DIR}}/tunnel-retry`, then `{{ENV_COMMAND}} doctor` — clean.*
>
> Skill: "✓ Removed `{{WORKTREE_DIR}}/tunnel-retry` and freed slot 3. Branch
> `{{BRANCH_PREFIX}}tunnel-retry` remains on the remote (PR #412 points at it)."

> User: `/worktree-remove docs-fix`
>
> *Worktree exists, but `git status --porcelain` returns `M src/foo.ts`. **Stop.***
>
> Skill: "Worktree `docs-fix` has uncommitted changes:
>
> ```
> M src/foo.ts
> ```
>
> Removing it loses them. Proceed anyway, or handle them first?"
