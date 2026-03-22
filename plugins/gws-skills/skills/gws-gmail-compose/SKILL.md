---
name: gws-gmail-compose
version: 1.1.0
description: "This skill should be used whenever composing, sending, replying to, forwarding, or saving a Gmail message as a draft. Triggers include: 'send an email', 'reply to that message', 'forward this to X', 'draft a message for me', 'write an email to...'. Handles plain-text .eml files and markdown .md files with automatic base64 encoding — no manual encoding required."
metadata:
  openclaw:
    category: "productivity"
    requires:
      bins: ["gws", "python3"]
      pip: ["markdown"]
    cliHelp: "python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py --help"
---

# gws-gmail-compose

> **Requires:** the [`gws` Google Workspace CLI](https://github.com/googleworkspace/cli) installed and authenticated.

> **Use this instead of the raw `gws gmail` send command** whenever composing, replying, forwarding, or editing an email. The raw API requires manually base64url-encoding an RFC 2822 message — this script does all of that automatically.

The script is bundled at `.claude/skills/gws-gmail-compose/scripts/gmail-compose.py`. All commands below assume the **repo root as the working directory** (which is the Claude Code default).

```bash
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py <command> [flags]
```

---

## Workflow

### 1. Composing a new email

**Option A — Markdown (preferred for rich content):**

Write a `.md` file with YAML frontmatter for headers and a markdown body:

```
/tmp/my-draft.md
─────────────────
---
to: someone@example.com
subject: Hello there
cc: other@example.com
---

# Hi there

This is a **markdown** email with a [link](https://example.com).

- Item one
- Item two
```

**Markdown draft rules:**
- YAML frontmatter between `---` delimiters; all keys are lowercase
- `to:` and `subject:` are required; `cc:`, `bcc:` are optional
- Do **not** include `from:` — Gmail adds it automatically
- Everything after the closing `---` is the markdown body
- When installed as a plugin, `markdown` is auto-installed via the SessionStart hook — no manual setup needed. For local `.claude/skills/` use, run `pip install markdown`.

Send it:

```bash
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py send --file /tmp/my-draft.md
```

The script builds a `multipart/alternative` message with the original markdown as `text/plain` and styled HTML as `text/html`, plus an `X-Claude-Markdown: 1` header for round-trip detection.

---

**Option B — Plain text (`.eml`):**

Write the draft as a local temp file, then send it:

```
/tmp/my-draft.eml
─────────────────
To: someone@example.com
Subject: Hello there
Cc: other@example.com

Body text here.
More body text.
```

**Draft file rules:**
- Headers first (`Key: value`), one per line
- Blank line separates headers from body
- `To:` and `Subject:` are required; `Cc:`, `Bcc:` are optional
- Do **not** include `From:` — Gmail adds it automatically

Send it:

```bash
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py send --file /tmp/my-draft.eml
```

---

### 2. Replying to a message

Write only your reply text in the draft file — the script automatically fills in `To`, `Subject`, `In-Reply-To`, `References`, and `threadId` from the original message.

```
/tmp/reply.eml
──────────────

Thanks for the update, I'll review it today.
```

```bash
# Reply to sender only
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py reply <message_id> --file /tmp/reply.eml

# Reply-all (original To/Cc added to Cc automatically)
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py reply-all <message_id> --file /tmp/reply.eml
```

You can override any auto-populated header by including it in the draft file explicitly (e.g. add `To: override@example.com`).

---

### 3. Saving or updating a draft

Use `draft` to save a local file to Gmail as a draft without sending it:

```bash
# Create a new Gmail draft (prints draft ID and message ID)
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py draft --file /tmp/my-draft.eml

# Update an existing draft in-place (use draft ID from drafts list)
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py draft --file /tmp/my-draft.eml --draft-id r2112529864235412017
```

To find existing draft IDs:
```bash
gws gmail users drafts list --params '{"userId":"me","maxResults":10}'
```

The typical edit loop: `fetch` → edit the `.eml` → `draft --draft-id <id>` to push back.

---

### 4. Fetching a message to a local file

Use `fetch` to pull a message down for inspection or to use as a base for editing:

```bash
# Writes to /tmp/gmail-<id>.eml and prints the path
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py fetch <message_id>

# Save to a specific path
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py fetch <message_id> --output /tmp/original.eml
```

The output file contains decoded headers and plain-text body — human-readable, no base64.

---

### 5. Forwarding a message

**Prepare a forward draft (no existing file):**

```bash
# Creates /tmp/gmail-fwd-<id>.eml with forwarded block pre-populated, prints path
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py forward <message_id> --to recipient@example.com
```

Edit the file to add an intro, then send:

```bash
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py forward <message_id> --to recipient@example.com --file /tmp/gmail-fwd-<id>.eml
```

---

## Typical Claude workflow

Step 1 — use the Write tool to create the draft file at `/tmp/reply.eml`:
```
To: (leave blank — auto-filled from original)
Subject: (leave blank — auto-filled as Re: ...)

Hi Geoff,

Your reply text here.

Cheers
```

Step 2 — send it:
```bash
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py reply <message_id> --file /tmp/reply.eml
```

Use `fetch` first if you need to see the original message before composing:
```bash
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py fetch <message_id>
# then Read the output file to inspect it
```

---

## Styling markdown emails

Default styles are in `.claude/skills/gws-gmail-compose/email-styles.yaml`. To customise without touching the committed file, copy it to `email-styles.local.yaml` (gitignored) and edit that:

```bash
cp .claude/skills/gws-gmail-compose/email-styles.yaml \
   .claude/skills/gws-gmail-compose/email-styles.local.yaml
```

Available style keys (all standard CSS values):

| Key | Default | Controls |
|-----|---------|----------|
| `font_family` | system-ui stack | Body text font |
| `font_size` | `15px` | Base font size |
| `line_height` | `1.6` | Line spacing |
| `body_color` | `#333333` | Body text colour |
| `background_color` | `#ffffff` | Email background |
| `heading_color` | `#111111` | h1–h6 colour |
| `link_color` | `#0070f3` | Hyperlink colour |
| `code_bg` | `#f4f4f4` | Inline code / code block background |
| `code_color` | `#c7254e` | Inline code text colour |
| `code_font` | monospace stack | Code font |
| `blockquote_border` | `#cccccc` | Blockquote left-border colour |
| `blockquote_color` | `#666666` | Blockquote text colour |
| `max_width` | `600px` | Max email width |
| `padding` | `20px` | Outer padding |

---

## Finding message IDs

Use the `gws` CLI to find message IDs:

```bash
# List recent messages
gws gmail users messages list --params '{"userId":"me","maxResults":10}'

# Search inbox
gws gmail users messages list --params '{"userId":"me","q":"from:someone@example.com","maxResults":5}'
```
