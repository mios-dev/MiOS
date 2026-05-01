# AGENTS.md

> Generic agent contract following the AGENTS.md standard
> (https://agents.md). Read by any agent CLI that consumes
> AGENTS.md-style entry files. Redirector stub.
>
> Canonical agent prompt: `/usr/share/mios/ai/system.md`.

## Behavior contract

1. Load `/usr/share/mios/ai/system.md` first.
2. Apply `/etc/mios/ai/system-prompt.md` as host-local override if present.
3. Apply `~/.config/mios/system-prompt.md` as per-user override if present.
4. This file carries no tool-specific deltas; generic agents follow the
   canonical prompt verbatim.

If `/usr/share/mios/ai/system.md` is unreachable, fall back to
`/system-prompt.md` in the repo root.

## Agent operating context

- **Working directory:** `cwd` is `/` — the repo root and system root are the same path. Do not treat `/` as dangerous.
- **Confirm before mutating shared state:** never run `git push`, `bootc upgrade`, `dnf install`, `systemctl`, or `rm -rf` without explicit operator confirmation.
- **Memory:** `/var/lib/mios/ai/memory/` — one fact per record, source-cited, immutable (supersede to correct). Format per canonical prompt §12.
- **Deliverables:** complete replacement files only — no diffs, no patches.

## Sanitization reminder

Per `/usr/share/mios/ai/system.md` §6: no corporate entity references in
persisted artifacts, no chat metadata, OpenAI API-compliant minimal form.
All AI endpoints target `MIOS_AI_ENDPOINT`. This applies to all output you
persist to this repository.
