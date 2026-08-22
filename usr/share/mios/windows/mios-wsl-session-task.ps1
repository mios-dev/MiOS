# AI-hint: Registers a scheduled task to boot the podman-MiOS-DEV WSL distro at interactive logon, ensuring WSLg/msrdc binds Linux GUI windows to the use...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_share_mios_windows_mios_wsl_session_task_ps1.md

param(
    [string]$Distro   = '',
    [string]$TaskName = 'MiOS-WSL-Session'
)

if (-not $Distro) {
    if (Get-Command Resolve-MiosDistro -ErrorAction SilentlyContinue) { $Distro = Resolve-MiosDistro }
    else { $Distro = 'podman-MiOS-DEV' }
}

$toolExe   = Join-Path $PSScriptRoot 'MiosServiceTool.exe'
$wslExe    = Join-Path $env:SystemRoot 'System32\wsl.exe'
$psExe     = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$inner     = "& '$wslExe' -d $Distro -- /bin/true"
$action    = New-ScheduledTaskAction -Execute $toolExe `
    -Argument "-Run `"$psExe`" -NoProfile -ExecutionPolicy Bypass -Command `"$inner`""
$trigger   = New-ScheduledTaskTrigger -AtStartup
# SYSTEM + ServiceAccount: starts the WSL VM pre-graphical logon
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
                -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
                -MultipleInstances IgnoreNew
$desc      = "Starts the MiOS WSL VM at system startup as SYSTEM pre-graphical logon so backend VM services are active immediately."

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
