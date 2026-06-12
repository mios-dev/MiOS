# mios-wsl-keepalive.ps1
#
# Registers the "MiOS-WSL-KeepAlive" scheduled task: hold a PERSISTENT session
# open inside the WSL distro so WSL never tears the VM (and its systemd services)
# down on last-session-detach.
#
# WHY THIS EXISTS
# ---------------
# WSL2 stops a distro's systemd services when the LAST attached session detaches
# (default vmIdleTimeout ~60s). On MiOS this cycles the whole stack every ~30-60s:
# agent-pipe / pgvector / searxng / sglang restart, every MCP server is re-probed
# (Playwright stdio re-spawns), the 8B is swapped in/out of VRAM, and the P0
# byte-stable RadixAttention prefix is destroyed -- which also makes any latency /
# VRAM / offline-eval measurement non-reproducible (operator 2026-06-11). A single
# long-lived `sleep infinity` process keeps a session attached, so WSL keeps the VM
# + all enabled services running continuously.
#
# This task runs that holder at logon AND re-checks every minute: if the holder
# died (a `wsl --shutdown`, a crash, a manual stop), the next tick restarts it
# within ~60s. MultipleInstances=IgnoreNew means only ever ONE holder runs.
#
# Idempotent: safe to re-run (-Force overwrites). Run as the operator (mios);
# NO elevation needed to register a logon task for the current user.
#
# Alternative / complementary OS-level fix (operator, one-time): add to
# %USERPROFILE%\.wslconfig  ->  [wsl2]\nvmIdleTimeout=-1   then `wsl --shutdown`
# once to reload it. The KeepAlive task is the robust default because it also
# survives an explicit shutdown and needs no global WSL config change.
#
# To remove:  Unregister-ScheduledTask -TaskName 'MiOS-WSL-KeepAlive' -Confirm:$false

param(
    [string]$Distro   = 'podman-MiOS-DEV',
    [string]$TaskName = 'MiOS-WSL-KeepAlive'
)

$me = "$env:COMPUTERNAME\$env:USERNAME"
Write-Host "Registering '$TaskName' (run as $me, Interactive/Session 1, logon + every 1 min) -> hold '$Distro' up via sleep infinity"

# Action: a long-lived holder, launched through a HIDDEN powershell host so NO
# console window (Windows Terminal / conhost) ever flashes on the operator's
# desktop. The hidden powershell keeps a console of its own; wsl.exe attaches to
# THAT hidden console instead of allocating a fresh visible one -- the same proven
# `-WindowStyle Hidden` pattern the iGPU / OSControl server tasks use (operator-
# confirmed: those never pop). The powershell process stays alive for as long as
# `sleep infinity` runs, so the holder IS a live attached session and WSL keeps
# the VM + services up. Still Interactive/Session 1 (NOT S4U) so WSLg binds its
# GUI projection to the operator's desktop.
#
# WHY NOT launch wsl.exe directly (the old action): a scheduled-task action that
# execs wsl.exe in an interactive session spawns a visible Windows Terminal /
# conhost window every time it fires. With a 1-min self-heal trigger that meant a
# window flashing onto the operator's desktop, stealing focus, then vanishing
# (operator report 2026-06-12). Wrapping in a hidden powershell removes the flash.
$wslExe  = Join-Path $env:SystemRoot 'System32\wsl.exe'
$psExe   = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$inner   = "& '$wslExe' -d $Distro --exec /usr/bin/sleep infinity"
$action  = New-ScheduledTaskAction -Execute $psExe `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command `"$inner`""

# Trigger: at logon, then repeat every 1 minute forever. The repetition is the
# self-heal: if the holder ever exits (shutdown/crash), the next tick restarts it.
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $me
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition

# Interactive (Session 1) so it shares the operator's session; never S4U.
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited

# ExecutionTimeLimit = 0 -> the holder may run forever (it is supposed to).
# IgnoreNew -> the 1-min ticks never start a SECOND holder while one is alive.
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
                -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
                -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$desc      = "Holds a persistent sleep-infinity session inside the MiOS WSL distro so WSL never tears the VM/services down on last-session-detach (stops the ~30-60s service cycling). Logon + 1-min self-heal; only one holder runs."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Description $desc -Force | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($t) {
    Write-Host ("OK: {0} state={1} runAs={2}({3}) action='{4} {5}'" -f `
        $t.TaskName, $t.State, $t.Principal.UserId, $t.Principal.LogonType, `
        $t.Actions[0].Execute, $t.Actions[0].Arguments)
    Write-Host "Start it now without waiting for logon:  Start-ScheduledTask -TaskName '$TaskName'"
} else {
    Write-Error "Registration failed: task '$TaskName' not found after Register-ScheduledTask"
    exit 1
}
