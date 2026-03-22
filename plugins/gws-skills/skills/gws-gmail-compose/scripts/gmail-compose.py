#!/usr/bin/env python3
"""
gmail-compose.py - Compose, edit, and send Gmail messages without manual base64 encoding.

Handles the fetch → local file → encode → send pipeline so Claude (or a human)
never has to touch raw base64.

Supports both plain-text (.eml) and markdown (.md) draft files. Markdown emails
are sent as multipart/alternative (text/plain + text/html) with a custom header
so they round-trip back to markdown on fetch.

USAGE
-----
# Write a draft file then send it (.eml or .md)
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py send --file /tmp/draft.eml
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py send --file /tmp/draft.md

# Pull an existing message down to a temp file for inspection/editing
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py fetch <message_id> [--output /tmp/out.eml]

# Save a file as a new Gmail draft (prints draft ID)
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py draft --file /tmp/draft.eml

# Update an existing Gmail draft in-place
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py draft --file /tmp/draft.eml --draft-id <draft_id>

# Reply: fetch original, pre-populate headers/quoted body, send from file
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py reply <message_id> --file /tmp/draft.eml

# Reply-all
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py reply-all <message_id> --file /tmp/draft.eml

# Forward
python .claude/skills/gws-gmail-compose/scripts/gmail-compose.py forward <message_id> --to <addr> --file /tmp/draft.eml

PLAIN-TEXT DRAFT FILE FORMAT (.eml)
-------------------------------------
Headers first (Key: value), blank line, then body:

    To: someone@example.com
    Subject: Hello there
    Cc: other@example.com

    Body text here.
    More body text.

Only To and Subject are required. All other headers are optional.

MARKDOWN DRAFT FILE FORMAT (.md)
----------------------------------
YAML frontmatter for headers, then a markdown body:

    ---
    to: someone@example.com
    subject: Hello there
    cc: other@example.com
    ---

    # Hello

    This is a **markdown** email with a [link](https://example.com).

    - Item one
    - Item two

Markdown emails are sent as multipart/alternative (plain=original markdown source,
html=styled rendered HTML) with an X-Claude-Markdown: 1 header. On fetch, that
header is detected and the file is written back as .md — no lossy HTML conversion.

Style customisation: copy email-styles.yaml to email-styles.local.yaml and edit.
Requires: pip install markdown
"""

import sys
import os
import json
import subprocess
import base64
import email
import email.utils
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


SKILL_DIR = Path(__file__).parent.parent

DEFAULT_STYLES = {
    "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif",
    "font_size": "15px",
    "line_height": "1.6",
    "body_color": "#333333",
    "background_color": "#ffffff",
    "heading_color": "#111111",
    "link_color": "#0070f3",
    "code_bg": "#f4f4f4",
    "code_color": "#c7254e",
    "code_font": "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
    "blockquote_border": "#cccccc",
    "blockquote_color": "#666666",
    "max_width": "600px",
    "padding": "20px",
}


# ---------------------------------------------------------------------------
# Markdown / style helpers
# ---------------------------------------------------------------------------

def load_styles():
    """Load styles from email-styles.yaml (and optional .local.yaml override)."""
    styles = dict(DEFAULT_STYLES)
    for fname in ("email-styles.yaml", "email-styles.local.yaml"):
        p = SKILL_DIR / fname
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and ": " in line:
                    key, _, val = line.partition(": ")
                    styles[key.strip()] = val.strip().strip('"').strip("'")
    return styles


def build_css(s):
    return (
        f"body{{margin:0;padding:0;background:{s['background_color']}}}"
        f".eb{{font-family:{s['font_family']};font-size:{s['font_size']};"
        f"line-height:{s['line_height']};color:{s['body_color']};"
        f"max-width:{s['max_width']};margin:0 auto;padding:{s['padding']}}}"
        f"h1,h2,h3,h4,h5,h6{{color:{s['heading_color']};margin-top:1.2em;margin-bottom:0.4em}}"
        f"a{{color:{s['link_color']}}}"
        f"code{{background:{s['code_bg']};color:{s['code_color']};"
        f"font-family:{s['code_font']};padding:0.1em 0.3em;border-radius:3px;font-size:0.9em}}"
        f"pre{{background:{s['code_bg']};padding:1em;border-radius:4px;overflow-x:auto}}"
        f"pre code{{background:none;padding:0;color:inherit}}"
        f"blockquote{{border-left:3px solid {s['blockquote_border']};"
        f"color:{s['blockquote_color']};margin:0;padding-left:1em}}"
        f"table{{border-collapse:collapse;width:100%}}"
        f"th,td{{border:1px solid {s['blockquote_border']};padding:0.5em 0.75em;text-align:left}}"
        f"th{{background:{s['code_bg']}}}"
        f"hr{{border:none;border-top:1px solid {s['blockquote_border']};margin:1.5em 0}}"
        f"img{{max-width:100%}}"
        f"p{{margin:0.6em 0}}"
    )


