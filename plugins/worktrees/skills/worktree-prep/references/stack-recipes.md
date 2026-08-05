# Stack recipes

Where the environment tool goes, how it is invoked, and the idioms per stack. The design is
identical everywhere — see `allocation-design.md`; only the syntax and placement change.

Read the section for the stack the scan reported. The [common patterns](#common-patterns)
section at the end applies regardless of language.

## Contents

- [Node / TypeScript](#node--typescript)
- [Go](#go)
- [Python](#python)
- [Rust](#rust)
- [Polyglot, or no clear host stack](#polyglot-or-no-clear-host-stack)
- [Docker Compose (any stack)](#docker-compose-any-stack)
- [Common patterns](#common-patterns)

---

## Node / TypeScript

**Place it** at `tools/worktree-env/` (or `scripts/worktree-env.ts` for a small one). In a pnpm
or npm workspace, keep it out of the workspace packages so it has no build step of its own.

**Invoke it** through package.json scripts, matching how the repo runs its other tooling:

```json
{
  "scripts": {
    "worktree": "tsx tools/worktree-env/index.ts",
    "worktree:list": "tsx tools/worktree-env/index.ts list"
  }
}
```

**Watch out:** in a fresh worktree `node_modules` does not exist, so `tsx` is not installed — and
the very first command someone runs is the one that needs it. Either make `install` the documented
first step and say so loudly in the generated docs, or write the tool as a dependency-free
`.mjs` run by bare `node`, which sidesteps the bootstrap problem entirely. The second option is
usually worth the small loss in ergonomics.

**Idioms:** `node:util`'s `parseArgs` for the CLI, `node:fs`'s `writeFileSync` + `renameSync` for
the atomic registry write, `node:net`'s `createServer().listen(port)` to probe a port.

Frontends need extra care: Vite and Next read ports from their own config files, and the browser
bundle cannot read a JSON file off disk. Feed the descriptor into the config at load time and
expose what the client needs as build-time env (`VITE_API_URL`, `NEXT_PUBLIC_API_URL`).

---

## Go

**Place it** at `cmd/worktree-env/main.go`, alongside the repo's other commands. Stdlib is enough —
`flag`, `encoding/json`, `os/exec`, `net`.

**Invoke it** via `go run ./cmd/worktree-env <cmd>`, wrapped in a Makefile target if the repo has
one. `go run` needs no build step and no bootstrap, which makes Go the easiest stack to do this in.

**Idioms:** `os.CreateTemp` + `os.Rename` for the atomic write, `net.Listen("tcp", addr)` then
`Close()` to probe a port, `flag.NewFlagSet` per subcommand.

If the repo already has a CLI binary, adding a `worktree` subcommand to it is usually better than
a separate command — one binary, one help text, and existing config resolution for free. Weigh
that against the bootstrap cost: the CLI has to build before it can set up the worktree it is
being built in.

---

## Python

**Place it** at `tools/worktree_env.py` or as a console-script entry point in `pyproject.toml`.

**Invoke it** the way the repo invokes everything else — `uv run worktree-env`, `poetry run
worktree-env`, `make worktree`, or plain `python3 tools/worktree_env.py`.

**Prefer stdlib only** (`argparse`, `json`, `pathlib`, `socket`, `subprocess`, `shutil`), so the
tool runs before the virtualenv exists. That is exactly when it is needed: setting up a fresh
worktree is what creates the venv.

**Idioms:** `tempfile.NamedTemporaryFile(dir=...)` + `os.replace` for the atomic write,
`socket.socket().bind(("127.0.0.1", port))` to probe, `os.open(path, O_CREAT|O_EXCL)` for the lock.

Per-worktree virtualenvs are the norm and are already isolated (`.venv` lives in the worktree).
Leave the package cache (`~/.cache/uv`, `~/.cache/pip`) shared.

---

## Rust

**Place it** as a workspace member at `xtask/` — the established Rust convention for repo tooling —
invoked via a `.cargo/config.toml` alias:

```toml
[alias]
worktree = "run --package xtask --bin worktree-env --"
```

Then `cargo worktree start`. Note the compile cost on first run in a fresh worktree; if that is
too slow, a small Python or shell script is a defensible exception to keeping everything in-stack.

**Idioms:** `clap` if already a dependency, `std::env::args` if not. `target/` is inside the
worktree and therefore isolated already; leave `~/.cargo` shared.

---

## Polyglot, or no clear host stack

When the repo has several languages, or is mostly shell and compose:

- Pick the language of the **primary service**, or of whatever the repo's existing scripts are
  written in. Consistency with the repo beats theoretical fit.
- If nothing dominates, **Python 3 stdlib** is the safest choice: present on macOS and Linux,
  installable everywhere, no build step, no dependency bootstrap.
- Avoid Bash. The registry needs JSON parsing, atomic writes, and port probing — all of which are
  awkward and error-prone in shell, and all of which the tool needs to get exactly right.

---

## Docker Compose (any stack)

Compose does most of the isolation work if you let it.

**Set `COMPOSE_PROJECT_NAME=<project>-<slug>`** and compose namespaces containers, volumes, and
networks automatically. This single change eliminates most of section 2 of the clash catalogue.

**Delete every `container_name:`.** An explicit `container_name` defeats project namespacing and
is the most common cause of "container name already in use" in a worktree setup.

**Parameterise host ports** and nothing else:

```yaml
services:
  web:
    ports:
      - "${WEB_PORT:-3000}:3000"     # host side from the descriptor; container side fixed
```

The `:-3000` default keeps the file working for anyone who runs `docker compose up` directly
without the tool.

**Feed values via a `.env` file at the compose file's directory** — compose reads it automatically
— generated by `start` from the descriptor and gitignored.

**Named volumes** get the project prefix automatically once `container_name` is gone; a top-level
`name:` on a volume overrides that, so remove those too.

**Teardown** is `docker compose -p <project> down -v --remove-orphans`, runnable from anywhere
using only the project name — which is precisely why `delete` can work with the worktree directory
already deleted.

---

## Common patterns

**Descriptor loading.** Write one small function in the app's own code that finds the descriptor
by walking up from `cwd` to the worktree root and falls back to the repo defaults when it is
absent. Everything else calls that. Without a single loader, descriptor reading gets copy-pasted
into six places and three of them drift.

**Precedence** — explicit flag, then environment variable, then descriptor, then repo default.
Predictable, and it keeps `PORT=4000 npm run dev` working for someone debugging.

**Fail loudly on a missing descriptor inside a worktree.** Silently falling back to defaults means
the second worktree quietly attacks the first one's database. Falling back is right in the *main*
checkout, where no descriptor is expected; inside a worktree it is a bug.

**Do not shell out for what the stdlib does.** Every `os/exec` call is a platform assumption.
Reserve subprocess calls for genuinely external tools (`docker`, `git`, `psql`).

**Cross-platform paths.** Use the language's path API rather than string concatenation, and never
hardcode `/tmp` or `~` — resolve them properly. Windows contributors will hit every one of these.
