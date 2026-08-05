<!--
Template for the worktree section in the target repo's CLAUDE.md / AGENTS.md.
Replace every {{PLACEHOLDER}} with the real value, delete rows and sections that do not
apply, and drop this comment. A section shipped with placeholders left in is worse than
no section, because it teaches the next session values that do not exist.
-->

## Parallel development with worktrees

Multiple branches can be developed at once, each in its own worktree with its own fully
isolated environment. Use this instead of stashing and switching when you have more than one
change in flight, and always when running more than one agent against this repo.

### Creating one

```bash
git worktree add {{WORKTREE_DIR}}/<slug> -b {{BRANCH_PREFIX}}<slug>
cd {{WORKTREE_DIR}}/<slug>
{{INSTALL_COMMAND}}
{{ENV_COMMAND}} start --description "<what this worktree is for>"
```

Or run `/worktree-create <slug>`, which does all four steps in order with pre-flight checks.
Prefer it — the ordering matters, and `{{ENV_COMMAND}} start` before `{{INSTALL_COMMAND}}` or
outside the worktree does not do what it looks like it does.

### What is isolated

`{{ENV_COMMAND}} start` assigns the worktree a **slot** and derives everything from it, so no
two worktrees collide:

| Resource | Main checkout (slot 0) | Worktree slot N |
|---|---|---|
{{ALLOCATION_TABLE_ROWS}}

The allocation is written to `{{DESCRIPTOR_FILE}}` at the worktree root, and it is **stable
across restarts** — the same worktree keeps the same ports.

### Reading the environment — never hardcode a port

Every port and name differs per worktree. Read `{{DESCRIPTOR_FILE}}` instead of assuming:

```bash
{{DESCRIPTOR_READ_EXAMPLE}}
```

This applies to browser automation, integration tests, and anything that dials a local URL.
A hardcoded `localhost:{{DEFAULT_PORT}}` in a worktree reaches whatever the main checkout is
running — which looks like it works, right up until it corrupts something.

### What is still shared

{{SHARED_RESOURCES_SECTION}}

Writes to anything on that list escape the worktree. Treat them with the same care you would
in the main checkout.

### Other commands

```bash
{{ENV_COMMAND}} list      # every worktree, its slot, its URLs
{{ENV_COMMAND}} doctor    # drift: orphaned entries, stolen ports, leaked containers
{{ENV_COMMAND}} delete <slug>   # destroy the environment and free the slot
```

### Finishing

```bash
cd <repo-root>
{{ENV_COMMAND}} delete <slug>
git worktree remove {{WORKTREE_DIR}}/<slug>
```

Or `/worktree-remove <slug>`, which checks for unpushed work first. Both commands are needed,
in that order — removing only the directory leaks containers and holds the slot. The remote
branch is left alone so any open PR stays valid.

### Notes

- Run git commands from **inside** the worktree, not the main checkout. Mixing the two is the
  main way commits land on the wrong branch.
- A fresh worktree has no dependencies installed — worktrees share git objects, not build
  artifacts. `{{INSTALL_COMMAND}}` first, before anything else.
- The ceiling is {{MAX_WORKTREES}} concurrent worktrees; `{{ENV_COMMAND}} start` errors clearly
  when the bands are exhausted.
