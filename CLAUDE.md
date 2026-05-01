# CLAUDE.md

> Read by Claude Code (CLI, VSCodium/VSCode, JetBrains, Slack) on entry.
> This is a redirector stub. The canonical agent prompt for MiOS-DEV is
> `/usr/share/mios/ai/system.md` (or `/etc/mios/ai/system-prompt.md` for
> host-local overrides).

## Behavior contract

1. **Load `/usr/share/mios/ai/system.md` first**, before any other file in
   this repo. It is the authoritative system prompt.
2. **Apply `/etc/mios/ai/system-prompt.md` as an override** if present
   (host-local admin customization).
3. **This file (`/CLAUDE.md`) carries Claude Code-specific deltas only.**
   See §Tool-specific deltas below.

If `/usr/share/mios/ai/system.md` is unreachable (e.g., running outside a
MiOS host), fall back to the copy at `/system-prompt.md` in the repo root.

## Tool-specific deltas (Claude Code only)

- **TodoWrite usage:** Track multi-step audits, refactors, and migrations
  with TodoWrite. One in_progress at a time. Mark completed immediately
  on finish.
- **File-creation defaults:** New files default to `/var/lib/mios/ai/scratch/`
  unless the user specifies a path or the work is targeted at the system
  overlay (`/automation/`, `/usr/share/mios/`, etc.).
- **Tool permissions:** When unsure whether a tool call would mutate state,
  prefer the read-only equivalent and ask before escalating. Never run
  `git push`, `bootc upgrade`, `dnf install`, `systemctl`, `rm -rf` without
  explicit user confirmation.
- **Skills:** This repo does not need the docx/pptx/xlsx skills for routine
  work. Use them only when explicitly asked to produce a Word/Excel/PowerPoint
  artifact.
- **Memory:** Per-session learnings persist to `/var/lib/mios/ai/memory/`.
  Read `/usr/share/mios/ai/system.md` §12 before writing memory entries.

## Sanitization reminder

Per `/usr/share/mios/ai/system.md` §6, all artifacts persisted to repo paths
or `/usr/share/mios/ai/` must be sanitized: no corporate entity references,
no chat metadata, no tool-call envelopes, OpenAI API-compliant minimal form.
This applies to anything you write — including this file's future revisions.
