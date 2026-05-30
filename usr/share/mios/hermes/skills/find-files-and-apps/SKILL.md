---
name: find-files-and-apps
description: |
  How to LOCATE files and applications on a MiOS host by navigating the
  real filesystems generatively -- never from a hardcoded list of names
  or paths, never by guessing. Load this whenever you need to find where
  something IS (a binary, a config, a document, an installed app) before
  acting on it: "where is X", "find the X config", "is X installed",
  "resolve X to a launch target", or any step that needs a concrete path.
  MiOS spans TWO filesystems -- the Linux side (FHS: /usr, /etc, /var,
  /home, flatpak app-ids, .desktop entries, $PATH) and the Windows side
  (/mnt/<drive>, the App Paths registry, the Start Menu, the Everything
  index). Each has a dedicated discovery TOOL; this skill maps intent to
  the right one. The cardinal rule: discover by QUERYING the live system,
  not by assuming a path.
metadata:
  hermes:
    requires_tools:
      - mios_find
      - mios_apps
      - fs_search
      - everything_search
      - viking_find
---

# Locating files & applications on MiOS

> _MiOS-managed: seeded from
> /usr/share/mios/hermes/skills/find-files-and-apps/SKILL.md._

## Cardinal rule

**Navigate the real filesystem; never guess a path or rely on a baked-in
name list.** Every "where is X / is X installed / find X" question has a
TOOL that queries the live environment. Call the tool, read the result,
act on the concrete path it returns. If you don't know which tool, start
with `mios_find` (it spans every surface) and narrow from there.

## Pick the tool by what you're locating

| You want to find… | Tool | Covers |
| --- | --- | --- |
| **An app to launch** (any OS) | `mios_find(query)` | flatpak ids, .desktop, $PATH CLIs, Windows Start-Menu/App-Paths/Everything, games, MiOS shims -- the unified resolver. Returns a runnable launch line. |
| **The full app inventory** | `mios_apps()` | Every installed app across Linux (flatpak + RPM .desktop) and Windows (Start Menu, games). Use to enumerate / disambiguate. |
| **A FILE on the Linux side** | `fs_search(query, ext?, path?, type?)` | plocate/locate/find over the Linux FHS (/usr, /etc, /var, /home, flatpak exports). Fast, always available, fully offline. |
| **A FILE on the Windows side** | `everything_search(query, ext?)` | The Voidtools Everything NTFS index across every mounted Windows drive. (Install-gated: if it returns `everything_unreachable`, fall back -- see below.) |
| **Prior knowledge / a skill / a memory** | `viking_find(query, ns?)` | The viking:// second-brain VFS (skills, knowledge, memory). For "have we solved this before", not for disk files. |

## Resolving a fuzzy app name to a concrete launch target

This is generative on BOTH OSes -- no hardcoded name→path table:

- **Linux**: the app is identified by its flatpak app-id or XDG .desktop
  id; the launch target comes from the .desktop `Exec` key (full path,
  else `$PATH`). `mios_find` / `mios_apps` surface these from `flatpak
  list` + the live `/usr/share/applications` scan.
- **Windows**: a bare name resolves via the **App Paths registry**
  (`HKCU`/`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\<name>.exe`),
  then the System32 / Windows system dirs, then the Start Menu, then the
  Everything index. `launch_app` does this chain for you; `mios_find`
  exposes it for resolve-without-launch.

So to OPEN something, you usually don't pre-resolve at all -- just call
`launch_app(name=...)` (see the `app-launch` skill) and it walks the
generative chain. Pre-resolve with `mios_find` only when you need the
PATH itself (to read/edit a file, pass an arg, or disambiguate).

## When a tool can't reach its index (graceful fallback)

- `everything_search` → `everything_unreachable` (the Everything index
  isn't installed/running on this host, e.g. the M:\ install is
  incomplete): **don't give up or fabricate a path.** Fall back to
  `fs_search` for anything under the Linux FHS, and to `mios_find` /
  `mios_apps` (which also read the Start Menu + App Paths) for Windows
  apps. Tell the operator Everything is unavailable if a Windows *file*
  (not app) genuinely can't be found another way.
- `mios_find` returns multiple candidates (exit 2, list in stderr):
  surface them and ask which -- never guess one.
- A search returns nothing: widen the query (drop the extension, use a
  shorter substring), try the OTHER OS's tool, then report honestly.

## What NOT to do

| Do NOT | Instead |
| --- | --- |
| Assume `/mnt/c/Windows/System32/<x>.exe` or any fixed path | `mios_find` / `everything_search` resolve it live |
| `terminal: find / -name ...` from the agent uid | `fs_search` (it runs plocate in the broker context with the right perms) |
| Keep a mental list of "known apps" | the inventory is `mios_apps`; the resolver is `mios_find` -- both read the LIVE system |
| Fabricate a path when a tool is unreachable | fall back to another tool (above) and, if all fail, say so |

## Examples

```
# "where is the agent-pipe server?"
fs_search(query="server.py", path="/usr/lib/mios/agent-pipe")

# "is VSCodium installed?"
mios_find(query="codium")            # -> launch line if present, else candidates

# "find the chrome executable on Windows"
everything_search(query="chrome", ext="exe")
#   if everything_unreachable -> mios_find(query="chrome")  (Start Menu / App Paths)

# "list everything I can launch"
mios_apps()

# "have we fixed the executor hang before?"
viking_find(query="executor window enumeration hang", ns="knowledge")
```
