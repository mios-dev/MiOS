# AI-hint: Registers a Windows Scheduled Task to run a hidden PowerShell process that maintains a persistent WSL session via `sleep infinity`, preventing the WSL VM and its internal services (systemd, pgvector, sglang) from shutting down.
# AI-related: mios-wsl-keepalive
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
# VRAM / offline-eval measurement non-reproducible. A single
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

[CmdletBinding()]
param(
    [string]$Distro   = 'podman-MiOS-DEV',
    [string]$TaskName = 'MiOS-WSL-KeepAlive',
    [switch]$Install,
    [switch]$Uninstall
)

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
