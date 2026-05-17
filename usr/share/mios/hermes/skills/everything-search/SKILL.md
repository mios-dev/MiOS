---
name: everything-search
description: |
  Find ANY file or installation on ANY mounted NTFS drive in sub-100ms
  via the Voidtools Everything CLI. Load this skill whenever the
  operator asks you to find / launch / open / locate a Windows app,
  game, file, folder, or executable -- ESPECIALLY when mios-find or
  mios-apps come back empty. Do NOT fabricate "I searched Steam --
  not found" or "I checked Program Files -- nothing"; the only
  authoritative answer for "is X on disk anywhere" is mios-everything.
metadata:
  hermes:
    requires_tools:
      - terminal
---

# Everything Search — authoritative Windows-side file finder

<!-- MiOS-managed: seeded from
     /usr/share/mios/hermes/skills/everything-search/SKILL.md. -->

## When to use this skill

Load + use `mios-everything` IMMEDIATELY when ANY of the following
fire — do not narrate "let me try Steam" first; that path lies:

- Operator says "launch / open / start / run / find / locate **X**"
  AND `mios-find X` returned empty / not-found
- Operator says "where is X installed?" / "is X on this system?"
- You are about to claim "X is not installed" — verify with
  `mios-everything` FIRST. The Everything index covers every NTFS
  drive mounted on the Windows side; if it's not in the index it
  genuinely is not on disk.
- You need an `.exe`, `.lnk`, save file, config file, or any other
  artifact whose path you don't know

## How to call it

`mios-everything` is on `$PATH`. It is a thin wrapper around
Voidtools `es.exe` invoked over WSL interop. Sub-100ms typical.
Exit 0 with one Windows path per stdout line; exit 1 on no-match.

Call it via the `terminal` tool (it is NOT a native tool name):

```
terminal: mios-everything "<query>"
```

### Query syntax (Everything CLI)

| Want                            | Query                                   |
| ------------------------------- | --------------------------------------- |
| Substring on filename           | `mios-everything BeamNG`                |
| Specific extension              | `mios-everything BeamNG.exe`            |
| Wildcard                        | `mios-everything "BeamNG*.exe"`         |
| Filter by path                  | `mios-everything "BeamNG path:steamapps"` |
| Limit results                   | `mios-everything BeamNG -n 5`           |
| Multiple extensions             | `mios-everything BeamNG -ext exe,lnk`   |
| Recent file                     | `mios-everything "dm:today *.log"`      |
| Large files                     | `mios-everything "size:>1gb"`           |

## Canonical workflow when launching a Windows game

```
# 1. Inventory check (fast; reads cache)
terminal: mios-apps                                  # look in == windows-game ==
# 2. If not in the apps cache, hit the index
terminal: mios-everything "<name>" -ext exe,lnk      # authoritative
# 3. If found, launch the discovered .exe / .lnk via the broker
terminal: mios-launch "<discovered_path_or_short_name>"
# 4. Verify the window came up
terminal: mios-window-active "<expected_window_substring>"
```

`mios-apps` is a 5-min cached inventory of installed apps (Steam +
Epic + Xbox + flatpak + RPM). When the operator launches a NEW
install or you suspect the cache is stale, jump straight to
`mios-everything` — it queries the live NTFS index and is never stale.

## What NOT to do

- Don't say "I searched Steam / Epic / Program Files" unless you
  actually ran `mios-everything path:steamapps` etc. Claiming a
  negative without checking the index is a fabrication.
- Don't use raw PowerShell `Get-ChildItem -Recurse` or `dir /s` --
  hours slower, locks the filesystem, no value over Everything.
- Don't call `mios-everything` as if it were a native tool
  (`mios-everything BeamNG` standalone). It is a SHELL COMMAND --
  invoke via the `terminal` tool with the full command string.
- Don't give up after one empty result. Try variations: alt spelling
  ("BeamNG.drive" vs "beamng"), shorter substring, different
  extension filter.
