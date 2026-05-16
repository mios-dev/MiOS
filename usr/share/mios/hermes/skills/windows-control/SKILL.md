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

## ⚡ ES.EXE (VOIDTOOLS EVERYTHING SEARCH CLI) IS THE PRIMARY METHOD ⚡

Operator directive (repeated 2026-05-16): "they should be using
everything search cli!!! ... MiOS-Agent should use this method first
when trying to do things on the local Windows host machine(s)".

es.exe queries Voidtools Everything's NTFS index in <100 ms. Use it
FIRST for any Windows-side path lookup (file, app, exe, install
dir, game, config, log, anything).

### Two ways to invoke from the agent (BOTH go to es.exe)

**A) `mios-find <query>` (recommended -- agent-context-safe)**

```
mios-find steam            # -> mios-windows launch "C:\Program Files (x86)\Steam\steam.exe"
mios-find beamng           # -> mios-windows launch "D:\...\BeamNG.drive.exe"
mios-find "the crew"       # -> Ubisoft launcher URI
```

mios-find wraps es.exe + Steam/Epic/GOG library scans + flatpak
inventory + Get-StartApps. ALWAYS works from the agent's service-user
context (uid 820); ~60 ms first call, cached after. Returns ONE line
on stdout: the ready-to-execute launch command. Pipe it or just run
the printed line.

**B) `mios-windows ps "& 'M:\Programs\Everything\es.exe' -n 5 <query>"` (broker route, the canonical es.exe path)**

```
mios-windows ps "& 'M:\Programs\Everything\es.exe' -n 5 'steam.exe'"
mios-windows ps "& 'M:\Programs\Everything\es.exe' -n 10 'motorfest'"
mios-windows ps "& 'M:\Programs\Everything\es.exe' -n 5 'config.json'"
```

Goes through `mios-windows ps` -> mios-as-operator -> the launcher
broker -> PowerShell on the Windows side. This gets you direct es.exe
access for custom queries (specific extension, multi-word phrase,
operator-driven exploration). Output: bare Windows paths, one per
line. Verified live 2026-05-16:
  -> C:\Program Files (x86)\Steam\steam.exe
  -> D:\SteamLibrary\steamapps\common\BeamNG.drive\BeamNG.drive.exe
  -> ... etc.

Canonical es.exe location: `M:\Programs\Everything\es.exe` (installed
by mios-bootstrap on every MiOS host). Fallback if M: is unavailable:
`C:\Users\mios\AppData\Local\Programs\Everything\es.exe`. Note:
`C:\Program Files\Everything\es.exe` is the GUI default for the
admin-install of Everything (via winget) which DOES NOT include es.exe
-- the CLI is a separate Voidtools download. Use the M:\ path.

### Forbidden anti-patterns

* `Get-ChildItem -Recurse` over a Windows drive -- never. 60s timeout
  + spams the operator + es.exe already indexed it.
* Guessing paths from memory -- always confirm with es.exe.
* "I'll check common locations..." -- always es.exe FIRST.
* "It's installed at <imagined path>" -- always es.exe to verify.
* Calling `/mnt/m/Programs/Everything/es.exe` DIRECTLY from inside
  WSL -- DOES NOT WORK from the agent's service-user context (perm
  denied via WSL DrvFs exec wall). Always go through `mios-find` OR
  `mios-windows ps "& '<path>' ..."` (broker-routed).

### After finding, LAUNCH via mios-windows launch

mios-windows launch accepts ANY Windows-style path -- it translates
via wslpath internally:

```
mios-windows launch "C:\Program Files (x86)\Steam\steam.exe"
mios-windows launch "D:\SteamLibrary\steamapps\common\BeamNG.drive\BeamNG.drive.exe"
mios-windows launch "%LOCALAPPDATA%\Programs\<App>\<app>.exe"
```

es.exe finds, mios-windows launches. Two commands. ~150 ms total.

If mios-find returns "no match", THEN escalate to:
  * `mios-windows ps "& 'M:\Programs\Everything\es.exe' -n 5 <pattern>"`
    (Voidtools direct query if mios-find's heuristics missed)
  * `mios-windows ps Get-StartApps` (raw Start Menu enumeration)
  * Operator clarification ("Where is X installed?" -- the 3-fail rule)

NEVER reply "I don't have access to the Windows filesystem" -- you have
mios-find, mios-windows, mios-pc-control, AND can call `/mnt/c/Program
Files/Everything/es.exe` directly via WSL interop. Operator-confirmed
2026-05-16 that ALL of these work; refusal phrases are false on this
host (the agent-nudger watches for them + alerts).

## Game / third-party app recipes -- use `mios-find` FIRST (above)

```
# THE ONE-STOP SHOP for "launch X". Returns a ready-to-execute
# launch command in <5 s for ANYTHING in the inventory:
#   * Linux flatpaks (chromedev, ptyxis, nautilus, ...)
#   * Windows Start Menu apps (every UWP + Win32 reachable via
#     Get-StartApps)
#   * Steam games (every appmanifest_*.acf -> steam://rungameid/<id>)
#   * Epic games (every .item manifest -> com.epicgames.launcher://)
#   * GOG games (every Games/<title>/<exe>)
#   * MiOS shims, agent CLIs, internal service URLs
mios-find beamng      # -> mios-windows ps "Start-Process 'steam://rungameid/284160'"
mios-find chrome      # -> mios-gui chromedev  (or windows-app ChromeDev)
mios-find "the crew"  # -> Ubisoft launcher path
mios-find ptyxis      # -> mios-gui ptyxis

# Then just execute the returned command via terminal tool. ONE
# terminal call to discover, ONE to launch. Total ~5 s.
```

This is the SNAPPY path. The operator's directive 2026-05-16:
"MiOS-Hermes should be given the opportunity to map out it's
environment for faster follow-up questions like ex; 'launch this
app for me' should be snappy". `mios-find` IS that map.

## WSL <-> Windows path translation (NEVER fail at this)

When you've located an executable at a `/mnt/c/...` or `/mnt/d/...`
path inside WSL, translate to Windows format BEFORE passing to
`mios-windows launch`. Two tools:

```
# Canonical: wslpath -w converts /mnt/<drv>/... -> <DRV>:\...
wslpath -w /mnt/d/SteamLibrary/steamapps/common/BeamNG.drive/BeamNG.drive.exe
# -> D:\SteamLibrary\steamapps\common\BeamNG.drive\BeamNG.drive.exe

# Then launch with the translated path:
mios-windows launch "$(wslpath -w /mnt/d/SteamLibrary/steamapps/common/BeamNG.drive/BeamNG.drive.exe)"
```

NEVER reply "I don't have the exact Windows path format that works
with the WSL interop system" -- you have wslpath. Operator-confirmed
2026-05-16: agent found BeamNG.drive.exe at /mnt/d/SteamLibrary/...
then GAVE UP on launching it because it didn't translate the path.
The translation is one command.

## Fallback recipes (only when mios-find returns "no match")

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
