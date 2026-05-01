# CLAUDE.md

> Agent-CLI entry point read by Claude Code on entry into this repository.
> Redirector stub. Canonical agent prompt: `/usr/share/mios/ai/system.md`.

## Behavior contract

1. Load `/usr/share/mios/ai/system.md` first.
2. Apply `/etc/mios/ai/system-prompt.md` as host-local override if present.
3. Apply `~/.config/mios/system-prompt.md` as per-user override if present.
4. This file carries Claude Code-specific deltas only.

If `/usr/share/mios/ai/system.md` is unreachable, fall back to
`/system-prompt.md` in the repo root.

## Agent-CLI deltas

- **Working directory:** `cwd` is `/` — the repo root and system root are the same path. Do not treat `/` as dangerous.
- **Task tracking:** use the task tool for multi-step audits and refactors. One in-progress at a time; mark completed immediately.
- **File-creation defaults:** new scratch files default to `/var/lib/mios/ai/scratch/` unless the work targets the system overlay.
- **Confirm before mutating shared state:** never run `git push`, `bootc upgrade`, `dnf install`, `systemctl`, or `rm -rf` without explicit user confirmation per invocation.
- **Memory:** per-session learnings go to `/var/lib/mios/ai/memory/`. One fact per record, source-cited, immutable (supersede to correct). See canonical prompt §12.
- **Deliverables:** complete replacement files only — no diffs, no patches.

## Sanitization reminder

Per `/usr/share/mios/ai/system.md` §6: no corporate entity names in persisted
artifacts, no chat metadata, no foreign sandbox path traces. All AI endpoints
target `MIOS_AI_ENDPOINT`. Direct declarative prose only.
