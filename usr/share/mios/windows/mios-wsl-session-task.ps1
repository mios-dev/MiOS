# mios-wsl-session-task.ps1
#
# Registers the "MiOS-WSL-Session" scheduled task: at the operator's
# INTERACTIVE logon (Session 1), start the WSL VM so WSLg/msrdc binds its
# Linux-GUI window projection to the operator's session.
#
# WHY THIS EXISTS
# ---------------
# WSLg projects Linux windows into the Windows session that FIRST starts the
# WSL VM. If a NON-INTERACTIVE Session 0 process starts it first (a boot task,
# or a tool whose process runs in Session 0 such as an automation/agent
# harness), msrdc spawns in Session 0 and every Linux GUI window renders to
# the invisible Session-0 desktop -- apps "launch" (process runs) but no
# window ever appears on the operator's RDP/console desktop (Session 1).
# Operator-confirmed 2026-05-30: a Session-0 `wsl` start made all Linux
# flatpak windows invisible; restarting WSL from the operator's own Session-1
# terminal fixed it. This task makes that the automatic behaviour every boot.
#
# Idempotent: safe to re-run (-Force overwrites). Run as the operator (mios);
# no elevation needed to register a logon task for the current user.
#
# To remove:  Unregister-ScheduledTask -TaskName 'MiOS-WSL-Session' -Confirm:$false

param(
    [string]$Distro   = 'podman-MiOS-DEV',
    [string]$TaskName = 'MiOS-WSL-Session'
)

$me = "$env:COMPUTERNAME\$env:USERNAME"
Write-Host "Registering '$TaskName' (run as $me, Interactive/Session 1, at logon) -> start WSL distro '$Distro'"

# Action: booting the distro starts systemd (boot=systemd) + all enabled MiOS
# services and brings up WSLg in THIS (interactive) session. /bin/true returns
# immediately; the distro keeps running because systemd + services persist.
$action    = New-ScheduledTaskAction -Execute 'wsl.exe' -Argument "-d $Distro -- /bin/true"
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User $me
# LogonType Interactive == "run only when user is logged on" -> runs in the
# operator's interactive session (Session 1). Do NOT use S4U (session-less).
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
                -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
                -MultipleInstances IgnoreNew
$desc      = "Starts the MiOS WSL VM from the operator's INTERACTIVE (Session 1) logon so WSLg/msrdc projects Linux GUI windows onto the operator's desktop, not the invisible Session 0."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Description $desc -Force | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($t) {
    Write-Host ("OK: {0} state={1} runAs={2}({3}) action='{4} {5}'" -f `
        $t.TaskName, $t.State, $t.Principal.UserId, $t.Principal.LogonType, `
        $t.Actions[0].Execute, $t.Actions[0].Arguments)
} else {
    Write-Error "Registration failed: task '$TaskName' not found after Register-ScheduledTask"
    exit 1
}
