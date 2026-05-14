# /usr/libexec/mios/Setup-MiOSLanPortProxy.ps1
#
# Open the MiOS service ports on Windows' physical NIC so other LAN
# devices (phone / tablet / laptop) can reach the dev VM's containers
# at <Windows-host-IP>:NNNN. Adds Windows Firewall inbound allow rules
# + netsh portproxy 0.0.0.0:NNNN -> 127.0.0.1:NNNN entries (the
# 127.0.0.1 side bounces into WSL via .wslconfig's localhostForwarding).
#
# MUST run elevated. The script self-checks and re-launches itself
# via UAC if not already admin.
#
# Operator-flagged 2026-05-11: "none of my services are available on
# my local wifi network".

$ErrorActionPreference = 'Stop'

# Self-elevate if not admin.
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host '  [*] Not elevated. Re-launching via UAC...' -ForegroundColor Yellow
    $args = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath)
    Start-Process -FilePath 'pwsh.exe' -ArgumentList $args -Verb RunAs
    return
}

$portMap = @(
    @{ Port = 3000;  Name = 'forge'            }
    @{ Port = 3030;  Name = 'open-webui'       }
    @{ Port = 8080;  Name = 'code-server'      }
    @{ Port = 8642;  Name = 'hermes'           }
    @{ Port = 8888;  Name = 'searxng'          }
    @{ Port = 9090;  Name = 'cockpit'          }
    @{ Port = 9119;  Name = 'hermes-dashboard' }
    @{ Port = 11434; Name = 'ollama'           }
)

# 1. iphlpsvc must be running for netsh portproxy.
$svc = Get-Service -Name iphlpsvc -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne 'Running') {
    Write-Host '  [*] Starting IP Helper service...' -ForegroundColor Cyan
    Set-Service -Name iphlpsvc -StartupType Automatic
    Start-Service -Name iphlpsvc
}

# 2. netsh portproxy: listen on 0.0.0.0:PORT, forward to 127.0.0.1:PORT.
foreach ($p in $portMap) {
    $port = $p.Port
    & netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port | Out-Null
    & netsh interface portproxy add    v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=127.0.0.1 connectport=$port | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host ("  [+] portproxy 0.0.0.0:{0} -> 127.0.0.1:{0}  ({1})" -f $port, $p.Name) -ForegroundColor Green
    } else {
        Write-Host ("  [!] portproxy add for {0} failed" -f $port) -ForegroundColor Red
    }
}

# 3. Windows Defender Firewall inbound allow rules for each port.
foreach ($p in $portMap) {
    $port = $p.Port
    $name = "MiOS - $($p.Name) ($port/tcp)"
    $existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
    if ($existing) {
        Set-NetFirewallRule -DisplayName $name -Enabled True -Action Allow -Direction Inbound -Profile 'Private,Domain' -ErrorAction SilentlyContinue
        $existing | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort $port -ErrorAction SilentlyContinue
        Write-Host ("  [.] firewall: refreshed '{0}'" -f $name) -ForegroundColor DarkGray
    } else {
        New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Profile 'Private','Domain' | Out-Null
        Write-Host ("  [+] firewall: created '{0}'" -f $name) -ForegroundColor Green
    }
}

# 4. Show the resulting state + the LAN URLs the operator can hit.
Write-Host ''
Write-Host '--- netsh portproxy table ---' -ForegroundColor Cyan
& netsh interface portproxy show all

Write-Host ''
Write-Host '--- LAN URLs ---' -ForegroundColor Cyan
$wifi = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
         Where-Object { $_.IPAddress -match '^192\.168\.' -or $_.IPAddress -match '^10\.' -or $_.IPAddress -match '^172\.(1[6-9]|2[0-9]|3[01])\.' } |
         Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|WSL' } |
         Select-Object -First 1).IPAddress
if (-not $wifi) { $wifi = '<your-windows-ip>' }
foreach ($p in $portMap) {
    $scheme = if ($p.Port -eq 9090) { 'https' } else { 'http' }
    Write-Host ("  {0}://{1}:{2}/   ({3})" -f $scheme, $wifi, $p.Port, $p.Name)
}

Write-Host ''
Write-Host '  Done. Press any key to close this window.' -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
