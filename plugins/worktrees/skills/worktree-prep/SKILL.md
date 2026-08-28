---
name: worktree-prep
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, TodoWrite
description: >
  Prepares a repository for parallel development across multiple git worktrees. Audits the repo for
  every resource that concurrent worktrees would fight over — host ports, Docker container/volume/network
  names, databases and state files under $HOME, sockets, lockfiles, OS daemons, external namespaces —
  then designs a slot-based allocation scheme, generates a per-worktree environment tool written in the
  repo's own stack, wires it into the repo's entrypoints and agent docs so a worktree created by Claude
  Code's WorktreeCreate hook gets its environment started at the right point, and proves it by running
  two worktrees side by side. Use this skill whenever the user talks about worktrees together with setup,
  isolation, clashing, or parallelism — including "make this repo work with worktrees", "get this repo
  ready for worktrees", "my worktrees fight over port 3000", "set up isolated dev environments per
  branch", "I want to run several Claude sessions on this repo at once", "each worktree needs its own
  database", "add worktree support", or "why do my parallel agents keep breaking each other". Also use
  it when someone hits EADDRINUSE, "container name already in use", or unexplained state bleeding
  between branches while running more than one checkout. Do not use it to create a single worktree in a
  repo that has already been prepared — Claude Code's WorktreeCreate hook covers that.
---

# Worktree Prep

Git worktrees isolate **files**. That is all they isolate.

