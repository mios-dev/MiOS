# AGENTS.md

> Generic agent contract following the AGENTS.md standard.
> Read by Codex, Cursor, Aider, Continue.dev, and other agents that don't
> have a dedicated rules file. Redirector stub.
>
> Canonical agent prompt: `/usr/share/mios/ai/system.md`.

## Behavior contract

1. Load `/usr/share/mios/ai/system.md` first.
2. Apply `/etc/mios/ai/system-prompt.md` as host-local override if present.
3. This file carries no tool-specific deltas; generic agents follow the
   canonical prompt verbatim.

If `/usr/share/mios/ai/system.md` is unreachable, fall back to
`/system-prompt.md` in the repo root.

## Sanitization reminder

Per `/usr/share/mios/ai/system.md` §6: no corporate entity references in
persisted artifacts, no chat metadata, OpenAI API-compliant minimal form.
This applies to all output you persist to this repository.
