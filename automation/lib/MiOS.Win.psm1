# AI-hint: Windows Task Scheduler and interpreter resolution helper module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MiosPowerShellExe {
    $psExe = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
    if (-not $psExe -or $psExe -like '*\WindowsApps\*' -or -not (Test-Path -LiteralPath $psExe)) {
        $psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    }
    return $psExe
}

function Register-MiosScheduledTask {
    param(
        [Parameter(Mandatory)][string]$TaskName,
        [Parameter(Mandatory)][string]$ScriptPath,
        [string]$Arguments = '',
        [string]$Description = '',
        [switch]$Elevated
    )
    $psExe = Get-MiosPowerShellExe
    $toolExe = Join-Path (Split-Path -Parent $ScriptPath) 'MiosServiceTool.exe'
    $argline = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`" $Arguments"

    if (Test-Path -LiteralPath $toolExe) {
        $action = New-ScheduledTaskAction -Execute $toolExe -Argument "-Run `"$psExe`" $argline"
    } else {
        $action = New-ScheduledTaskAction -Execute $psExe -Argument $argline
    }

    $trigger = New-ScheduledTaskTrigger -AtLogon
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

    $principal = if ($Elevated) {
        New-ScheduledTaskPrincipal -GroupId 'BUILTIN\Administrators' -RunLevel Highest
    } else {
        New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
    }

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description $Description -Force | Out-Null
    if (Get-Command Start-ScheduledTask -ErrorAction SilentlyContinue) {
        Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    }
}

Export-ModuleMember -Function Get-MiosPowerShellExe, Register-MiosScheduledTask