Everything else the repo touches is still one shared thing that every worktree grabs at
once: TCP port 3000, the container called `api`, the sqlite file at `~/.myapp/db`, the
lockfile in `/tmp`, the launchd job, the staging S3 bucket. Two worktrees running at the
same time collide on all of it. The loud collisions (`EADDRINUSE`, "container name already
in use") are the lucky ones — the quiet collisions are two branches writing to the same
database, and those get diagnosed as flaky tests for a week.

The job of this skill is to give every worktree its own copy of, or its own name for,
every one of those resources — and to be honest in writing about the ones that genuinely
cannot be isolated.

The end state: someone runs one command in a fresh worktree and gets a complete,
non-colliding environment; a second worktree started a minute later gets a different one;
tearing either down leaves nothing behind.

---

## Phase 1 — Inventory the clash surface

You cannot isolate what you have not enumerated, and the resources that bite hardest are
the ones nobody remembers exist. Start from evidence.

**Run the scanner.** It walks the repo and reports the classes of resource that clash:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/worktree-prep/scripts/scan_shared_resources.py <repo-root>
```

It prints a repo profile (languages, package manager, container tooling, task runners,
existing worktree tooling) followed by findings grouped by category, with `*` marking
findings in dev-entrypoint files. `--json` gives the same data structured; `--max-per-category N`
widens the output when a category looks interesting.

**Then read the dev entrypoints yourself.** The scanner is regex over static text — it
cannot see a port computed at runtime, a container name built from a variable, or a
temp directory chosen by a library. Open and actually read:

- every `docker-compose*.yml` / `compose.yml`, and the `Dockerfile`
- the task runner: `Makefile`, `justfile`, `Taskfile.yml`, or `package.json` scripts
- the app's startup path — wherever it binds a listener or opens its store
- `.env`, `.env.example`, and any config the app reads at boot
- the test setup, which is where shared databases hide most often

**Then look at what is actually running**, because a live process is ground truth:

```bash
lsof -iTCP -sTCP:LISTEN -P -n | head -40      # macOS / Linux: who holds which port
docker ps -a --format '{{.Names}}\t{{.Ports}}'
docker volume ls && docker network ls
```

Sort everything you find into three buckets. This split, not the raw list, is the real
output of this phase:

| Bucket | Meaning | Examples |
|---|---|---|
| **Must isolate** | Concurrent use breaks or corrupts | host ports, container/volume/network names, dev + test databases, sockets, pidfiles, per-app state under `$HOME` |
| **Share on purpose** | Isolating costs a lot and buys nothing; these are read-mostly | package manager caches, base Docker images, downloaded toolchains, the git object store itself |
| **Cannot isolate** | Genuinely singular, or lives in a system you do not control | a shared staging DB, a single OAuth callback URL, a cloud account's global namespace, a licensed device |

The third bucket matters as much as the first. A resource that cannot be isolated should
be **named in the generated environment descriptor** so that whoever — human or agent —
works in that worktree knows their writes are global. Silence here is what produces the
"I thought I was in a sandbox" incident.

Read `references/clash-catalogue.md` for the full class-by-class catalogue: what each
resource class is, how to detect it, and the standard isolation technique for it. Reach
for it when the scan turns up a category you have not isolated before.

---

## Phase 2 — Design the allocation, and get sign-off

Read `references/allocation-design.md` before writing anything. It specifies the slot
model, the registry format, the descriptor format, and the teardown contract in
language-agnostic terms — the design is the same in every stack, only the syntax changes.

The short version, which you should be able to justify to the user:

**One slot per worktree.** Each worktree gets a single small integer. Every resource it
needs is derived from that integer — `port = BASE + slot`, `container = <project>-<slug>`,
`db = <state-dir>/<slug>.sqlite`. One number to allocate, one number to free, and a
worktree's entire footprint is predictable from it. The alternative — hunting for a free
port per service at boot — produces URLs that move between restarts and a footprint you
cannot enumerate at teardown.

**Allocation is persisted, not recomputed.** A registry keyed by slug lives at
`~/.<project>/worktrees.json` (host-global, because its whole purpose is coordinating
*across* worktrees — a repo-local file would sit inside one of them). Re-running `start`
returns the same slot, so the URL a person bookmarked still works tomorrow.

**Slot 0 is the main checkout.** Map slot 0 to the repo's existing default ports and names,
so nothing changes for someone who never uses a worktree, and the migration is additive.
Slots 1..N get `BASE + slot`, with `BASE` chosen clear of everything the scan found.

Treat this as settled rather than a per-repo decision. There is a real argument the other way —
if `main` keeps port 3000 people keep typing `localhost:3000`, so the habit that caused the
original collision survives the migration — but it loses to the migration cost: uniform
allocation invalidates every bookmark, launch config, README URL and shell alias on day one for
a benefit that is behavioural rather than technical. Reopen it only if the user asks, or if the
repo has CI or scripts that must treat main and worktrees identically; `allocation-design.md`
covers that alternative.

**One band per service.** Give each service a contiguous range wide enough for the number
of worktrees anyone will realistically run at once — 16 or 32 is plenty. Bands make the
port readable: `3117` is worktree slot 17's web port, at a glance.

Now present the plan to the user **as a table, before generating code**, because the
share-versus-isolate calls in the second and third buckets are theirs to make, and a wrong
call there means regenerating everything:

```
Resource              Current            Per-worktree                  Bucket
--------------------  -----------------  ----------------------------  -----------
web server port       3000               3100 + slot                   isolate
postgres host port    5432               5500 + slot                   isolate
compose project       myapp              myapp-<slug>                  isolate
dev database          myapp_dev          myapp_<slug>                  isolate, seeded from dev
test database         myapp_test         myapp_test_<slug>             isolate, empty
uploads dir           ~/.myapp/uploads   <worktree>/.worktree/uploads  isolate
pnpm store            ~/.pnpm-store      unchanged                     share (read-mostly)
Stripe test account   shared             unchanged                     CANNOT ISOLATE
```

Ask for confirmation in one consolidated question — flag the specific rows you are least
sure about rather than walking every line. Then build.

---

## Phase 3 — Build the environment tool

Write it in the repo's own stack: TypeScript for a Node repo, Go for a Go repo, Python for
a Python repo. It lives alongside the code it manages, gets the repo's linting and types,
and a contributor can read it without installing anything new. `references/stack-recipes.md`
covers where the file goes, how to wire the entrypoint, and the idioms per stack — read the
section for the stack you found in Phase 1.

Four commands carry the whole lifecycle:

- **`start`** — allocate or look up the slot, materialise every isolated resource, write the
  descriptor, print the URLs. Idempotent: running it twice is a no-op plus a rebuild.
- **`list`** — every registered worktree, its slot, its URLs, whether its directory still exists.
- **`delete <slug>`** — destroy everything `start` created, then drop the registry entry.
- **`doctor`** — report drift: registry entries whose worktree is gone, slots whose ports are
  held by something else, worktrees with no registry entry.

`start` also needs a `--dry-run` that prints the full allocation without writing the registry or
creating anything. The obvious way to check the scheme works is to run it, and doing that leaves
real containers and real directories under `$HOME` on a machine where someone may only have been
looking.

Four properties are easy to leave out and painful to add later:

**Concurrency-safe allocation.** Two agents will run `start` at the same time — that is the
entire point of worktrees. Re-read the registry immediately before choosing a slot, and write
it back via temp-file-plus-atomic-rename so a crash mid-write cannot corrupt it. A lockfile
around the read-modify-write is better still.

**Teardown from the registry alone.** People run `git worktree remove` first and clean up
after. `delete` must therefore work with the worktree directory already gone — everything it
needs to destroy comes from the registry entry, never from files inside the worktree. It must
also be idempotent, because the second half of a half-failed teardown is the common case.

**A descriptor at the worktree root.** `start` writes a machine-readable file — JSON, YAML,
whatever the repo already parses — holding every allocated value plus the known-shared list.
This file is the contract: everything else in the repo reads it instead of hardcoding. Add it
to `.gitignore`; it is per-worktree, per-machine state.

**A loud unknown-slug error.** `start` in a directory that is not a git worktree, or `delete`
on a slug with no registry entry, should say so plainly rather than half-succeeding.

---

## Phase 4 — Wire it into the repo

A generated tool nobody invokes changes nothing. Five wiring steps; the third is the one that
gets half-done, and the fifth is the one that decides whether the tool is ever run at all.

**1. Native entrypoint.** `"worktree-env": "tsx tools/worktree-env.ts"` in package.json scripts,
a `worktree-env` Makefile target, `go run ./cmd/worktree-env` — whatever matches how the repo's
other commands are invoked.

**2. `.gitignore`.** If the repo has a `.gitignore`, append the worktree directory and every
per-worktree file the tool generates:

```gitignore
# git worktrees and their per-worktree environment
.claude/worktrees/
.worktree-env.json
.worktree/
```

Use `.claude/worktrees/` unless Phase 1 found the repo already keeping worktrees somewhere
else — follow the existing convention rather than introducing a second one. Substitute the
real descriptor filename and state-directory name you chose in Phase 3.

This matters more than it looks: worktrees created *inside* the repo show up as a large block
of untracked files in every `git status`, and sooner or later someone commits one. The
descriptor is per-worktree, per-machine state and must never be committed — a checked-in
descriptor hands one worktree's ports to whoever clones next.

Check before writing, so re-running the skill does not duplicate entries. If the repo has
**no** `.gitignore`, say so and ask rather than creating one — a repo without one is often
relying on a global excludes file or a parent `.gitignore`, and a new file is a change to the
repo's conventions that the user should agree to.

**3. Route the hardcoded values through the descriptor.** Take the scanner's *distinct ports*
list and every name from the isolate bucket, grep each one, and change every live reference to
read from the descriptor. Miss one and the isolation is theatre: the app comes up on its own
port while a test helper, a seed script, or a Playwright config still dials 3000 and lands in
another worktree. Docs and READMEs count too — a stale port in a README is how a hardcoded
value gets reintroduced six months later.

**4. Repo docs.** Copy `assets/worktree-docs-section.md` into the repo's `CLAUDE.md` /
`AGENTS.md` (adapting the placeholders), so future sessions in this repo know the workflow
exists, know the allocation is per-worktree, and know what is still shared.

**5. Say where the environment step happens.** The environment tool has a correct order of
operations that nobody remembers under time pressure: `start` runs *after* the install step and
*inside* the new worktree; `delete` runs *before* the worktree directory goes away. Get either
backwards and you leak a slot, leak containers, or bring a worktree up on the main checkout's
ports.

That ordering belongs in the repo's docs (step 4 above), not in a skill. Creating a worktree is
not the repo's decision to make. Claude Code has `WorktreeCreate` and `WorktreeRemove` hooks, and
where one is registered Claude Code delegates creation to it and never falls back to `git worktree
add`. `wt claude install` registers one machine-wide, covering every repository on the machine. A
skill that described a `git worktree add` of its own would be describing something that never
runs.

So write the docs for a worktree that the hook has already created. State two things explicitly:

- **The environment step is not automatic.** The hook creates the directory and stops. Whoever
  arrives in a fresh worktree runs the install step and `{{ENV_COMMAND}} start` themselves, and
  until they do the worktree shares the main checkout's ports and state.
- **Teardown is two things in order.** `{{ENV_COMMAND}} delete <slug>` from the repo root
  releases the environment; removing the worktree directory is separate and comes second.
  Removing only the directory leaks containers and holds the slot, and the leak stays invisible
  until slots run out.

**Do not install a `worktree-create` or `worktree-remove` skill into the repo.** If an earlier run
of this skill left one at `.claude/skills/worktree-create/` or `.claude/skills/worktree-remove/`,
say so and offer to delete it. It competes with the hook, and the two have already drifted apart
on which branch a worktree is cut from and on what happens when the branch already exists.

### If the machine has wt's hooks installed

Check for them, because the interaction is confusing and worth naming up front:

```bash
grep -l 'WorktreeCreate' ~/.claude/settings.json ~/.claude/settings.local.json 2>/dev/null
```

wt's `WorktreeCreate` hook treats a repository as adopted only when there is a `wt.yaml` at its
root. A repo prepared by *this* skill has no `wt.yaml` — it has this skill's own generated
environment tool instead — so the hook gives it a plain worktree under `.claude/worktrees/<slug>`,
starts no environment, and prints a notice suggesting `/worktree-onboarding`.

Both halves of that need to reach the repo's docs. The worktree directory the hook actually uses
is `.claude/worktrees/<slug>`, so use that as `{{WORKTREE_DIR}}` rather than inventing a second
location the hook will not honour. And record that the `/worktree-onboarding` suggestion should be
declined: taking it up adopts the repo into wt, which would give it a second environment tool
allocating the same ports as the first.

---

## Phase 5 — Prove it with two live worktrees

A scheme that looks right on paper and dies on `docker: name already in use` is worth nothing,
and this is the phase most likely to get skipped because it is slow. Do it anyway — it is the
only step that distinguishes a working setup from a plausible one.

```bash
git worktree add .claude/worktrees/probe-one -b wt-probe-one
git worktree add .claude/worktrees/probe-two -b wt-probe-two
# run the tool's start command in each, then check:
```

Verify, with commands rather than assertion:

1. **Both start clean.** The second one does not error, and does not silently reuse the first's slot.
2. **The allocations differ.** Compare the two descriptors — every isolated value is distinct.
3. **Both run at once.** Both listen; `curl` each health endpoint; `docker ps` shows two
   independent sets of containers with distinct names.
4. **State does not bleed.** Write something in worktree one — a row, a file, a user — and
   confirm it is absent in worktree two. This is the check that catches a missed database.
5. **Teardown is complete.** Delete both, then confirm: no leftover containers, volumes, or
   networks; ports released; registry entries gone; `doctor` clean.

Then remove the probe worktrees and branches. If any check fails, fix the tool and re-run the
whole sequence — a partial pass usually means one resource class was missed entirely, not that
the design is wrong.

---

## Phase 6 — Report

Tell the user what now exists and what the workflow is:

- the command they run, and what a fresh worktree costs in time
- how a worktree gets made here: Claude Code's `WorktreeCreate` hook creates the directory, and
  the environment step is theirs to run afterwards — name the two commands and their order
- the allocation table as built, including the share-on-purpose rows
- **the cannot-isolate list, restated** — this is the part they need to remember
- the ceiling: how many concurrent worktrees the bands allow
- anything you deliberately left out, and why

**Separate what you proved from what you reasoned about.** Say plainly which checks you ran and
which you could not — a missing dependency, no Docker, no network — and what therefore remains
unverified. This is easy to blur, because a summary describing a concurrency test and a summary
describing a concurrency test *that exists* read identically. The person acting on your report
is deciding how much to trust the setup before running it in anger; an honest "the two-worktree
proof is written up in VERIFICATION.md but I could not execute it" is far more useful to them
than a confident sentence that turns out to have been aspirational.

---

## Things that go wrong

- **Isolating the package cache.** `~/.pnpm-store`, the Go module cache, `~/.cargo` — these are
  content-addressed and read-mostly. Isolating them turns a 20-second worktree setup into a
  five-minute one and buys nothing.
- **Forgetting the main checkout competes.** It is a worktree too, and it is usually already
  running on the default ports. Slot 0 exists for exactly this.
- **Slugs derived from branch names.** Branches get renamed and deleted; the worktree directory
  name is stable and is what the person actually types. Key the registry on the directory name.
- **Test databases left shared.** Two worktrees running their suites concurrently truncate each
  other's tables between assertions. It presents as flakiness and costs days to attribute.
- **A descriptor nothing reads.** Writing the file is the easy half; Phase 4 step 3 is the half
  that makes it real.
- **Teardown that only works from inside the worktree.** By the time someone cleans up, the
  directory is often already gone.
- **Isolating everything, including the things that cannot be.** Where a resource is genuinely
  shared, say so in the descriptor. A worktree that claims full isolation and does not have it is
  more dangerous than one that is honest about the gap.
