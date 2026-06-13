---
name: windows-control
description: |
  Launch + control Windows apps from the MiOS-Agent. The host provides
  helpers that handle WSL ↔ Windows interop, broker dispatch to the
  operator session, path translation, and window auto-centering — you
  invoke them by name, not by remembering paths or syntax. Use when
  the operator asks to launch / open / start / run any Windows app or
  game, open a URL, query a Windows service, or manipulate a Windows
  window.
metadata:
  hermes:
    requires_tools: [terminal]
---
<!-- AI-hint: Defines the `windows-control` skill for the Hermes agent to launch, manage, and interact with Windows applications, services, and URLs via a set of abstracted host-side helpers that handle path translation and session brokering.
     AI-related: mios-find, mios-windows, mios-open-url, mios-pc-control, mios-apps, mios-doctor, hermes-agent.service -->

# windows-control — host-specific helpers

> _MiOS-managed: vendor surface map. Hermes's NATIVE skill_manage
> can append learned-by-experience specifics to a separate skill
> (e.g. `learned-windows-launches`) without editing this file.
> Delete this marker to take ownership._

The MiOS host provides a small set of helpers on `$PATH`. They
resolve all paths from environment vars (set by
`hermes-agent.service.d` drop-ins) or `mios.toml [paths]` — you
never hardcode a path.

## Helpers

| Helper | Purpose |
|---|---|
| `mios-find <query>` | App / file lookup. Returns ONE ready-to-execute line on stdout. The line is shell-safe. |
| `mios-windows launch <name-or-path>` | Launch a Windows app. Accepts short name, Windows path, or stdin (`echo PATH \| mios-windows launch -`). |
| `mios-windows ps <powershell>` | Run a PowerShell command on Windows. |
| `mios-windows cmd <cmd-line>` | Run a cmd.exe command on Windows. |
| `mios-open-url <url>` | Open URL in operator's browser. |
| `mios-pc-control <subcmd>` | Win32 input + window enumeration + screenshot. Subcommands listed in `mios-pc-control --help`. |
| `mios-apps` / `mios-apps --filter <q>` | Full launchable inventory. |
| `mios-doctor` | Health probe. |

## The canonical chain

When the operator asks to launch X:

1. `mios-find X` → prints a line.
2. Execute that line.

The helpers route service-user calls through the operator broker
automatically, translate paths automatically, and auto-center the
new window automatically. You don't reconstruct any of that.

## When mios-find returns a URI (uplay://, steam://, epic://, http://)

The output line will already be `mios-windows ps "Start-Process
'<uri>'"`. Just execute it. Windows dispatches URIs to the registered
handler (Ubisoft Connect, Steam, browser, etc).

## When the operator's app isn't in mios-find's output

1. `mios-apps --filter <q>` to confirm.
2. ASK the operator where it lives — don't guess paths.
3. If you learn the path, `memory_save` it + (optionally) `skill_manage`
   a session-specific entry so future turns recall.

## What NOT to do

* `Get-ChildItem -Recurse` across a Windows drive — 60s timeout; the
  Voidtools index already has it (via `mios-find`).
* Invoke `/mnt/c/...exe` directly from this service-user context —
  WSL DrvFs strips exec; helpers route through the broker for you.
* `xdg-open` for a Windows URI — Linux-side; no Windows handler.
* Claim a helper "doesn't exist" — `which <helper>` first. All
  documented helpers are on `$PATH`.
* Push manual recovery on the operator — you have the tools.

## Learning

When a launch attempt fails (wrong path, missing app, parens-in-
shell, etc):
1. Read the actual error verbatim.
2. `memory_save` what was tried + the failure mode.
3. On retry, `memory_search` first.

Don't regress to refusal — that's worse than the first attempt. The
native memory loop is how you improve across turns; SKILL.md is just
the static surface map.
