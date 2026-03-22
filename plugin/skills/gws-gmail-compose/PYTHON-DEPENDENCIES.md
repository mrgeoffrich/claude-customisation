# Managing Python Dependencies in Claude Code Skills

When a skill bundles a Python script that requires third-party packages, there are
several approaches — each with different trade-offs around isolation, setup cost,
and portability.

---

## Approaches

### 1. `uv run` with inline script metadata (PEP 723)

Add a dependency block at the top of the script using [PEP 723][pep723] inline
metadata, then invoke via [`uv run`][uv-scripts] instead of `python3`:

```python
# /// script
# requires-python = ">=3.9"
# dependencies = ["markdown"]
# ///
```

```bash
uv run .claude/skills/gws-gmail-compose/scripts/gmail-compose.py send --file /tmp/draft.md
```

`uv` creates an isolated, cached environment per script automatically. Nothing is
installed globally or into the project.

**Requires:** `uv` installed ([installation guide][uv-install]).
**Best for:** modern dev environments where `uv` is already present.

---

### 2. Plugin data directory + SessionStart hook

The [Anthropic plugin reference][anthropic-plugin-ref] recommends storing
installed dependencies in `${CLAUDE_PLUGIN_DATA}` — a persistent directory
that survives plugin updates (`~/.claude/plugins/data/{id}/`).

A `SessionStart` hook checks whether the installed `requirements.txt` matches
the bundled one, and reinstalls only when they differ:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "diff -q \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" \"${CLAUDE_PLUGIN_DATA}/requirements.txt\" >/dev/null 2>&1 || (python3 -m venv \"${CLAUDE_PLUGIN_DATA}/.venv\" && \"${CLAUDE_PLUGIN_DATA}/.venv/bin/pip\" install -r \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" -q && cp \"${CLAUDE_PLUGIN_ROOT}/requirements.txt\" \"${CLAUDE_PLUGIN_DATA}/requirements.txt\") || rm -f \"${CLAUDE_PLUGIN_DATA}/requirements.txt\""
      }]
    }]
  }
}
```

Invoke the script using the venv's Python:

```bash
"${CLAUDE_PLUGIN_DATA}/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/gmail-compose.py" ...
```

**Note:** `${CLAUDE_PLUGIN_DATA}` and `${CLAUDE_PLUGIN_ROOT}` are only set for
*installed* plugins. For local skills (under `.claude/skills/`), these variables
may not be available — substitute a local `.venv` path instead.
**Best for:** published/installed plugins with a `plugin.json` manifest.

---

### 3. Vendored dependencies

Copy the package source into a `vendor/` subdirectory alongside the script and
prepend it to `sys.path` at runtime:

```
scripts/
  gmail-compose.py
vendor/
  markdown/        ← copied from site-packages
```

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "vendor"))
import markdown
```

**Requires:** manually copying and updating the package source.
**Best for:** fully offline/air-gapped environments, or when you want zero
runtime dependencies at the cost of owning upgrades.

---

### 4. Stdlib-only implementation

Replace the third-party package with a minimal stdlib implementation. For
markdown-to-HTML, a small regex-based converter (~60 lines) covers the subset
of syntax typically used in email: headings, bold/italic, links, inline code,
fenced code blocks, unordered lists, and horizontal rules.

**Requires:** nothing extra.
**Best for:** maximum portability; acceptable when the full feature set of a
library isn't needed.

---

## Comparison

| Approach | Isolation | Setup | Works offline | Maintenance |
|----------|-----------|-------|---------------|-------------|
| `uv run` + PEP 723 | Excellent | `brew install uv` | After first run | None |
| Plugin data dir + hook | Excellent | Plugin install | After first run | None |
| Vendored | Complete | Manual copy | Always | Manual upgrades |
| Stdlib only | Complete | None | Always | None |

---

## References

[pep723]: https://peps.python.org/pep-0723/
[uv-scripts]: https://docs.astral.sh/uv/guides/scripts/
[uv-install]: https://docs.astral.sh/uv/getting-started/installation/
[anthropic-plugin-ref]: https://docs.anthropic.com/en/claude-code/plugins-reference
