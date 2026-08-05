# gws-skills

Google Workspace skills built on the [`gws` CLI](https://github.com/googleworkspace/cli).

## What's here

The skills fall into two groups, maintained differently.

### Vendored — do not hand-edit

These are generated from the Google Workspace API discovery documents by the `gws` CLI itself:

```
gws-shared              gws-gmail              gws-calendar
gws-gmail-read          gws-gmail-send         gws-calendar-agenda
gws-gmail-reply         gws-gmail-reply-all    gws-calendar-insert
gws-gmail-forward       gws-gmail-triage
gws-gmail-watch
```

They are API reference — resources, methods, and parameter discovery. **Any edit to them is lost on the next regeneration.** Fix things upstream at `googleworkspace/cli` instead.

`gws-shared` is a prerequisite: the others open by telling the agent to read it for auth, global flags, and security rules. Keep it even if you prune the rest.

### Hand-maintained

- **`gws-gmail-compose`** — wraps `scripts/gmail-compose.py`, which builds RFC 2822 messages and base64url-encodes them, and renders markdown drafts to styled HTML. Its `requirements.txt` is installed into a venv by the `SessionStart` hook in `plugin.json`.

  It deliberately overlaps `gws-gmail-send` / `-reply` / `-reply-all` / `-forward`. Those hit the raw API and need you to hand-build and encode the message; the composer does not. Its description claims precedence for exactly that reason. If the agent keeps reaching for the raw ones, prune them rather than weakening the composer.

## Refreshing the vendored skills

`gws generate-skills` writes **all 90-odd** skills for every service into `skills/` **relative to the current working directory**, and an index to `docs/skills.md`. It takes no `--help` and does not prompt — run it somewhere disposable, never in a project repo.

```bash
cd "$(mktemp -d)"
gws generate-skills
# then copy across only the ones this plugin carries
```

The generated skills track the version of `gws` that produced them, so upgrade the CLI first if you want current output:

```bash
npm install -g @googleworkspace/cli@latest
```

## Requirements

- `gws` on `$PATH`, authenticated (`gws auth status`)
- Scopes must cover the services in use. `gws auth login` **replaces** the scope set rather than adding to it, so list every service needed in one command:

  ```bash
  gws auth login -s gmail,calendar,drive,docs,sheets
  ```

  A `403 insufficient authentication scopes` means the account was authorised without that service. Re-authorising is an interactive browser flow — the user has to run it.