def render_markdown_html(md_body):
    """Convert markdown body to a full styled HTML document."""
    try:
        import markdown as md_lib
    except ImportError:
        print(
            "Error: 'markdown' package required for .md files.\n"
            "Install with: pip install markdown",
            file=sys.stderr,
        )
        sys.exit(1)

    styles = load_styles()
    html_content = md_lib.markdown(
        md_body,
        extensions=["extra"],  # fenced_code, tables, footnotes, attr_list, etc.
    )
    css = build_css(styles)
    return (
        f'<!DOCTYPE html><html><head><meta charset="utf-8">'
        f"<style>{css}</style></head>"
        f'<body><div class="eb">{html_content}</div></body></html>'
    )


# ---------------------------------------------------------------------------
# GWS helpers
# ---------------------------------------------------------------------------

def run_gws(*args):
    result = subprocess.run(
        ["gws"] + list(args),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"gws error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def fetch_raw_message(message_id):
    """Return (gws_data_dict, parsed email.Message)."""
    data = run_gws(
        "gmail", "users", "messages", "get",
        "--params", json.dumps({"userId": "me", "id": message_id, "format": "raw"})
    )
    raw_bytes = base64.urlsafe_b64decode(data["raw"] + "==")
    return data, email.message_from_bytes(raw_bytes)


def get_text_body(msg):
    """Extract the first text/plain part from an email.Message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


# ---------------------------------------------------------------------------
# Draft file helpers
# ---------------------------------------------------------------------------

def parse_draft_file(path):
    """Parse a plain-text draft file into (headers dict, body str)."""
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    headers = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "":
            break
        if ": " in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(": ")
            headers[key.strip()] = value.strip()
        i += 1
    body = "\n".join(lines[i + 1:]).strip()
    return headers, body


def parse_markdown_file(path):
    """Parse a markdown draft file (YAML frontmatter + markdown body).

    Frontmatter keys are normalised to Title-Case ('to' → 'To', 'in-reply-to' → 'In-Reply-To').
    Frontmatter is optional — if absent the whole file is treated as the body.
    """
    text = Path(path).read_text(encoding="utf-8")
    headers = {}
    body = text.strip()

    if text.startswith("---\n") or text.startswith("---\r\n"):
        rest = text[4:]
        end_idx = rest.find("\n---")
        if end_idx != -1:
            for line in rest[:end_idx].splitlines():
                line = line.strip()
                if line and not line.startswith("#") and ": " in line:
                    key, _, val = line.partition(": ")
                    # Normalise: "in-reply-to" → "In-Reply-To"
                    normalised = "-".join(p.title() for p in key.strip().split("-"))
                    headers[normalised] = val.strip()
            body = rest[end_idx + 4:].strip()

    return headers, body


def load_draft(path):
    """Parse a draft file; return (headers, body, is_markdown)."""
    if path.endswith(".md"):
        headers, body = parse_markdown_file(path)
        return headers, body, True
    headers, body = parse_draft_file(path)
    return headers, body, False


def write_draft_file(path, headers, body):
    """Write headers + blank line + body to path."""
    lines = []
    for key, value in headers.items():
        if value:
            lines.append(f"{key}: {value}")
    lines.append("")
    lines.append(body)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown_file(path, headers, body):
    """Write a markdown file with YAML frontmatter (lowercase keys)."""
    key_map = [("From", "from"), ("To", "to"), ("Cc", "cc"), ("Subject", "subject"), ("Date", "date")]
    lines = ["---"]
    for std_key, yaml_key in key_map:
        val = headers.get(std_key, "")
        if val:
            lines.append(f"{yaml_key}: {val}")
    lines += ["---", "", body]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_raw_message(headers, body):
    """Return a base64url-encoded RFC 2822 plain-text message."""
    msg = EmailMessage()
    msg["To"] = headers.get("To", "")
    msg["Subject"] = headers.get("Subject", "")
    if headers.get("Cc"):
        msg["Cc"] = headers["Cc"]
    if headers.get("Bcc"):
        msg["Bcc"] = headers["Bcc"]
    if headers.get("In-Reply-To"):
        msg["In-Reply-To"] = headers["In-Reply-To"]
    if headers.get("References"):
        msg["References"] = headers["References"]
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def build_raw_markdown_message(headers, md_body):
    """Return a base64url-encoded multipart/alternative message.

    text/plain  = original markdown source (preserved for round-trip fetch)
    text/html   = styled rendered HTML
    X-Claude-Markdown: 1  marks the message for round-trip detection
    """
    html_body = render_markdown_html(md_body)

    msg = MIMEMultipart("alternative")
    msg["To"] = headers.get("To", "")
    msg["Subject"] = headers.get("Subject", "")
    if headers.get("Cc"):
        msg["Cc"] = headers["Cc"]
    if headers.get("Bcc"):
        msg["Bcc"] = headers["Bcc"]
    if headers.get("In-Reply-To"):
        msg["In-Reply-To"] = headers["In-Reply-To"]
    if headers.get("References"):
        msg["References"] = headers["References"]
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["X-Claude-Markdown"] = "1"

    msg.attach(MIMEText(md_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def build_message(headers, body, is_markdown):
    """Build the appropriate raw message depending on format."""
    if is_markdown:
        return build_raw_markdown_message(headers, body)
    return build_raw_message(headers, body)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_fetch(message_id, output_path=None):
    """Fetch a message and write it as a local draft file.

    Writes .md if the message has X-Claude-Markdown: 1, otherwise .eml.
    """
    data, orig = fetch_raw_message(message_id)
    is_markdown = orig.get("X-Claude-Markdown") == "1"

    headers = {
        "From":    orig.get("From", ""),
        "To":      orig.get("To", ""),
        "Cc":      orig.get("Cc", ""),
        "Subject": orig.get("Subject", ""),
        "Date":    orig.get("Date", ""),
    }
    body = get_text_body(orig)

    if is_markdown:
        if output_path is None:
            output_path = f"/tmp/gmail-{message_id[:12]}.md"
        write_markdown_file(output_path, headers, body)
    else:
        if output_path is None:
            output_path = f"/tmp/gmail-{message_id[:12]}.eml"
        write_draft_file(output_path, headers, body)

    print(output_path)
    return output_path


def cmd_draft(draft_path, draft_id=None):
    """Save a draft file to Gmail as a draft (create or update)."""
    headers, body, is_markdown = load_draft(draft_path)
    if not body.strip():
        print("Error: draft body is empty", file=sys.stderr)
        sys.exit(1)

    raw = build_message(headers, body, is_markdown)
    payload = json.dumps({"message": {"raw": raw}})

    if draft_id:
        result = subprocess.run(
            ["gws", "gmail", "users", "drafts", "update",
             "--params", json.dumps({"userId": "me", "id": draft_id}),
             "--json", payload],
            capture_output=True, text=True
        )
        action = "updated"
    else:
        result = subprocess.run(
            ["gws", "gmail", "users", "drafts", "create",
             "--params", json.dumps({"userId": "me"}),
             "--json", payload],
            capture_output=True, text=True
        )
        action = "created"

    if result.returncode != 0:
        print(f"Error saving draft:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    print(f"Draft {action}. Draft ID: {data.get('id')}  Message ID: {data.get('message', {}).get('id')}")


def cmd_send(draft_path, thread_id=None):
    """Send a draft file as a new message (or into a thread)."""
    headers, body, is_markdown = load_draft(draft_path)
    if not body.strip():
        print("Error: draft body is empty", file=sys.stderr)
        sys.exit(1)

    raw = build_message(headers, body, is_markdown)
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id

    result = subprocess.run(
        ["gws", "gmail", "users", "messages", "send",
         "--json", json.dumps(payload)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Error sending message:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    response = json.loads(result.stdout)
    print(f"Sent. Message ID: {response.get('id', '?')}  Thread ID: {response.get('threadId', '?')}")


def cmd_reply(message_id, draft_path, reply_all=False):
    """
    Fetch the original message and send draft_path as a reply (in the same thread).
    The draft file should already contain the reply body — this just handles
    the threading headers (In-Reply-To, References, threadId) automatically.
    """
    data, orig = fetch_raw_message(message_id)
    thread_id = data.get("threadId")

    orig_message_id = orig.get("Message-ID", "")
    orig_references = orig.get("References", "")

    headers, body, is_markdown = load_draft(draft_path)

    if not headers.get("To"):
        headers["To"] = orig.get("From", "")
    if not headers.get("Subject"):
        subj = orig.get("Subject", "")
        headers["Subject"] = subj if subj.startswith("Re:") else f"Re: {subj}"
    if reply_all and not headers.get("Cc"):
        me_data = run_gws("gmail", "users", "getProfile", "--params", '{"userId":"me"}')
        my_email = me_data.get("emailAddress", "").lower()
        raw_addrs = ", ".join(p for p in [orig.get("To", ""), orig.get("Cc", "")] if p)
        parsed = email.utils.getaddresses([raw_addrs])
        filtered = [email.utils.formataddr((name, addr))
                    for name, addr in parsed if addr.lower() != my_email]
        if filtered:
            headers["Cc"] = ", ".join(filtered)

    headers["In-Reply-To"] = orig_message_id
    headers["References"] = (
        f"{orig_references} {orig_message_id}".strip() if orig_references else orig_message_id
    )

    raw = build_message(headers, body, is_markdown)
    payload = {"raw": raw, "threadId": thread_id}

    result = subprocess.run(
        ["gws", "gmail", "users", "messages", "send",
         "--json", json.dumps(payload)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Error sending reply:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    response = json.loads(result.stdout)
    print(f"Reply sent. Message ID: {response.get('id', '?')}  Thread ID: {response.get('threadId', '?')}")


def cmd_forward(message_id, to, draft_path=None):
    """
    Fetch original message, prepare a forward draft (or send draft_path directly).
    If draft_path is given, that file's body is used (with the forwarded message appended).
    If draft_path is not given, prints the prepared draft path for the user to edit.
    """
    data, orig = fetch_raw_message(message_id)
    orig_body = get_text_body(orig)
    orig_from = orig.get("From", "")
    orig_date = orig.get("Date", "")
    orig_subject = orig.get("Subject", "")

    fwd_block = (
        "\n---------- Forwarded message ----------\n"
        f"From: {orig_from}\n"
        f"Date: {orig_date}\n"
        f"Subject: {orig_subject}\n\n"
        f"{orig_body}"
    )

    if draft_path:
        headers, body, is_markdown = load_draft(draft_path)
        if not headers.get("To"):
            headers["To"] = to
        if not headers.get("Subject"):
            headers["Subject"] = orig_subject if orig_subject.startswith("Fwd:") else f"Fwd: {orig_subject}"
        full_body = (body + "\n" + fwd_block).strip()

        raw = build_message(headers, full_body, is_markdown)
        payload = {"raw": raw}

        result = subprocess.run(
            ["gws", "gmail", "users", "messages", "send",
             "--json", json.dumps(payload)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print("Error forwarding message:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)

        response = json.loads(result.stdout)
        print(f"Forwarded. Message ID: {response.get('id', '?')}")
    else:
        # Write a ready-to-edit draft and return its path
        headers = {
            "To":      to,
            "Subject": orig_subject if orig_subject.startswith("Fwd:") else f"Fwd: {orig_subject}",
            "Cc":      "",
        }
        full_body = fwd_block.strip()
        out = f"/tmp/gmail-fwd-{message_id[:12]}.eml"
        write_draft_file(out, headers, full_body)
        print(out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def usage():
    print(__doc__, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        usage()

    cmd = args[0]

    def flag(name, default=None):
        key = f"--{name}"
        if key in args:
            idx = args.index(key)
            if idx + 1 < len(args):
                return args[idx + 1]
        return default

    if cmd == "fetch":
        if len(args) < 2:
            usage()
        cmd_fetch(args[1], output_path=flag("output"))

    elif cmd == "draft":
        path = flag("file")
        if not path:
            print("Error: --file <path> required", file=sys.stderr)
            sys.exit(1)
        cmd_draft(path, draft_id=flag("draft-id"))

    elif cmd == "send":
        path = flag("file")
        if not path:
            print("Error: --file <path> required", file=sys.stderr)
            sys.exit(1)
        cmd_send(path, thread_id=flag("thread-id"))

    elif cmd == "reply":
        if len(args) < 2:
            usage()
        path = flag("file")
        if not path:
            print("Error: --file <path> required", file=sys.stderr)
            sys.exit(1)
        cmd_reply(args[1], path, reply_all=False)

    elif cmd == "reply-all":
        if len(args) < 2:
            usage()
        path = flag("file")
        if not path:
            print("Error: --file <path> required", file=sys.stderr)
            sys.exit(1)
        cmd_reply(args[1], path, reply_all=True)

    elif cmd == "forward":
        if len(args) < 2:
            usage()
        to = flag("to")
        if not to:
            print("Error: --to <address> required for forward", file=sys.stderr)
            sys.exit(1)
        path = flag("file")
        cmd_forward(args[1], to, draft_path=path)

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        usage()
