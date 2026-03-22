# Achievement Guide — Feature Reference

This reference is loaded when the user asks for more detail about a specific
feature mentioned in an achievement.

## Beginner Features

### Reading Files (Curious Eyes)
Claude uses the **Read** tool to view file contents. It sees line numbers and
can read specific ranges of large files. It can also read images, PDFs, and
Jupyter notebooks.

### Editing Files (First Edit)
The **Edit** tool performs exact string replacements. Claude reads the file
first, then specifies the old text and new text. Every edit creates a
checkpoint you can rewind with `Escape`.

### Creating Files (From Nothing)
The **Write** tool creates new files or fully rewrites existing ones. Claude
prefers Edit for modifications and Write for brand-new files.

### Running Commands (Terminal Tamer)
The **Bash** tool executes shell commands. Claude can run tests, build
projects, install dependencies, use git, and more. Commands respect your
permission settings.

### Searching Code (Code Detective)
**Grep** searches file contents with regex. **Glob** finds files by name
patterns (e.g., `**/*.ts`). Together they let Claude navigate any codebase.

### CLAUDE.md (Ground Rules)
A markdown file at your project root that Claude reads every session. Put your
conventions, build commands, and architecture notes here. Run `/init` to
create one. Keep it under 200 lines.

### Multi-Tool (Multi-Tool)
In a single conversation, Claude naturally uses multiple tools — reading files
to understand context, editing to make changes, running tests to verify. This
achievement recognizes that flow.

## Intermediate Features

### Web Research (Web Wanderer)
Claude can search the web with **WebSearch** and fetch specific URLs with
**WebFetch**. Useful for looking up docs, API references, or recent changes.

### Subagents (Delegation Master)
Claude can spawn isolated subagents for complex tasks. **Explore** agents
research codebases. **Plan** agents design implementations. Subagents keep the
main conversation clean by returning only summaries.

### Multi-File Editing (Refactorer)
Claude can edit many files in sequence — renaming variables, updating imports,
refactoring patterns across a codebase. Ask for cross-cutting changes.

### Path-Specific Rules (Rule Writer)
Create `.claude/rules/testing.md` with YAML frontmatter specifying `paths:`
patterns. These rules only load when Claude works on matching files, keeping
context focused.

### Git Workflows (Git Apprentice)
Claude can stage, commit, create branches, and push. Ask it to "commit these
changes" and it will examine the diff, write a descriptive message, and
create the commit.

### Test Running (Quality Guard)
Ask Claude to run your test suite. It will execute the tests, interpret
failures, and offer fixes. Works with any test framework.

### Context Management (Context Ninja)
Long sessions consume your context window. Use `/compact` to compress the
conversation, `/context` to check usage, and `/clear` to start fresh.
Claude automatically compacts when nearing limits.

### Achievements Skill (Skill Seeker)
Meta-achievement! By running `/achievements` you're already using the skill
system — reusable workflows invoked via slash commands.
