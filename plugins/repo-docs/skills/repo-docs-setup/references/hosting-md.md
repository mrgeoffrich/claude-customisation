# Writing HOSTING.md

## What this file is for

Where this software actually runs, and how code gets there. It answers the questions someone has when they're not changing the code but changing where it lives: what environments exist, what's underneath them, how a deploy is triggered, how to tell if it worked, and how to undo it.

## The line between this and RELEASE.md

`RELEASE.md` ends when a versioned artifact exists and is published. `HOSTING.md` covers the environments that artifact runs in and how it reaches them. "A version exists" and "it is serving traffic" are different facts, and treating them as one is how people announce a release that never deployed, or deploy something they never meant to ship.

| Question | File |
|---|---|
| What version are we on, and how does a version get cut? | `RELEASE.md` |
| What does merging to `main` publish? | `RELEASE.md` |
| Where does production run, on what? | `HOSTING.md` |
| What does merging to `main` deploy, and where? | `HOSTING.md` |
| How do I roll back the published package? | `RELEASE.md` |
| How do I roll back what's serving traffic? | `HOSTING.md` |

Plenty of repos need exactly one of the two. A library published to a registry has releases and no hosting. A web app on continuous deploy has hosting and no releases worth the name — merging is the whole ceremony, and forcing a `RELEASE.md` onto it invents a process. When one document genuinely covers both because the repo has a single pipeline from merge to production, write it in whichever file matches what the team calls it, and have the other link across rather than restating it.

## Don't invent this one

The general rule against invention applies hardest here. A wrong `HOSTING.md` gets followed against production by someone who is, very often, in a hurry. Inferring "there's a Dockerfile, so it's probably on ECS" produces a confident, plausible, wrong document.

Write only what the repo demonstrates, and mark the rest visibly:

```markdown
> **TODO:** confirm — `fly.toml` defines a `staging` app, but no CI job references
> it and there's no evidence of how staging gets deployed. Manual `fly deploy`?
```

Hosting is also the area most likely to live somewhere the repo can't see: a separate infra repo, a platform dashboard, someone's shell history. When the trail runs out, say so and ask.

## Establish what kind of deployment this is first

| Evidence | Implies |
|---|---|
| `vercel.json`, `netlify.toml`, `render.yaml`, `railway.json`, `app.yaml` | Platform-as-a-service; deploys are usually git-triggered, and the dashboard holds config the repo doesn't |
| `fly.toml`, `Procfile`, `captain-definition` | PaaS with a CLI deploy — find whether CI runs it or a human does |
| `wrangler.toml` / `wrangler.jsonc` | Cloudflare Workers/Pages; environments are usually `[env.*]` blocks |
| `terraform/`, `*.tf`, `main.bicep`, CDK app, `template.yaml`, `serverless.yml` | Infrastructure as code — the source of truth for what exists; note where state lives |
| `k8s/`, `helm/`, `kustomization.yaml`, Argo/Flux config | Kubernetes; find what applies the manifests before describing a deploy |
| `Dockerfile` + a registry push in CI | An image is produced — but that alone doesn't tell you what runs it. Keep looking |
| CI job with `environment:`, or a deploy job gated on a branch or tag | The real trigger. This is the most reliable evidence in the repo |
| `docker-compose.prod.yml`, Ansible playbooks | Deployed to machines someone owns; note how the machines are reached |
| Nothing at all | The repo may not warrant a `HOSTING.md`. Say so rather than describing a deployment that isn't here |

CI is again the strongest evidence: a deploy job that runs is a deploy process that works, and its trigger, environment name and required secrets tell you most of the document.

## Structure

