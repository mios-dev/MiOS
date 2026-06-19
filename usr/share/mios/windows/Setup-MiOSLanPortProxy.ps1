# AI-hint: Configures Windows Firewall rules and netsh portproxy for port 11450 to bridge Tailscale IPv4 traffic to local Podman/WSL instances for MiOS AI Node LLM Light access.
# AI-related: mios-llm-light
# Setup-MiOSLanPortProxy.ps1 — Run as Administrator
# Sets up Windows Firewall rules and portproxy for MiOS AI Node Tailscale access.
# wslrelay binds Podman machine ports on [::1]; v4tov6 bridges Tailscale (IPv4) -> wslrelay (IPv6).

$ErrorActionPreference = 'Stop'

# Clean up old firewall rules and portproxies
foreach ($port in @(11434, 11435)) {
    $name = "MiOS AI Node - mios-ollama ($port/tcp)"
    if ($port -eq 11435) { $name = "MiOS AI Node - mios-ollama-cpu ($port/tcp)" }
    Remove-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Out-Null
    netsh interface portproxy delete v4tov6 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
}

$entry = [pscustomobject]@{ Port = 11450; Name = 'MiOS AI Node - mios-llm-light (11450/tcp)' }
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

$svc = Get-Service iphlpsvc -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne 'Running') {
    Set-Service iphlpsvc -StartupType Automatic; Start-Service iphlpsvc
}

$port = 11450
netsh interface portproxy delete v4tov6 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
netsh interface portproxy add    v4tov6 listenaddress=0.0.0.0 listenport=$port `
      connectaddress=::1 connectport=$port | Out-Null
Write-Host "  [+] portproxy 0.0.0.0:${port} -> [::1]:${port}"

# Dynamic Tailscale IP resolution
$tsIp = try { (& tailscale ip --4 2>$null).Trim() } catch { '100.79.3.50' }
if ($tsIp -notmatch '^\d+\.\d+\.\d+\.\d+$') { $tsIp = '100.79.3.50' }

Write-Host ""
Write-Host "  MiOS AI Node firewall + portproxy configured."
Write-Host "  LLM Light GPU/CPU  : http://${tsIp}:11450/v1"
