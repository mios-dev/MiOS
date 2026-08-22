<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Registers a scheduled task to boot the podman-MiOS-DEV WSL distro at interactive logon, ensuring WSLg/msrdc binds Linux GUI windows to the user's Session 1 instead of an invisible Session 0.
AI-related: mios-wsl-session-task
mios-wsl-session-task.ps1

Registers the "MiOS-WSL-Session" scheduled task: at the operator's
INTERACTIVE logon (Session 1), start the WSL VM so WSLg/msrdc binds its
Linux-GUI window projection to the operator's session.

WHY THIS EXISTS
---------------
WSLg projects Linux windows into the Windows session that FIRST starts the
WSL VM. If a NON-INTERACTIVE Session 0 process starts it first (a boot task,
or a tool whose process runs in Session 0 such as an automation/agent
harness), msrdc spawns in Session 0 and every Linux GUI window renders to
the invisible Session-0 desktop -- apps "launch" (process runs) but no
window ever appears on the operator's RDP/console desktop (Session 1).
Operator-confirmed a Session-0 `wsl` start made all Linux
flatpak windows invisible; restarting WSL from the operator's own Session-1
terminal fixed it. This task makes that the automatic behaviour every boot.

Idempotent: safe to re-run (-Force overwrites). Run as the operator (mios);
no elevation needed to register a logon task for the current user.

To remove:  Unregister-ScheduledTask -TaskName 'MiOS-WSL-Session' -Confirm:$false

<!-- mios-src:f7d5edcad312 from usr/share/mios/windows/mios-wsl-session-task.ps1:1-24 -->

