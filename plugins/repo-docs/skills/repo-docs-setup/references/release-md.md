# Writing RELEASE.md

## What this file is for

Someone needs to ship, possibly under pressure, possibly having never done it before, possibly because the person who normally does it is asleep. Precision beats prose everywhere in this document. Exact commands, exact tag formats, exact order.

This is also the file where invention does the most damage. A `RELEASE.md` describing a release process the repo doesn't actually have will be followed, and it will publish something wrong. Only document what you found evidence for; mark everything else as unconfirmed.

## Establish what kind of repo this is first

The document's shape depends entirely on the answer:

| Evidence | Implies |
|---|---|
| `release-please-config.json`, `.release-please-manifest.json` | Automated: merge a release PR, everything else happens |
| `.releaserc*`, `semantic-release` in devDependencies | Automated: push to the release branch, CI does the rest |
| `.changeset/` directory | Changesets: contributors add changesets, a version PR accumulates them |
| Conventional Commits in `git log` | Version bumps are probably derived from commits — check for automation before assuming manual |
| Tags but no automation config | Manual tagging; reconstruct the sequence from CI triggers and past tags |
| CI job triggered `on: push: tags:` or `on: release:` | The tag or GitHub release is the trigger — say so explicitly, it's the thing people get wrong |
| No tags, no registry, no release CI | The repo may not warrant a `RELEASE.md` at all — say so |

`git tag --sort=-creatordate | head -20` shows the real tag format, which beats guessing between `v1.2.3` and `1.2.3` or `pkg-name@1.2.3`.

## Structure

```markdown
# Releasing

## Versioning

<Scheme (semver / calver / something else) and what drives a bump. If it's derived
from Conventional Commits, spell out the mapping: `fix:` → patch, `feat:` → minor,
`feat!:` or `BREAKING CHANGE:` → major. In a monorepo, say whether packages version
independently or in lockstep.>

## What gets published

| Artifact | Destination | Produced by |
|----------|-------------|-------------|
| `<pkg>` | npm | `<...>` |
| `<image>` | ghcr.io | `<...>` |
| Binaries | GitHub release assets | `<...>` |

## Before releasing

- [ ] `main` is green in CI
- [ ] <smoke test from TESTING.md passes>
- [ ] CHANGELOG entries read sensibly to a user
- [ ] <migrations applied / config flags set / anything environment-side>
- [ ] <breaking changes are documented and announced>

## Cutting a release

<The exact sequence. For an automated setup, this may be two steps — say that
plainly rather than padding it out.>

### Automated
1. Merge the release PR that `<tool>` keeps open against `main`.
2. `<tool>` tags, generates the changelog, creates the GitHub release, and publishes.
3. Verify: <how to confirm it actually landed — registry URL, `gh release view`>

### Manual
```bash
git checkout main && git pull
<version bump command>
git commit -am "chore(release): v<X.Y.Z>"
git tag -a v<X.Y.Z> -m "v<X.Y.Z>"
git push origin main --follow-tags
gh release create v<X.Y.Z> --generate-notes
<publish command, if not handled by CI>
```

<If pushing the tag is what triggers CI to publish, state it here — it's the step
whose consequences people misjudge.>

## Changelog

<Generated or hand-written? Which format? Where does it live? If contributors need
to do something per-PR (add a changeset, use a commit prefix, apply a label),
that's the important part of this section — it's a contributor obligation, not
just a release-time detail.>

## Permissions and secrets

<Who can release: branch protection rules, required approvals, org teams. Which
secrets the pipeline needs, **by name only** — `NPM_TOKEN`, `GITHUB_TOKEN`
permissions, signing keys — and where they're configured. Never a value.>

## Hotfix

<The path for shipping a fix without dragging in everything else on `main`:
branch from the tag, cherry-pick, tag a patch. Write it before you need it.>

## If a release goes wrong

<Rollback and remediation, per artifact type: `npm deprecate` (npm publishes are
effectively permanent — unpublishing is heavily restricted), retag a container,
`gh release delete`, revert-and-re-release. State the constraints honestly; the
worst moment to discover you can't unpublish is while trying to.>

## Pre-releases

<Only if the repo does them: how alpha/beta/rc versions are tagged, which dist-tag
or channel they publish to, how one gets promoted to stable.>
```

## Getting it right

**CI is the specification.** For an automated setup, the workflow file *is* the release process — read its triggers, its permissions block, its publish steps. Document what it does, not what a release usually looks like.

**Reconstruct manual processes from history.** `git log --oneline` around past tags shows the real pattern: whether a version-bump commit precedes the tag, what the commit message convention is, whether a CHANGELOG edit is part of it.

**State the trigger unambiguously.** The single most consequential fact in this document is what action causes a publish — merging a PR, pushing a tag, creating a GitHub release, or running a command locally. Someone who gets that wrong either ships nothing or ships accidentally.

**Monorepo:** say whether versioning is independent or fixed, how tags are namespaced (`@scope/pkg@1.2.3` vs `v1.2.3`), and how a change to a shared package propagates to its dependants. Tools like changesets and release-please handle this differently and the difference matters to contributors.

## What does not belong here

- **Secret values** — names and locations only, always
- **The deployment runbook**, if deploying is separate from releasing — that's `docs/runbooks/` or a skill; conflating "a version exists" with "it's running in production" causes real incidents
- **Full CI YAML** — link to the workflow file
- **The changelog itself** — that's `CHANGELOG.md`; this file describes the policy
