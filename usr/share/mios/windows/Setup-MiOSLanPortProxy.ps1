# Setup-MiOSLanPortProxy.ps1 — Run as Administrator
# Sets up Windows Firewall rules and portproxy for MiOS AI Node Tailscale access.
# wslrelay binds Podman machine ports on [::1]; v4tov6 bridges Tailscale (IPv4) -> wslrelay (IPv6).

$ErrorActionPreference = 'Stop'

foreach ($entry in @(
    [pscustomobject]@{ Port = 11434; Name = 'MiOS AI Node - mios-ollama (11434/tcp)' },
    [pscustomobject]@{ Port = 11435; Name = 'MiOS AI Node - mios-ollama-cpu (11435/tcp)' }
)) {
    $existing = Get-NetFirewallRule -DisplayName $entry.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Set-NetFirewallRule -DisplayName $entry.Name -Enabled True -Action Allow
        Write-Host "  [+] firewall: refreshed '$($entry.Name)'"
    } else {
        New-NetFirewallRule -DisplayName $entry.Name `
            -Direction Inbound -Action Allow -Protocol TCP `
            -LocalPort $entry.Port -RemoteAddress '100.64.0.0/10' `
            -Profile Any | Out-Null
        Write-Host "  [+] firewall: created '$($entry.Name)'"
    }
}

$svc = Get-Service iphlpsvc -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne 'Running') {
    Set-Service iphlpsvc -StartupType Automatic; Start-Service iphlpsvc
}

foreach ($port in @(11434, 11435)) {
    netsh interface portproxy delete v4tov6 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
    netsh interface portproxy add    v4tov6 listenaddress=0.0.0.0 listenport=$port `
          connectaddress=::1 connectport=$port | Out-Null
    Write-Host "  [+] portproxy 0.0.0.0:${port} -> [::1]:${port}"
}

Write-Host ""
Write-Host "  MiOS AI Node firewall + portproxy configured."
Write-Host "  Ollama GPU  : http://100.79.3.50:11434/v1"
Write-Host "  Ollama CPU  : http://100.79.3.50:11435/v1"
