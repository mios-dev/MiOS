---
name: windows-control
description: |
  Launch + control Windows apps from the MiOS-Agent (WSL → Windows
  interop). Use whenever the operator says: launch / open / start /
  run any Windows app or game; open a URL; query a Windows service;
  manipulate a Windows window (focus, move, center, resize). The
  helpers translate paths, route through the operator broker, and
  auto-center launched windows — you don't need to memorise the
  WSL ↔ Windows path mechanics.
metadata:
  hermes:
    requires_tools: [terminal]
---

# windows-control — reach Windows from WSL

<!-- MiOS-managed: seeded from /usr/share/mios/hermes/skills/
     windows-control/SKILL.md. Delete this marker to take ownership. -->

The MiOS-DEV WSL distro runs inside Windows. `mios-windows` is the
single shim for Windows-host control; it handles WSL interop, the
operator-session broker, path translation (WSL `/mnt/c/...` ↔ Windows
`C:\...`), and auto-centering launched windows.

## The two-step launch — canonical

```
mios-find <name-or-keyword>
# → prints ONE line: a ready-to-execute launch command
<that line>
# → window opens on operator's desktop, centered + foregrounded
```

`mios-find` queries Voidtools Everything's NTFS index (via
`mios.toml [paths].everything_cli`), Steam/Epic/GOG library scans,
Windows Get-StartApps, and the Linux flatpak inventory. ~60 ms.

## Direct `mios-windows launch` invocations

```
mios-windows launch notepad                     # known short name
mios-windows launch "C:\Program Files\App\App.exe"  # full path (quoted)
echo 'C:\Program Files (x86)\Steam\steam.exe' \
    | mios-windows launch -                     # stdin -- SAFE for any
                                                  path with spaces/parens
                                                  /amps
mios-windows launch chrome https://example.com   # known shortname + args
```

`mios-windows launch` accepts (a) a known short name, (b) a Windows-
style full path, or (c) a path via stdin (`-`). It always:
* translates the path via `wslpath -u` if Windows-style
* routes through the operator-session broker if you're in a service
  user context (so the window appears on the operator's desktop)
* auto-centers + foregrounds the new window post-launch

## `mios-windows ps` and `mios-windows cmd`

```
mios-windows ps 'Get-Service vmcompute | fl'
mios-windows ps 'Get-StartApps | ConvertTo-Json'
mios-windows ps '& '"'"'M:\Programs\Everything\es.exe'"'"' -n 5 motorfest'
mios-windows cmd 'tasklist /FI "IMAGENAME eq notepad.exe"'
```

Both broker-route. PowerShell + cmd full paths come from `mios.toml
[paths].powershell_exe` and `[paths].cmd_exe`.

## URL launching

```
mios-open-url https://github.com/mios-dev/MiOS
```

Routes through the broker, opens in the operator's default browser
(ChromeDev on this host per `mios.toml`).

## Window control

```
mios-pc-control window-list
mios-pc-control window-focus  <hwnd-or-pid>
mios-pc-control window-move   <hwnd> <x> <y>
mios-pc-control window-resize <hwnd> <w> <h>
mios-pc-control window-center <hwnd-or-pid>
mios-pc-control screenshot    /tmp/screen.png
mios-pc-control click         <x> <y>
mios-pc-control type          'hello world'
mios-pc-control key-combo     ctrl+shift+t
```

For coordinate-driven clicks when you don't know the position:

```
mios-pc-control screenshot /tmp/s.png
mios-pc-vision /tmp/s.png "the Start button"
# → {"x":18,"y":1058,"confidence":0.92,...}
mios-pc-control click 18 1058
```

## What NOT to do

* `Get-ChildItem -Recurse` on a Windows drive — never. 60s timeout.
  Voidtools (via `mios-find` or `mios-windows ps "& '...es.exe' ..."`)
  already indexed it.
* Direct invocation of `/mnt/c/...exe` from this agent's WSL context
  — perm-denied by WSL DrvFs metadata. Helpers route through the
  broker for you.
* Tell the operator to "open Start menu manually" — you have the
  tools. Use them.
