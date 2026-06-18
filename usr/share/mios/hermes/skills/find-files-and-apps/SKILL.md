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
  (/mnt/<drive>, the App Paths registry, the Start Menu, the NTFS file
  index). Each has a dedicated discovery TOOL; this skill maps intent to
  the right one. The cardinal rule: discover by QUERYING the live system,
  not by assuming a path.
metadata:
  hermes:
    requires_tools:
      - find_file_fast
      - app_search
      - list_installed_apps
      - linux_file_search
      - windows_file_search
      - tool_search
---
<!-- AI-hint: Defines the logic for locating files and applications across Linux and Windows filesystems by mapping user intent to specific discovery tools (find_file_fast, app_search, list_installed_apps, linux_file_search, windows_file_search) to resolve concrete paths.
     AI-related: /usr/share/mios/hermes/skills/find-files-and-apps/SKILL.md._, /usr/lib/mios/agent-pipe
     AI-functions: app_search -->

# Locating files & applications on MiOS

> _MiOS-managed: seeded from
> /usr/share/mios/hermes/skills/find-files-and-apps/SKILL.md._

## Cardinal rule

**Navigate the real filesystem; never guess a path or rely on a baked-in
name list.** Every "where is X / is X installed / find X" question has a
TOOL that queries the live environment. Call the tool, read the result,
act on the concrete path it returns. If you don't know which tool, start
with `find_file_fast` (it spans every drive) and narrow from there.

## Pick the tool by what you're locating

| You want to find… | Tool | Covers |
| --- | --- | --- |
| **An app to launch** (any OS) | `app_search(query)` | flatpak ids, .desktop, $PATH CLIs, Windows Start-Menu/App-Paths, games, MiOS shims -- the unified resolver. Returns a runnable launch target. |
| **The full app inventory** | `list_installed_apps()` | Every installed app across Linux (flatpak + RPM .desktop) and Windows (Start Menu, games). Use to enumerate / disambiguate. |
| **A FILE on the Linux side** | `linux_file_search(query, ext?, path?, type?)` | plocate/locate/find over the Linux FHS (/usr, /etc, /var, /home, flatpak exports). Fast, always available, fully offline. |
| **A FILE on the Windows side** | `windows_file_search(query, ext?)` | The NTFS file index across every mounted Windows drive. (Index-gated: if it returns an unreachable error, fall back -- see below.) |
| **A FILE on EITHER side, fast** | `find_file_fast(query, ext?)` | Fast cross-drive find that spans the Linux FHS and the mounted Windows drives in one call. Use when you don't know which side a file is on. |
| **Prior knowledge / a skill / a memory** | `knowledge_search(query)` | The second-brain knowledge store (skills, knowledge, notes). For "have we solved this before", not for disk files. |

## Resolving a fuzzy app name to a concrete launch target

This is generative on BOTH OSes -- no hardcoded name→path table:

- **Linux**: the app is identified by its flatpak app-id or XDG .desktop
  id; the launch target comes from the .desktop `Exec` key (full path,
  else `$PATH`). `app_search` / `list_installed_apps` surface these from
  the live `flatpak list` + `/usr/share/applications` scan.
- **Windows**: a bare name resolves via the **App Paths registry**
  (`HKCU`/`HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\<name>.exe`),
  then the System32 / Windows system dirs, then the Start Menu, then the
  NTFS file index. `resolve_launch_command` does this chain for you;
  `app_search` exposes it for resolve-without-launch.

So to OPEN something, you usually don't pre-resolve at all -- just call
`resolve_launch_command(name=...)` to get the concrete launch command,
then `launch_windows_app(...)` (see the `app-launch` skill) and confirm
with `verify_launch(...)`; the chain is generative. Pre-resolve with
`app_search` / `find_file_fast` only when you need the PATH itself (to
read/edit a file, pass an arg, or disambiguate).

## When a tool can't reach its index (graceful fallback)

- `windows_file_search` returns an unreachable error (the Windows file
  index isn't installed/running on this host, e.g. an incomplete install):
  **don't give up or fabricate a path.** Fall back to `linux_file_search`
  for anything under the Linux FHS, to `find_file_fast` for a fast
  cross-drive sweep, and to `app_search` / `list_installed_apps` (which
  also read the Start Menu + App Paths) for Windows apps. Tell the
  operator the Windows file index is unavailable if a Windows *file* (not
  app) genuinely can't be found another way.
- `find_file_fast` / `app_search` returns multiple candidates: surface
  them and ask which -- never guess one.
- A search returns nothing: widen the query (drop the extension, use a
  shorter substring), try the OTHER OS's tool, then report honestly.
- You're unsure which discovery tool exists for an unusual surface: call
  `tool_search(query)` to discover the right tool at runtime rather than
  guessing a tool name.

## What NOT to do

| Do NOT | Instead |
| --- | --- |
| Assume `/mnt/c/Windows/System32/<x>.exe` or any fixed path | `find_file_fast` / `windows_file_search` resolve it live |
| `terminal: find / -name ...` from the agent uid | `linux_file_search` (it runs plocate in the broker context with the right perms) |
| Keep a mental list of "known apps" | the inventory is `list_installed_apps`; the resolver is `app_search` -- both read the LIVE system |
| Fabricate a path when a tool is unreachable | fall back to another tool (above) and, if all fail, say so |

## Examples

```
# "where is the agent-pipe server?"
linux_file_search(query="server.py", path="/usr/lib/mios/agent-pipe")

# "is VSCodium installed?"
app_search(query="codium")            # -> launch target if present, else candidates

# "find the chrome executable on Windows"
windows_file_search(query="chrome", ext="exe")
#   if the Windows index is unreachable -> app_search(query="chrome")  (Start Menu / App Paths)

# "find a file but I'm not sure which drive it's on"
find_file_fast(query="invoice", ext="pdf")

# "list everything I can launch"
list_installed_apps()

# "have we fixed the executor hang before?"
knowledge_search(query="executor window enumeration hang")
```