```markdown
# Hosting

## Environments

| Environment | URL | Purpose | Deployed from |
|---|---|---|---|
| Production | `<...>` | <...> | `<branch/tag/trigger>` |
| Staging | `<...>` | <...> | `<...>` |
| Preview | per-PR | <...> | `<...>` |

<Say which environments share resources with each other. "Staging points at the
production database" is the kind of fact that causes an incident exactly once.>

## Where it runs

<Platform and region. The services in play and what each one is: the compute, the
database, the cache, the queue, the object store, the CDN. Name them; don't
enumerate settings a console holds better.>

<A short list beats a diagram here — but if the topology genuinely needs one, a
mermaid diagram of request flow through the hosted pieces belongs in
ARCHITECTURE.md, and this file links to it.>

## How infrastructure is provisioned

<Terraform/Pulumi/CDK/manual. Where the code lives — this is very often a
different repo, so link it. Where remote state lives. What is NOT in code and
therefore lives only in a dashboard: say so explicitly, because that's what
someone will fail to find.>

## Deploying

### Production
<The trigger, stated unambiguously: merging to `main`, pushing a tag, a manual
workflow_dispatch, a CLI command. Then any approval gate, roughly how long it
takes, and how to verify it landed — the health endpoint, the dashboard, the
command that shows the running version.>

### Staging
<Same, where it differs.>

<Migrations: whether they run automatically as part of the deploy or are a
separate step someone must take, and in which order relative to the code deploy.
This is the single most dangerous ambiguity in the document.>

## Configuration and secrets

<Which env vars the app needs, **by name only**, and where each is set — CI
secrets, the platform dashboard, a secret manager. Never a value, never a
connection string. Note which are required to boot versus optional, and where the
authoritative list is (`.env.example`, a schema module).>

## Rollback

<How to get back to the previous good state, per environment: the platform's
rollback command or dashboard action, redeploying a previous ref, scaling down.
Whether a database migration makes rollback unsafe — and if so, what to do
instead. Write this before it's needed; it's read under pressure.>

## Observability and access

<Where logs, metrics, traces and error reports live, with links. How to get a
shell or tail logs against a running environment, if that's possible. Who can
deploy and how access is granted.>

## Scheduled and background work

<Cron jobs, queue workers, one-off task runners — what runs outside a request,
where it runs, and how it's deployed if that differs.>
```

Drop any section this repo has nothing real for. A `HOSTING.md` that is just an environments table and a deploy trigger is a good document if that's the truth.

## Getting it right

**State the trigger unambiguously.** As in `RELEASE.md`, the highest-consequence sentence is what action causes a deploy. "Merging to `main` deploys to production automatically, with no approval step" is worth more than the rest of the file. If a human must run something, name the command and who has permission to run it.

**Name what shares state.** Environments that look independent but aren't — staging pointing at the production database, a shared Redis, a single third-party sandbox account with rate limits — are the highest-value lines you can write, because nothing in the code reveals them.

**Distinguish infrastructure from configuration.** What's in Terraform is reproducible and reviewable; what someone set in a dashboard three years ago is neither. Documenting which parts are click-configured is not an embarrassment, it's the most useful thing in the section — it tells the next person what won't come back if the account is lost.

**Say where the boundary of this repo is.** If infrastructure lives in another repo, or the platform is managed by a different team, say that and link out. A reader who doesn't know that will search this repo until they give up.

**Keep brittle values out** — see the main skill's rule. "Runs on 3 `t3.medium` instances", "about $400/month", "scaled to 12 pods" are measurements of a moment and nothing flags them when they drift. Name the instance class only if it's a deliberate, load-bearing constraint; otherwise point at the IaC that holds the real number.

## Security

This is the file most likely to leak something, because everything it describes has a credential attached, and because plenty of these repos are public.

- **Never a value.** Env var *names*, secret *names*, and where they're configured. Never the contents, never a connection string, never a token — including ones that look inert, like a project ID paired with an API base URL.
- **Cloud account identifiers, ARNs, project numbers, bastion hostnames and internal-only URLs are not documentation.** They're reconnaissance if the repo is public, and useless to anyone who lacks access anyway. Refer to "the production AWS account" and let the console show which.
- **Check whether the repo is public before writing internal hostnames at all.** If it is, and the content is genuinely needed, that's a case for a private runbook with a link from here.
- If you find a secret already committed in an existing doc, don't quietly relocate it — tell the user plainly that it's in git history and needs rotating, not just deleting.

## What does not belong here

- **Secret values, account IDs, internal hostnames** — see above
- **Full Terraform or Kubernetes manifests** — link to them; they're already the source of truth and transcription only creates a second, wrong copy
- **Versioning and publishing** — `RELEASE.md`
- **How the system is designed** — `ARCHITECTURE.md`. This file says where the pieces run, not why they exist or how they relate
- **Incident response and on-call procedure** — `docs/runbooks/`. Deploying is routine; responding to an outage at 3am is a different document with a different reader
- **A long multi-step operational procedure** — if it's numbered steps someone follows under pressure, it wants to be a skill or a runbook, linked from here
