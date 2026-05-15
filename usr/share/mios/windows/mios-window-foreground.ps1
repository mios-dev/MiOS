# /usr/share/mios/windows/mios-window-foreground.ps1
#
# Find a Windows process by name and bring its main window to the
# foreground. Called from /usr/libexec/mios/mios-windows after a
# `launch` to ensure the new window actually surfaces on the
# operator's interactive desktop (the launch itself succeeds via
# WSL /init exec, but Windows doesn't auto-focus the new window
# when the launching shell isn't itself a foreground app).
#
# Usage (invoked via WSL interop):
#   powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
#     -File <unc-path-to-this-script> -ProcessName notepad
#
# WHY .ps1 INSTEAD OF -Command
#   Bash quoting + cmd.exe quoting + PowerShell quoting compose into
#   an unsolvable escape soup once the script needs `$variable` or
#   `[DllImport("user32.dll")]`. A real .ps1 file with $vars and
#   strings reads CLEAN to PowerShell because no shell layer above it
#   touches the contents.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProcessName,
    [Parameter()][int]$WaitMs = 200,
    [Parameter()][int]$MaxAttempts = 5
)

# Strip a trailing .exe -- Get-Process expects the bare name.
$ProcessName = $ProcessName -replace '\.exe$', ''

# Wait for the process to appear (the launch + window-creation race
# is real on slower spawn paths; ~1s budget).
for ($i = 0; $i -lt $MaxAttempts; $i++) {
    $proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowHandle -ne 0 } |
            Sort-Object StartTime -Descending |
            Select-Object -First 1
    if ($proc) { break }
    Start-Sleep -Milliseconds $WaitMs
}

if (-not $proc) {
    Write-Output ("[mios-window-foreground] no '{0}' process with a window found after {1} attempts" -f $ProcessName, $MaxAttempts)
    exit 1
}

# AppActivate is the documented "raise this window" call that doesn't
# need a Win32 P/Invoke. Returns $true on success.
$shell = New-Object -ComObject WScript.Shell
$ok = $shell.AppActivate($proc.Id)

Write-Output ("[mios-window-foreground] {0} PID {1} window='{2}' foreground={3}" -f $ProcessName, $proc.Id, $proc.MainWindowTitle, $ok)
exit 0
