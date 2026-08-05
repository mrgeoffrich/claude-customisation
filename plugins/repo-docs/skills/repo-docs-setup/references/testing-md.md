# Writing TESTING.md

## What this file is for

Two audiences with different questions:

- Someone **adding** code: what kind of test should I write for this, where does it go, and what does a good one look like here?
- Someone who **just changed** code: what do I run to convince myself I haven't broken anything?

The second is the one most repos never write down, and it's the one an agent needs most. Give it its own section and make it copy-pasteable.

## Structure

```markdown
# Testing

## Test layers

<For each layer this repo actually uses: what it's for *here*, what it's allowed to
touch, and roughly how much of the suite it should be. Skip the generic test-pyramid
lecture — the reader can get that anywhere. What they can't get anywhere is where
the line falls in *this* codebase.>

| Layer | Purpose here | Touches | Runner | Lives in |
|-------|--------------|---------|--------|----------|
| Unit | Pure logic, no I/O | Nothing external | `<...>` | `<...>` |
| Integration | Real DB / real HTTP boundary | Dockerised Postgres | `<...>` | `<...>` |
| End-to-end | Critical user journeys only | Full stack | `<...>` | `<...>` |

## What to test where

<Per component or package. This is the section that stops people writing an E2E test
for something a unit test would have caught in 40ms.>

### `<path/to/component>`
- **Write:** <which layers apply, and what specifically warrants a test>
- **Don't bother:** <what's deliberately not tested, and why — this is real
  guidance, not an admission; it stops people writing low-value tests>
- **Run:** `<command scoped to just this component>`

## Running tests

| What | Command |
|------|---------|
| Everything | `<...>` |
| One package | `<...>` |
| One file | `<...>` |
| One test by name | `<...>` |
| Watch mode | `<...>` |
| With coverage | `<...>` |

<Prerequisites: services that must be up, env vars or `.env` files needed, seed or
migration steps, one-off setup. Be exact — "make sure the DB is running" helps nobody;
`docker compose up -d postgres && pnpm db:migrate` does.>

## Conventions

- **Naming:** <file and test-name patterns>
- **Fixtures and factories:** <where they live, which to prefer>
- **Mocking:** <what gets mocked and what must stay real — the single most common
  thing newcomers get wrong>
- **Assertions:** <house style, custom matchers, snapshot policy>

## Smoke test after a change

<The short sequence to run before considering a change done. Ordered
cheapest-first so failures surface fast, with the expected outcome stated.>

1. `<typecheck>` — no errors
2. `<lint>` — clean
3. `<unit tests>` — all pass, takes about <N>s
4. `<targeted integration tests for the area you touched>`

<Then the manual checks, if any: the specific journeys worth clicking through, and
what "working" looks like for each.>

<For a broad or risky change, say what escalates to the full suite: `<cmd>`,
about <N> minutes.>

## Known-awkward tests

<Flaky tests and the reason. Slow tests and how to skip them locally. Tests that
need credentials or network access and therefore only run in CI. Naming these is
what stops someone burning an afternoon on a failure that was already known.>

## Coverage

<Only if there's a real threshold. State the number, where it's enforced (CI job,
config file), and what's excluded. If there's no enforced threshold, say
"no enforced threshold" — that's useful information, and better than an
aspirational number nobody checks.>
```

## Getting the content right

**Read the CI workflow first.** It's the most reliable source in the repo, because those commands demonstrably run. Test job names, matrix dimensions, service containers and the ordering of steps tell you the real layering, often more accurately than the test directories do.

**Derive layers from what exists, not from the pyramid.** If the repo has unit and E2E and nothing between, document those two. Inventing an integration layer that doesn't exist produces a document describing a repo that isn't this one. The published ratios (roughly 60–70% unit, 20–25% mid-layer, a handful of E2E smoke journeys) are a useful sanity check on whether the shape is sensible, and worth a sentence if the repo is visibly lopsided — but they're a comparison, not a target to assert.

**The smoke test must be specific and ordered.** "Run the tests" is not a smoke test. The sequence should be cheapest-first so a typecheck failure doesn't cost someone a full E2E run, and each step should state what passing looks like. If the repo has a single command that does all of it (`make check`, `just ci`), lead with that and list what it covers.

**Name what isn't tested.** Deliberate gaps documented as deliberate are worth as much as the tests themselves — otherwise every new contributor rediscovers the gap and either writes a low-value test or files a bug about it.

## What does not belong here

- A tutorial for the test framework — link to upstream docs and spend the space on what's specific to this repo
- A catalogue of existing test cases — that's the test files
- Full CI configuration — link to `.github/workflows/test.yml`, don't transcribe it
- Debugging notes for one historical flake — the issue tracker
