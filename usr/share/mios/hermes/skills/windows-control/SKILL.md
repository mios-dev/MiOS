---
name: windows-control
description: |
  Use whenever the operator asks to (a) launch a Windows app -- notepad,
  explorer, calc, taskmgr, paint, snipping, regedit, ANY installed Windows
  game/program; (b) launch a BROWSER or open a URL ("open chrome", "open
  YouTube", "open Wikipedia in my browser") -- this routes through
  mios-open-url or mios-windows launch chrome <url>; (c) run a Windows-
  side command (PowerShell, cmd.exe, query a Windows service, inspect
  Windows networking). NEVER reply "the mios-windows tool doesn't exist
  in the toolset" or "there isn't a direct command to launch a Windows
  application" or "tools available don't include..." -- mios-windows IS
  on /usr/local/bin/, uses WSL interop via /init, works without SSH or
  extra setup. The /usr/local/bin/mios-windows binary is shipped with
  MiOS, present on every install, and verified active by mios-doctor.
metadata:
  hermes:
    requires_tools: [terminal]
---

# windows-control -- reach the Windows host from inside this WSL2 distro

The MiOS-DEV WSL distro runs *inside* Windows. The `mios-windows`
shim gives the agent first-class access to that Windows host without
the agent having to know about WSL interop, SSH, Tailscale, or PATH
manipulation.

## When to reach for this skill

* The operator says **"open notepad"**, **"open explorer"**, **"open
  calc / mspaint / paint / snipping tool / task manager"**, or names
  any Windows GUI app -- any built-in Windows app you'd find in the
  Start menu.
* The operator says **"open a browser to <URL>"**, **"open YouTube /
  Wikipedia / GitHub / anything.com"**, **"open Chrome / Firefox /
  Edge"** -- this is a URL/browser request. Use `mios-open-url <URL>`
  for "open <URL>" prompts, or `mios-windows launch chrome <URL>` to
  explicitly route via Chrome.
* The operator says **"launch <game> / <app>"** -- a game (The Crew
  Motorfest, Steam, Battle.net, etc.) or third-party Windows app
  (Discord, Spotify, Notepad++, ...) installed on the Windows host.
  Use `mios-windows launch "<exact-display-name-or-exe-name>"`.
  If the app isn't in `mios-windows list`'s known shortnames,
  `mios-windows launch "C:\\Users\\...\\path\\to\\App.exe"` works too;
  any full Windows path is accepted.
* The operator says **"run <PowerShell command>"** or **"check the
  Windows service <name>"** or **"query the Windows network
  config / IP / DHCP / firewall"**.
* The operator says **"launch <app> on Windows"** / **"on the host"**
  / **"on the Windows side"**.
* You're about to write "I cannot launch native Windows applications
  from WSL". Stop. Use `mios-windows launch <app>` instead.
* You're about to write **"the mios-windows tool doesn't exist in the
  current toolset"** or **"tools available to me don't include a direct
  way to launch Windows applications"** or **"isn't a direct command
  to launch a Windows application"**. STOP. Both are FALSE on this
  host. `mios-windows` is at `/usr/local/bin/mios-windows`, symlinked
  from `/usr/libexec/mios/mios-windows`, available on every MiOS install,
  reachable via the `terminal` tool with no extra setup. Verify with
  `terminal: which mios-windows` if you doubt it -- DO NOT guess.

## Browser + URL recipes (the operator's most common ask)

```
mios-open-url https://www.youtube.com         # OPEN any URL in op's browser
mios-open-url https://en.wikipedia.org        # ANY URL, no app-name resolution

mios-windows launch chrome https://github.com # launch Chrome with a starting URL
mios-windows launch chrome                    # launch Chrome to its home page
```

`mios-launch` is for APPLICATION NAMES (chrome, nautilus, etc.). It
does NOT resolve URLs as args -- if the operator says "open Wikipedia"
do NOT run `mios-launch wikipedia` (it will fail with "no resolution
for 'wikipedia'"). Use `mios-open-url https://en.wikipedia.org`
instead. This is the exact failure that bit the operator 2026-05-15.

## Game / third-party app recipes

```
mios-windows launch steam                     # if "steam" is in list
mios-windows launch "Battle.net Launcher"
mios-windows launch "C:\\Program Files\\Ubisoft\\Ubisoft Game Launcher\\upc.exe"

# Game install locations -- CHECK THESE FIRST before doing a deep
# Get-ChildItem -Recurse, which times out at 60s on a large C: drive:
#
#   Steam:        C:\Program Files (x86)\Steam\steamapps\common\<GameName>\
#   Steam D:      D:\SteamLibrary\steamapps\common\<GameName>\
#   Epic:         C:\Program Files\Epic Games\<GameName>\
#   Ubisoft:      C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\games\<GameName>\
#   GOG:          C:\Program Files (x86)\GOG Galaxy\Games\<GameName>\
#   EA / Origin:  C:\Program Files\EA Games\<GameName>\
#   Battle.net:   C:\Program Files (x86)\<GameName>\
#   Xbox/MS Store: C:\XboxGames\<GameName>\  (or under %ProgramFiles%\WindowsApps\)
#   Riot:         C:\Riot Games\<GameName>\
#   Standalone:   C:\Games\<GameName>\  or  D:\Games\<GameName>\

# Try the LIKELY launcher path FIRST -- one short Test-Path probe per
# launcher is cheap (~50ms each). Only fall back to recursive scan
# if all the obvious locations miss.
mios-windows ps 'Test-Path "C:\\Program Files (x86)\\Steam\\steamapps\\common\\BeamNG.drive\\BeamNG.drive.exe"'
mios-windows ps 'Test-Path "D:\\SteamLibrary\\steamapps\\common\\BeamNG.drive\\BeamNG.drive.exe"'

# When name discovery is needed, CAP THE RECURSION DEPTH to avoid
# hitting the 60s tool timeout:
mios-windows ps 'Get-ChildItem "C:\\Program Files (x86)" -Depth 3 -Filter "*motorfest*" -ErrorAction SilentlyContinue | Select-Object FullName | Format-List'

# Then launch with the discovered path:
mios-windows launch "C:\\Program Files (x86)\\Ubisoft\\Ubisoft Game Launcher\\games\\The Crew Motorfest\\TheCrewMotorfest.exe"
```

**3-fail rule**: if after 3 launch-locator attempts the .exe still
isn't found, STOP + ASK the operator in your reply text: "I checked
Steam / Epic / Ubisoft / GOG common paths -- where is <GameName>
installed on your system?". Do NOT keep running `-Recurse` over
the whole C: drive; each one is a 60s timeout.

NEVER tell the operator "I'd recommend you navigate to the Start Menu
manually" or "Look for <app> in your installed applications". You have
the tools. Use them.

## How

```
mios-windows launch notepad                    # GUI, detached, returns immediately
mios-windows launch explorer "C:\\Users\\mios\\Documents"   # GUI with a starting path
mios-windows launch calc                       # any known short name

mios-windows ps 'Get-Service vmcompute | fl'   # PowerShell, output captured
mios-windows ps 'ipconfig /all | Select-String IPv4'

mios-windows cmd 'tasklist /FI "IMAGENAME eq notepad.exe"'

mios-windows list                              # known short-name -> .exe mappings
mios-windows --help                            # full surface
```

Three backends, one frontend:

| Subcommand | Backend | When to use |
|---|---|---|
| `launch` / `ps` / `cmd` | WSL interop via `/init` -- direct .exe exec | DEFAULT for everything (works without setup) |
| `ssh-ps [-e] "<cmd>"` | Tailscale SSH to the Windows host's PowerShell | Elevated commands (Restart-Service, New-NetFirewallRule), or commands that must run as the operator's interactive Windows user (interop spawns get a SYSTEM-context-ish token) |

Don't use `ssh-ps` unless you have a specific reason -- WSL interop
is faster (no SSH handshake, no Tailscale dependency) and works on
hosts that haven't enabled Tailscale SSH.

## Patterns the agent gets wrong

**Bad**: *"I cannot launch native Windows applications from WSL.
Windows applications require a Windows desktop environment."*
**Why bad**: WSL2 + WSLg + /init *is* that path; you're already on
it; the launch is one shell call away.
**Good**: `mios-windows launch notepad` followed by reporting the
detached PID.

**Bad**: *"I'd need to SSH into another Windows machine."*
**Why bad**: There IS no other machine in the common case -- this
WSL distro lives inside the operator's Windows host. /init handles
the cross-environment exec on the SAME box.
**Good**: `mios-windows launch <app>` (interop, same box) or
`mios-windows ssh-ps "<cmd>"` (Tailscale SSH, only when needed).

**Bad**: *"I'd need a special mechanism."* / *"This requires
interactive shell access I don't have."*
**Why bad**: Both are false. `mios-windows` has the special
mechanism baked in, and your terminal tool has all the access it
needs.
**Good**: Run the call.

## What this isn't

* NOT a way to install Windows software -- for that, the operator uses
  Windows Settings or a package manager (winget, choco) on the
  Windows side; an agent on the Linux side has nothing useful to add.
* NOT a way to run elevated/admin commands transparently -- the
  Windows UAC token of the interop-spawned process is filtered. For
  `Restart-Service`, `New-NetFirewallRule`, registry writes:
  `mios-windows ssh-ps -e "<cmd>"` (placeholder; not yet wired) OR
  ask the operator to run the elevated command in their PowerShell
  themselves.
