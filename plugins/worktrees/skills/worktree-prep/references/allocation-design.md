# Allocation design

The language-agnostic specification for the environment tool: the slot model, the registry,
the descriptor, and the teardown contract. Implement this shape in whatever stack the repo
uses — `stack-recipes.md` covers the syntax and placement per language.

## Contents

1. [The slot model](#the-slot-model)
2. [Port bands](#port-bands)
3. [The registry](#the-registry)
4. [Concurrency](#concurrency)
5. [The descriptor](#the-descriptor)
6. [Command contracts](#command-contracts)
7. [Seeding isolated state](#seeding-isolated-state)
8. [Sizing and ceilings](#sizing-and-ceilings)

---

## The slot model

Each worktree holds one small non-negative integer, its **slot**. Everything the worktree needs
is a pure function of the slot and the slug:

```
slot   = 3
slug   = "tunnel-retry"

web_port        = 3100 + 3   = 3103
api_port        = 4100 + 3   = 4103
postgres_port   = 5500 + 3   = 5503
compose_project = "myapp-tunnel-retry"
database        = "myapp_tunnel_retry"
state_dir       = "<worktree>/.worktree"
```

Two properties make this worth the small amount of bookkeeping:

**The footprint is enumerable.** Teardown can destroy everything the worktree created, because
every resource is derivable from `(slot, slug)`. A design that allocates resources ad hoc as
services start cannot promise that — you end up with orphaned volumes nobody can attribute.

**Values are stable and readable.** Port `3117` unambiguously belongs to slot 17. Restarting
does not move it, so bookmarks, editor launch configs, and browser sessions survive. Dynamic
"find any free port" allocation loses both properties for no gain.

### Slot 0 is the main checkout

Reserve slot 0 and map it to the repo's **existing default values** — the ports and names the
repo already uses today. Consequences worth stating to the user:

- Nobody who never touches worktrees notices this change at all.
- The migration is additive: no existing README, launch config, or bookmark breaks.
- The main checkout is a real competitor for ports, and giving it a slot means the tool knows
  about it instead of colliding with it.

This is the default and should not be re-argued per repo. The case against it is genuine —
leaving `main` on port 3000 preserves the muscle memory that produced the original collision —
but it loses to the migration cost: uniform allocation invalidates every bookmark, editor launch
config, README URL and shell alias in the repo on day one, for a benefit that is behavioural
rather than technical.

The uniform alternative — every checkout including main uses `BASE + slot` — is the right choice
in exactly one situation: scripts or CI that must treat main and worktrees identically, where
carrying the slot-0 special case costs more than the one-time migration. Choose it deliberately
in that case, say so in the report, and be consistent.

### Slot assignment

`start` on an unregistered worktree takes the **lowest free slot**, not the next one ever issued.
Reuse keeps slots dense and ports readable; monotonic issuance drifts to `port 3247` after a few
months of churn. Free slots come back when `delete` removes an entry.

---

## Port bands

One contiguous band per service, each wide enough for the realistic maximum of concurrent
worktrees (16–32; almost nobody runs more than 8).

```
web       3100–3131
api       4100–4131
postgres  5500–5531
redis     6400–6431
debugger  9300–9331
```

Choosing bases:

- Start clear of everything the scan found, and clear of the well-known defaults for whatever
  else the developer runs (5432, 6379, 3000, 8080, 27017).
- Avoid the ephemeral port range the OS allocates outbound connections from — 49152–65535 on
  most systems, and from 32768 on Linux. A dev server bound there will intermittently lose to
  an outbound socket, and the failure is maddeningly intermittent.
- Keep the last two digits equal to the slot across every band. Then all of slot 7's ports end
  in `07`, and reading `docker ps` or `lsof` output takes no thought.

---

## The registry

One JSON (or YAML) file, host-global:

```
~/.<project>/worktrees.json
```

Host-global because its entire job is coordinating **across** worktrees. A repo-local file would
live inside one worktree and be invisible to the others.

```json
{
  "version": 1,
  "worktrees": {
    "tunnel-retry": {
      "slot": 3,
      "path": "/Users/me/repos/myapp/.claude/worktrees/tunnel-retry",
      "branch": "claude/tunnel-retry",
      "created_at": "2026-08-06T04:12:00Z",
      "description": "retry budget for the tunnel reconciler",
      "ports": { "web": 3103, "api": 4103, "postgres": 5503 },
      "compose_project": "myapp-tunnel-retry",
      "database": "myapp_tunnel_retry",
      "seeded_from": "myapp_dev"
    }
  }
}
```

Keyed on the **worktree directory name**, not the branch. Branches get renamed, deleted, and
reused; the directory name is stable and is what the person actually types.

Store the absolute path — it is what `list` and `doctor` use to detect entries whose worktree has
been removed. If the file holds credentials, write it `0600`.

---

## Concurrency

Two agents will run `start` simultaneously; that is the whole point of worktrees. Without care,
both read "slots 0,1 taken", both pick 2, and one silently wins.

- **Re-read immediately before allocating.** Never allocate from a registry loaded earlier in
  the process.
- **Write atomically**: serialise to `worktrees.json.tmp` in the same directory, then rename over
  the target. Rename is atomic on every platform that matters, so a crash mid-write cannot leave
  a truncated registry.
- **Hold a lock across read-modify-write** where the stack makes it easy — an exclusive-create
  lockfile (`O_EXCL`) with a stale-lock timeout is enough. Skipping this leaves a small race
  window; taking it removes the class of bug entirely.
- **Verify before committing.** After picking a slot, check the ports are actually free (attempt
  a bind, release it). If one is taken, pick the next slot rather than failing — something outside
  the registry may hold it.

---

## The descriptor

`start` writes a machine-readable file at the **worktree root** holding every allocated value.
This is the contract between the tool and everything else in the repo: no other file hardcodes a
port or a name; they all read this.

Use a format the repo already parses (`.json` in a Node repo, `.yaml` where the repo uses YAML).
Gitignore it — it is per-worktree, per-machine state.

```json
{
  "slug": "tunnel-retry",
  "slot": 3,
  "worktree_path": "/Users/me/repos/myapp/.claude/worktrees/tunnel-retry",
  "branch": "claude/tunnel-retry",
  "urls": {
    "web": "http://localhost:3103",
    "api": "http://localhost:4103"
  },
  "ports": { "web": 3103, "api": 4103, "postgres": 5503 },
  "compose_project": "myapp-tunnel-retry",
  "database_url": "postgres://localhost:5503/myapp_tunnel_retry",
  "state_dir": "/Users/me/repos/myapp/.claude/worktrees/tunnel-retry/.worktree",
  "shared_resources": [
    {
      "name": "Stripe test account",
      "why": "one sandbox account for the whole team; per-worktree accounts are not available",
      "impact": "test charges and webhooks are visible to every worktree and every teammate"
    },
    {
      "name": "pnpm store (~/.pnpm-store)",
      "why": "content-addressed and concurrency-safe; isolating it would multiply setup time",
      "impact": "none — shared deliberately"
    }
  ]
}
```

The `shared_resources` block is not decoration. It is how a person or an agent working inside the
worktree learns which of their actions escape it. Distinguish the two reasons for sharing —
*deliberate* (safe) and *unavoidable* (be careful) — because they call for different behaviour.

Emit a shell-sourceable form too (`.worktree/env.sh` with `export MYAPP_WEB_PORT=3103`) when the
repo's workflow is shell-driven; it costs three lines and removes a lot of friction.

---

## Command contracts

**`start [--description <text>] [--dry-run]`**

1. Confirm cwd is inside a git worktree of this repo; error clearly if not.
2. Derive the slug from the worktree directory name.
3. Load the registry, allocate or look up the slot.
4. Materialise every isolated resource: create the database, start containers with the namespaced
   project, create the state directory.
5. Write the descriptor and the registry entry.
6. Print the URLs.

Idempotent — a second run reuses the slot and reconciles rather than duplicating. Safe to run
after a machine reboot, when the registry entry survives but nothing is running.

`--dry-run` computes and prints the whole allocation without writing the registry, the
descriptor, or creating anything. It exists because the obvious way to check that the scheme
works is to run it, and doing that leaves real containers, real registry entries and real
directories under `$HOME` — often on a machine where the person was only trying to look. It also
gives Phase 5 a way to compare two worktrees' allocations before committing to either.

**`list [--json]`** — every entry: slug, slot, ports, path, whether the directory still exists,
whether anything is currently running.

**`delete <slug> [--force] [--keep-data]`**

Works from the registry alone; the worktree directory may already be gone. Destroys containers,
volumes, networks, the database, the state directory — then removes the entry. Idempotent, because
finishing a half-failed teardown is the common case. Does **not** touch the git worktree or the
branch: the branch usually has an open PR pointing at it, and removing the working tree is
`git worktree remove`'s job.

Two corollaries of "works from the registry alone" that are easy to violate by accident:

**No command line may name a path inside the worktree.** `docker compose -f
<worktree>/docker-compose.yml -p <project> down -v` reads as correct and passes a live test —
but in the scenario this command exists for, that file is gone. Use `-p <project>` alone and let
Docker resolve by project label, or keep a copy of anything you need under the registry. Every
argument must come from the registry entry, not from the directory.

**Do not swallow non-zero exits.** A teardown that ignores a failed step and still prints
"✓ freed slot 3" leaks containers silently and removes the registry entry that would have let
anyone find them. Check each step; on failure, report which resource survived and leave the
registry entry in place so a re-run can finish the job.

**`doctor`** — reports drift without fixing it: registry entries whose path is gone, worktrees with
no entry, ports held by a foreign process, containers matching the project prefix with no entry.
Cheap to write and the first thing to run when something behaves oddly.

---

## Seeding isolated state

When a worktree's database should start from the developer's existing data:

- **sqlite** — `sqlite3 <source> ".backup '<dest>'"`. Atomic and safe against a live writer;
  a plain file copy is not.
- **postgres** — `createdb -T <source> <dest>` when no session is connected to the source, else
  `pg_dump <source> | psql <dest>`.
- **mysql** — `mysqldump <source> | mysql <dest>`.

Seed **after** the store exists and migrations have run, so schema version and data agree.

A seeded copy is a snapshot taken at creation. It diverges from the source immediately. Record
`seeded_from` and the timestamp in the descriptor, and state the divergence in the tool's output —
otherwise someone will reasonably assume they are looking at live data.

---

## Sizing and ceilings

Say the ceiling out loud in the report: with 32-wide bands, 32 concurrent worktrees. Have `start`
fail with a clear message when the bands are exhausted, naming which band ran out — far better
than a mysterious bind error at slot 33.

Consider what each worktree actually costs before widening the bands: a per-worktree Postgres
container is ~100 MB of RAM, a per-worktree VM is ~2 GB. The practical ceiling is usually memory,
not port space.
