# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Canonical agent prompt: `/usr/share/mios/ai/system.md` (deployed from `mios-bootstrap`).

## Loading order

1. Load `/usr/share/mios/ai/system.md`.
2. Apply `/etc/mios/ai/system-prompt.md` if present (host override).
3. Apply `~/.config/mios/system-prompt.md` if present (user override).

## Claude Code deltas

* **cwd:** `/` is the repo root and system root — do not treat it as dangerous.
* **Confirm before:** `git push`, `bootc upgrade`, `dnf install`, `systemctl`, `rm -rf`.
* **Deliverables:** complete replacement files only — no diffs, no patches.
* **Memory:** `/var/lib/mios/ai/memory/`
* **Scratch:** `/var/lib/mios/ai/scratch/`
* **Tasks:** use the task tool for multi-step work; one in-progress at a time.

## Operator behavioural rules (binding on every Claude session)

These are runtime rules for the assistant working on MiOS. Encoded
here so EVERY Claude session reads them — no out-of-band memory.

### NO live launches — implement code, never run apps interactively

Claude is **infrastructure**, not a runtime convenience. When the
operator asks for something operational (open Chrome, launch a game,
post to a channel, navigate a URL), the answer is to **fix or
extend the code path** so the MiOS-Agent stack does it locally —
NOT to invoke the launch via Bash/PowerShell/`mios-launch` from
this assistant's tools.

Exceptions:
* **Read-only state checks** (Get-Process, journalctl reads,
  `mios-doctor`, `mios-find` which resolves-without-running,
  `mios-apps`, CDP `/json/version` probes, file inspections) are
  fine — anything whose effect is purely observational.
* **One-time API probes** for verifying a service binding
  (curl to Discord `/users/@me`, CDP `/json/version`, OWUI
  `/api/v1/functions/`) are fine — they touch external APIs but
  don't put windows on the operator's screen.

Forbidden:
* Anything whose effect is the operator seeing a NEW window,
  sound, notification, or app on their machine. The operator
  has stated this in caps multiple times ("I DON'T WANT YOU TO
  EVER LAUNCH THE APPS FOR ME!!!"). For verifying launch-chain
  changes, inspect the broker socket / journal / script source
  WITHOUT triggering the launch. Tell the operator "shipped;
  try X in OWUI" and let them verify visibly themselves.

### NO context injection — env discovery via tool calls only

The agent (MiOS-Hermes) learns its environment by **calling tools**
(`mios-env-probe`, `mios-apps`, `skill_view name=mios-environment`,
the native `mios_verbs.*` surface) — NEVER via a `pre_llm_call`
hook that auto-prepends env text to the user message.

Why:
* Inject text bloats every first-turn prompt (~500 tokens) without
  the model actually consuming it (operator-confirmed: agent had
  the env in its inject and STILL hallucinated the hostname)
* Tool-call discovery teaches the model the actual surface
* "Code over prompt" is the architectural direction

When working on Hermes config / hooks / plugins: do not add
`pre_llm_call` shapes that return `{"context": "..."}`. If env
awareness needs reinforcing, do it in SOUL.md prose telling the
agent WHEN to invoke env-discovery tools — not by pre-injecting
their output.
