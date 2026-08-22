<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: PowerShell script used by mios-windows to force a specific Windows process's main window into the foreground via AppActivate after a WSL-initiated launch to ensure UI focus.
AI-related: /usr/share/mios/windows/mios-window-foreground.ps1, /usr/libexec/mios/mios-windows, mios-windows, mios-window-foreground
/usr/share/mios/windows/mios-window-foreground.ps1

Find a Windows process by name and bring its main window to the
foreground. Called from /usr/libexec/mios/mios-windows after a
`launch` to ensure the new window actually surfaces on the
operator's interactive desktop (the launch itself succeeds via
WSL /init exec, but Windows doesn't auto-focus the new window
when the launching shell isn't itself a foreground app).

Usage (invoked via WSL interop):
  powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
    -File <unc-path-to-this-script> -ProcessName notepad

WHY .ps1 INSTEAD OF -Command
  Bash quoting + cmd.exe quoting + PowerShell quoting compose into
  an unsolvable escape soup once the script needs `$variable` or
  `[DllImport("user32.dll")]`. A real .ps1 file with $vars and
  strings reads CLEAN to PowerShell because no shell layer above it
  touches the contents.

<!-- mios-src:bd03957634f3 from usr/share/mios/windows/mios-window-foreground.ps1:1-21 -->

