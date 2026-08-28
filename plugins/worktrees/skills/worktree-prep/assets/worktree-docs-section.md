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

Ask Claude Code for a worktree, or run `git worktree add` yourself. Either way the directory is
all you get — **the environment is a separate step and it is not automatic.** From inside the new
worktree:

```bash
cd {{WORKTREE_DIR}}/<slug>
{{INSTALL_COMMAND}}
{{ENV_COMMAND}} start --description "<what this worktree is for>"
```

The order matters. `{{ENV_COMMAND}} start` before `{{INSTALL_COMMAND}}`, or run from the main
checkout instead of the worktree, does not do what it looks like it does. Until `start` has run,
the worktree shares the main checkout's ports and state, which is the problem worktrees were
supposed to solve.

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

Release the environment **before** the worktree directory goes away:

```bash
cd <repo-root>
{{ENV_COMMAND}} delete <slug>
git worktree remove {{WORKTREE_DIR}}/<slug>
```

Both are needed, in that order. Removing only the directory leaks containers and holds the slot,
and nothing complains until the bands run out. Check for uncommitted and unpushed work first —
`git worktree remove` refuses on a dirty tree, and that refusal is signal rather than an
obstacle, so do not reach for `--force`. The remote branch is left alone so any open PR stays
valid.

If Claude Code removed the worktree for you, `{{ENV_COMMAND}} delete <slug>` still has to be run
afterwards, and `{{ENV_COMMAND}} doctor` will show the orphaned entry until it is.

### Notes

- Run git commands from **inside** the worktree, not the main checkout. Mixing the two is the
  main way commits land on the wrong branch.
- A fresh worktree has no dependencies installed — worktrees share git objects, not build
  artifacts. `{{INSTALL_COMMAND}}` first, before anything else.
- The ceiling is {{MAX_WORKTREES}} concurrent worktrees; `{{ENV_COMMAND}} start` errors clearly
  when the bands are exhausted.
- If creating a worktree prints a notice suggesting `/worktree-onboarding`, **decline it.** That
  notice comes from worktree-manager's machine-wide hook, which does not recognise this repo
  because there is no `wt.yaml` here. This repo has its own environment tool — `{{ENV_COMMAND}}` —
  and adopting it into worktree-manager as well would give it two allocators handing out the same
  ports.
