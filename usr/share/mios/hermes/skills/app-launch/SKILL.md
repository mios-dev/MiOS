---
name: app-launch
description: |
  The canonical chain for launching ANY app, game, URL, or system
  service on a MiOS host. Load this skill whenever the operator says
  "launch / open / start / run X", whether X is a Windows .exe, a
  Steam/Epic/Xbox game, a flatpak, an RPM with a .desktop entry, or
  an internal MiOS service URL. There is exactly ONE entry point:
  the native `launch_app` tool. Do NOT shell out to wsl / cmd /
  powershell / start-process / xdg-open / flatpak run / steam.exe
  yourself -- those paths consistently fail in the agent's execution
  context (no /init interop inside the agent uid, no WSLg env, no
  Windows ACL access) and the model has been observed looping 6+
  failed shell calls before giving up. The mios_verbs.launch_app
  native tool handles every dispatch shape correctly via the
  operator-side launcher broker.
metadata:
  hermes:
    requires_tools:
      - launch_app
---

# Launching apps on MiOS

<!-- MiOS-managed: seeded from
     /usr/share/mios/hermes/skills/app-launch/SKILL.md. -->

## ONE rule

For ANY launch intent, the FIRST and (usually) ONLY tool you call is:

```
launch_app(name="<exact-or-substring>")
```

That's it. `launch_app` resolves through the canonical mios-launch
chain (internal-service alias -> URL/URI literal -> Windows GUI
shortname -> Windows games inventory -> MiOS shim -> Linux GUI ->
plain CLI), dispatches through the operator-side launcher broker
(which has the WSL interop env + Windows ACL access the agent uid
lacks), and returns the resolved dispatch target so you can confirm
it landed.

## What NOT to try (each has failed for the model before)

| Do NOT | Why |
| --- | --- |
| `terminal: wsl <app>` | The agent IS already inside WSL; there is no `wsl` binary in its PATH |
| `terminal: cmd /c start <app>` | `cmd.exe` lives at `/mnt/c/Windows/System32/cmd.exe`; the agent uid (mios-hermes) cannot exec DrvFs binaries -- "Permission denied" |
| `terminal: powershell ...` | Same DrvFs exec wall as cmd.exe; "command not found" in the agent's PATH |
| `terminal: steam://...` | A URI is not a shell command -- bash exits 127 |
| `terminal: flatpak run ...` | The agent's user@<uid> session is NOT the operator's; flatpak inherits the WRONG WAYLAND_DISPLAY, the window never surfaces |
| `browser_navigate https://...` | The CDP backend (port 9222) is only up when the operator has chromedev running; you can't use this to launch an APP |

The launcher broker (`/run/mios-launcher/launcher.sock`) exists
SPECIFICALLY to bypass all of the above. `launch_app` uses it.
Trust the tool.

## Examples

```
# Operator: "open BeamNG"
launch_app(name="beamng")
# -> {"success": true, "target": "steam://rungameid/284160", ...}

# Operator: "launch wallpaper engine"
launch_app(name="wallpaper engine")
# -> {"success": true, "target": "steam://rungameid/431960", ...}

# Operator: "open chromedev"
launch_app(name="chromedev")
# -> {"success": true, "target": "/usr/bin/flatpak run --branch=stable com.google.ChromeDev", ...}

# Operator: "open the cockpit dashboard"
launch_app(name="cockpit")
# -> {"success": true, "target": "https://localhost:9090", ...}

# Operator: "launch notepad"
launch_app(name="notepad")
# -> {"success": true, "target": "/mnt/c/Windows/System32/notepad.exe", ...}
```

## When launch_app needs help

The substring resolver is fuzzy. If you call `launch_app("steam")`
and get multiple games back as candidates (exit_code=2, stderr lists
matches), call it again with a MORE specific name from the list --
do not assume / guess. Resolution failures return their candidate
list in stderr; surface those candidates to the operator and ask
which one.

If `launch_app` returns `success=false` with `stderr` containing
"no resolution", THEN (and only then) reach for `everything_search`
to find the app on disk + retry `launch_app` with the discovered
path.

## When to deviate

Only when the operator says "I want to run this raw shell command"
(verbatim instruction to use `terminal`). Otherwise: `launch_app`.
