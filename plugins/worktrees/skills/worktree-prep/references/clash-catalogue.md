# Clash catalogue

Every class of resource that concurrent git worktrees fight over, how to spot it, and the
standard way to isolate it. Use this when the scan turns up a category you have not handled
before, or when you suspect the scan missed something.

## Contents

1. [Host ports](#1-host-ports)
2. [Container and orchestrator objects](#2-container-and-orchestrator-objects)
3. [Databases and stateful stores](#3-databases-and-stateful-stores)
4. [Filesystem paths outside the working tree](#4-filesystem-paths-outside-the-working-tree)
5. [Single-holder files: locks, pidfiles, unix sockets](#5-single-holder-files-locks-pidfiles-unix-sockets)
6. [Host-global daemons and virtual machines](#6-host-global-daemons-and-virtual-machines)
7. [OS-level registrations](#7-os-level-registrations)
8. [External and cloud namespaces](#8-external-and-cloud-namespaces)
9. [Build outputs and caches](#9-build-outputs-and-caches)
10. [Things that look like clashes but are not](#10-things-that-look-like-clashes-but-are-not)

---

## 1. Host ports

The first thing that breaks and the easiest to fix.

**Spot it:** compose `ports:` mappings, `EXPOSE`, `.listen(`, `--port`, `*_PORT` env vars,
`localhost:NNNN` in configs and tests, dev-server config (`vite.config`, `next.config`,
`webpack.config`), debugger ports (`--inspect=9229`, `dlv --listen`), and anything in the
scanner's *distinct ports* summary.

**Isolate:** `port = BASE + slot`. Give each service its own band. Do not forget:

- **Debugger and profiler ports** — `9229`, `2345`, `6060`. Two debuggers collide as surely
  as two servers, and the failure is confusing because the app itself starts fine.
- **Hot-reload / HMR websocket ports**, which are often separate from the HTTP port.
- **Ports the app dials rather than binds** — if the frontend hardcodes `http://localhost:4000`
  for the API, isolating the API's bind port without updating the dialer just breaks it.
- **"Reuse it if something is already listening" behaviour.** Playwright's
  `reuseExistingServer`, `webpack-dev-server`'s port auto-increment, `docker compose up` against
  an already-running project, and any "is it up? then skip starting it" check. These are worse
  than a plain clash: the second worktree does not error, it *attaches to the first worktree's
  server* and reports success for the wrong branch. A green e2e run against another branch's
  code is the most expensive failure in this whole catalogue, because nothing looks wrong.
  Isolate the port, and where the tool supports it, make the health check assert identity — have
  `/health` return the slug and have the test fail if it is not the expected one.

**Note:** a container's *internal* port never clashes; only the host side of a `HOST:CONTAINER`
mapping does. Leave the container side alone — remapping both is a common over-correction that
breaks intra-network service discovery.

---

## 2. Container and orchestrator objects

Docker names are global per daemon, not scoped to a directory.

**Spot it:** `container_name:`, `docker run --name`, top-level `name:` under compose
`volumes:`/`networks:`, `docker volume create`, fixed image tags, k8s `namespace:`,
`kind create cluster --name`.

**Isolate:**

- **Best: delete `container_name:` entirely and set `COMPOSE_PROJECT_NAME=<project>-<slug>`.**
  Compose then namespaces containers, volumes, *and* networks automatically. An explicit
  `container_name` overrides that namespacing and re-introduces the clash — which is exactly
  why it is the single most common cause of "container name already in use" in worktree setups.
- Where a name must be explicit, prefix it with the slug.
- Fixed image tags (`myapp:dev`) are shared, which is usually fine — images are content, not
  runtime. They clash only if two worktrees build different code to the same tag and race.
  Tag with the slug if builds are concurrent.
- Kubernetes: one namespace per worktree, named for the slug.

---

## 3. Databases and stateful stores

The dangerous class, because the failure is silent. Two worktrees writing to one database do
not error — they corrupt each other's assumptions and it surfaces later as a bug hunt.

**Spot it:** `DATABASE_URL`, `POSTGRES_DB`, `MYSQL_DATABASE`, `REDIS_URL`, `MONGODB_URI`,
`*.sqlite` / `*.db` paths, migration config, ORM config, and — critically — the **test**
configuration, which frequently points at a fixed database name that every worktree's test
run truncates.

**Isolate**, choosing per store:

| Mode | When | How |
|---|---|---|
| **Isolated + empty** | Test databases; anything migrations can rebuild | Fresh DB named `<base>_<slug>`, run migrations |
| **Isolated + seeded** | Dev databases where the developer wants their existing data | Copy the shared store at creation time (`sqlite3 src ".backup dest"`, `pg_dump \| psql`) |
| **Shared, declared** | A store you cannot duplicate — shared staging, a licensed instance | Leave it; record it in the descriptor's known-shared list |

A seeded copy is a **snapshot, not a mirror** — it diverges from the source the moment either
side is written to. Say so in the descriptor, or someone will treat it as live.

Redis deserves a specific note: a separate *database index* (`redis://host/3`) is a weak
boundary because `FLUSHALL` and many keyspace-wide commands ignore it. Prefer a separate
instance on its own port, or at minimum a per-slug key prefix.

---

## 4. Filesystem paths outside the working tree

Shared by construction. A worktree gives you an isolated `./`, and nothing else.

**Spot it:** `os.homedir()`, `Path.home()`, `os.path.expanduser`, `UserHomeDir()`, `~/...`,
`$HOME/...`, `%APPDATA%`, `XDG_*_HOME`, `/tmp/<fixed-name>`, `/var/run/...`, `/usr/local/var/...`.

**Isolate**, in order of preference:

1. **Move it into the worktree** — `<worktree>/.worktree/<thing>`, gitignored. Simplest to
   reason about, and `git worktree remove` cleans it up for free.
2. **Key the path by slug** — `~/.myapp/worktrees/<slug>/...`. Necessary when the path must
   survive the worktree, or when a tool insists on living under `$HOME`.
3. **Point an env var at it** and set that var from the descriptor.

Watch for paths the *framework* chooses rather than your code: Next.js `.next`, Vite's
`node_modules/.vite`, pytest's `.pytest_cache`, Playwright's browser downloads. Anything inside
the worktree is already isolated. Anything the tool resolves to `$HOME` is not.

---

## 5. Single-holder files: locks, pidfiles, unix sockets

First worktree in wins; the rest fail, hang, or — worst — attach to the first one's daemon and
appear to work.

**Spot it:** `*.sock`, `*.pid`, `*.lock`, `flock`, `O_EXLOCK`, `proper-lockfile`, any
"is it already running?" check.

**Isolate:** move the path into the worktree, or suffix it with the slug. Two specific traps:

- A **socket path length limit** of ~104 bytes on macOS. `<long-worktree-path>/.worktree/foo.sock`
  can exceed it and fail with a confusing `EADDRINUSE`-adjacent error. Keep socket paths short —
  `/tmp/<project>-<slug>.sock` is often the pragmatic answer even though `/tmp` is shared, because
  the slug makes it unique.
- **Single-instance guards** that check for a running process by name rather than by pidfile.
  These need the process name or the check itself to become slug-aware.

---

## 6. Host-global daemons and virtual machines

One per machine, unless explicitly given per-instance identity.

**Spot it:** `colima`, `lima`, `minikube`, `kind`, `multipass`, `vagrant`, `wsl --import`,
`brew services`, a Docker Desktop dependency, a local Kafka/Postgres/Redis installed natively.

**Isolate:** most of these support named instances — `colima start --profile <slug>`,
`minikube -p <slug>`, `wsl --import <project>-<slug>`. A per-worktree VM gives near-total
isolation (its own daemon, its own port space) at the cost of RAM and a slow first start; that
tradeoff is worth it when the stack is large, and overkill when it is one server and one database.

If the daemon stays shared, isolation drops to naming discipline within it — which is section 2's
problem, and is usually enough.

---

## 7. OS-level registrations

Rarely present, but total blockers when they are.

**Spot it:** `.plist` / `launchctl`, `systemd` units, `schtasks`, `/etc/hosts` edits, keychain
or credential-manager entries (`security add-generic-password`, `keytar`, `keyring`), certificate
trust stores, custom URL scheme handlers, mDNS/Bonjour service names.

**Isolate:** include the slug in the label (`com.myapp.<slug>.agent`, `myapp-<slug>.local`,
`<slug>.myapp.localhost`). Where the registration is genuinely singular — a system certificate,
a claimed URL scheme — it belongs in the cannot-isolate list. Do not have `delete` remove a
system-wide registration that other worktrees still depend on.

---

## 8. External and cloud namespaces

Systems where you do not own the namespace.

**Spot it:** S3 bucket names, k8s namespaces, queue/topic/subject names, search index names,
webhook endpoints, OAuth callback URLs, tunnel hostnames (ngrok, cloudflared), third-party
sandbox accounts, feature-flag environments.

**Isolate where the system allows it:** prefix by slug. Queue subjects, topics, bucket key
prefixes, table prefixes, and k8s namespaces all take this well.

**Where it does not:** a single OAuth callback URL, one shared payment-provider test account,
one staging database. These go in the cannot-isolate list, and the descriptor should state what
that means concretely — "webhooks from the Stripe test account are delivered to whichever worktree
is currently tunnelled; only one worktree can receive them at a time".

---

## 9. Build outputs and caches

Mostly a non-problem, occasionally a sharp one.

**Inside the worktree** (`dist/`, `target/`, `.next/`, `node_modules/`) — already isolated. The
cost is disk and a slower first build, not correctness. Do not try to share these across worktrees
to save time; that is how you get a stale-artifact bug that survives a clean checkout.

**Outside the worktree** — the package manager store, the Go build/module cache, `~/.cargo`,
`~/.gradle`, ccache. **Leave these shared.** They are content-addressed and concurrency-safe by
design, and isolating them multiplies setup time and disk for no benefit.

The exception: a cache keyed on something that is *not* content, such as an absolute path or a
fixed project name. Those can genuinely poison across worktrees, and need either a slug in the
key or to be moved into the worktree.

---

## 10. Things that look like clashes but are not

Do not spend effort here:

- **Container-internal ports.** Only the host side of the mapping is shared.
- **Git objects.** Worktrees share one object store by design; that is what makes them cheap.
- **Environment variables.** Per-process, so per-worktree already — as long as each worktree's
  shell sources its own descriptor rather than a machine-global profile.
- **Read-only fixtures and seed data files.** Shared reads are fine.
- **Source files.** This is the one thing worktrees genuinely do isolate.
