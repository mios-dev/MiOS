---
name: pc-window-control
description: |
  The canonical chain for controlling Windows-side window state on a
  MiOS host: list / focus / move / position / resize / minimize /
  maximize / restore / close. Load this skill whenever the operator
  references window arrangement -- "move X to the right", "make X
  fullscreen", "minimize all the chat windows", "put X at 100,100",
  "resize X to 1920x1080". One verb per intent; the dispatcher
  resolves title patterns to hwnds internally.
metadata:
  hermes:
    requires_tools:
      - list_windows
      - focus_window
      - move_window
      - position_window
      - resize_window
      - minimize_window
      - maximize_window
      - restore_window
      - close_window
---
<!-- AI-hint: Defines the pc-window-control skill for Hermes to map natural language window management (move, resize, focus, minimize) to specific Win32-backed tool calls via the mios-window CLI.
     AI-related: /usr/share/mios/hermes/skills/pc-window-control/SKILL.md._, mios-window -->

# PC window-control on MiOS

> _MiOS-managed: seeded from
> /usr/share/mios/hermes/skills/pc-window-control/SKILL.md._

Every window-state intent maps to ONE native dispatch verb. The
verb wraps `mios-window <subcmd>` which resolves a title-pattern
substring to an hwnd via Win32 enumeration; you only need to
supply enough of the title to disambiguate. Ambiguous matches
pick the first and log alternatives to stderr.

## Verb selection

| Intent | Verb | Notes |
| --- | --- | --- |
| "what windows are open" | `list_windows()` | Returns title / pid / hwnd / x,y,w,h for every visible top-level. |
| "focus X" / "bring X to front" / "switch to X" | `focus_window(title=X)` | Optional `position=as-is` to skip the default golden-ratio re-layout. |
| "move X to left/right/center/top-left/..." | `move_window(title=X, position=<pos>)` | SEMANTIC position names. Use this for snap-style positioning. |
| "move X to (a,b)" / "X to coords (a,b)" | `position_window(title=X, x=a, y=b)` | LITERAL pixel coords. Pair with `screen_layout()` first if the agent needs to compute the target. |
| "resize X to WxH" / "make X WxH" | `resize_window(title=X, width=W, height=H)` | Pixel WxH. Doesn't move. |
| "minimize X" / "hide X" | `minimize_window(title=X)` | Hides to taskbar. |
| "maximize X" / "fullscreen X" | `maximize_window(title=X)` | Maximize to containing monitor. |
| "restore X" / "un-minimize X" | `restore_window(title=X)` | Returns to last normal-state geometry. |
| "close X" / "quit X" | `close_window(title=X, mode="graceful")` | Sends WM_CLOSE (apps with unsaved state get to prompt). Use `mode="force"` for kill. |

## Multi-step chains the planner emits

For multi-window arrangements the Phase A.1 planner emits a DAG
of these verbs. Operator-side examples:

- "tile chrome on the left and discord on the right"
  ```
  position_window(title="chrome",  x=0,    y=0)
  resize_window(  title="chrome",  width=960,  height=1080)
  position_window(title="Discord", x=960,  y=0)
  resize_window(  title="Discord", width=960,  height=1080)
  ```
- "fullscreen vscode and minimize everything else"
  ```
  maximize_window(title="Visual Studio Code")
  minimize_window(title="Discord")
  minimize_window(title="Telegram")
  # ... (the planner enumerates via list_windows first)
  ```

## What NOT to do

- Do NOT call `pc_type` / `pc_key` to drive window-management
  keyboard shortcuts (Win+Up, Alt+Space, etc). Those send keys
  to the FOCUSED window which may not be the target -- always
  use the native verbs which target by hwnd.
- Do NOT shell out to `wmctrl` / `xdotool` / `nircmd` / PowerShell
  `Set-ForegroundWindow`. The MiOS dispatch path runs the
  Win32 helper through the launcher broker; calling these
  directly bypasses the broker + the Phase B.3 firewall + the
  C.3 passport-signed audit trail.
- Do NOT guess hwnds. Always pass a `title=` substring. The
  dispatch layer resolves to hwnd internally; the agent's job
  is to name the window in human terms.

## Hardening

All five WRITE-class window verbs (`minimize_window`,
`maximize_window`, `restore_window`, `resize_window`,
`position_window`) are in `[security].firewall_high_privilege_
verbs`. A tainted session -- one where any upstream tool_call
loaded untrusted content (web fetch, external open_url, system-
file text_view) -- gets these verbs REFUSED at dispatch with a
`firewall_block` event. Operator clears the chain by starting a
fresh session.
