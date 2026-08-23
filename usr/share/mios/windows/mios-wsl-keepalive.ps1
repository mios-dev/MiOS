# AI-hint: Registers a Windows Scheduled Task to run a hidden PowerShell process that maintains a persistent WSL session via `sleep infinity`, preventing th...
# AI-doc: usr/share/doc/mios/manual/windows.md

[CmdletBinding()]
param(
    [string]$Distro   = '',
    [string]$TaskName = 'MiOS-WSL-KeepAlive',
    [switch]$Install,
    [switch]$Uninstall
)

if (-not $Distro) {
    if (Get-Command Resolve-MiosDistro -ErrorAction SilentlyContinue) { $Distro = Resolve-MiosDistro }
    else { $Distro = 'podman-MiOS-DEV' }
}

if ($Uninstall) {
    # Stop and remove Windows Service if it exists
    if (Get-Service -Name $TaskName -ErrorAction SilentlyContinue) {
        Stop-Service -Name $TaskName -Force -ErrorAction SilentlyContinue
        sc.exe delete $TaskName | Out-Null
    }
    
    # Delete old scheduled task
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    
    # Clean up wrapper files
    $targetExe = Join-Path $PSScriptRoot "$TaskName.exe"
    $targetCfg = Join-Path $PSScriptRoot "$TaskName.cfg"
    Remove-Item $targetExe -Force -ErrorAction SilentlyContinue
    Remove-Item $targetCfg -Force -ErrorAction SilentlyContinue
    Write-Host "  [+] removed task '$TaskName'"
    return
}

if ($Install) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warning 'Not elevated -- re-launching via UAC to register the task...'
        Start-Process -FilePath 'pwsh.exe' -Verb RunAs -ArgumentList @(
            '-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-Install',
            '-Distro',$Distro,'-TaskName',$TaskName)
        return
    }

    # Stop and remove Windows Service if it exists
    if (Get-Service -Name $TaskName -ErrorAction SilentlyContinue) {
        Stop-Service -Name $TaskName -Force -ErrorAction SilentlyContinue
        sc.exe delete $TaskName | Out-Null
    }
    
    # Clean up wrapper files
    $targetExe = Join-Path $PSScriptRoot "$TaskName.exe"
    $targetCfg = Join-Path $PSScriptRoot "$TaskName.cfg"
    Remove-Item $targetExe -Force -ErrorAction SilentlyContinue
    Remove-Item $targetCfg -Force -ErrorAction SilentlyContinue

    # Resolve concrete interpreter path
    $psExe = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
    if (-not $psExe -or $psExe -like '*\WindowsApps\*' -or -not (Test-Path $psExe)) {
        $psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    }

    $toolExe = Join-Path $PSScriptRoot 'MiosServiceTool.exe'
    $wslExe  = Join-Path $env:SystemRoot 'System32\wsl.exe'
    $inner   = "& `"$wslExe`" -d $Distro --exec /usr/bin/sleep infinity"

    $action  = New-ScheduledTaskAction -Execute $toolExe `
        -Argument "-Run `"$psExe`" -NoProfile -ExecutionPolicy Bypass -Command `"$inner`""

    $trigger = New-ScheduledTaskTrigger -AtLogon
    $settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
                    -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
                    -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    
    $principal = New-ScheduledTaskPrincipal -GroupId "BUILTIN\Administrators" -RunLevel Highest
    $desc = "Holds a persistent sleep-infinity session inside the MiOS WSL distro so WSL never tears the VM/services down on last-session-detach. Runs hidden in Session 1."

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Principal $principal -Settings $settings -Description $desc -Force | Out-Null

    Write-Host "  [+] registered logon scheduled task '$TaskName'"
    Write-Host "  [*] starting it now..."
    Start-ScheduledTask -TaskName $TaskName
    return
}

# Standard run path (when wrapped as a service or run directly)
$wslExe  = Join-Path $env:SystemRoot 'System32\wsl.exe'
Write-Host "Starting WSL Keep-Alive for distro '$Distro'..."
& $wslExe -d $Distro --exec /usr/bin/sleep infinity
