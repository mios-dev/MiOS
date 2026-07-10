# AI-hint: Purges stale netsh portproxy entries (0.0.0.0:N to 127.0.0.1:N) that cause Windows to intercept and blackhole local browser requests to MiOS services, restoring proper WSL2 localhost routing.
# AI-related: /usr/libexec/mios/Heal-MiOSLocalhostForwarding.ps1
# /usr/libexec/mios/Heal-MiOSLocalhostForwarding.ps1
#
# Remove the stale `netsh interface portproxy v4tov4 0.0.0.0:N ->
# 127.0.0.1:N` entries left behind by an earlier version of
# Setup-MiOSLanPortProxy.ps1. Those entries make Windows itself answer
# `localhost:N` from the proxy listener (which loops to its own
# 127.0.0.1 where nothing runs), blackholing every browser tab the
# operator opens to a MiOS service URL.
#
# WSL2's built-in localhostForwarding=true in %USERPROFILE%\.wslconfig
# is the right path for Windows-side localhost; LAN-side access from
# phone/tablet needs a different connectaddress (the WSL VM IP,
# resolved at proxy-add time -- handled by the rewritten
# Setup-MiOSLanPortProxy.ps1).
#
# MUST run elevated. Self-elevates via UAC if not already admin.
# Operator-flagged "WEB SERVICES ARENT REACHABLE IN LOCAL
# WINDOWS BROWSER AGAIN!!!!".

$ErrorActionPreference = 'Stop'

# Self-elevate.
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host '  [*] Not elevated. Re-launching via UAC...' -ForegroundColor Yellow
    $relaunchArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath)
    Start-Process -FilePath 'pwsh.exe' -ArgumentList $relaunchArgs -Verb RunAs
    return
}

# Resolve mios.toml path
$tomlPath = $null
foreach ($path in @(
    (Join-Path $env:USERPROFILE '.config\mios\mios.toml'),
    'M:\etc\mios\mios.toml',
    'M:\usr\share\mios\mios.toml',
    'C:\mios-bootstrap\mios.toml'
)) {
    if (Test-Path $path) {
        $tomlPath = $path
        break
    }
}

# Simple toml parser for [ports]
function Get-MiosPort ($key, $default) {
    if ($tomlPath) {
        $content = Get-Content $tomlPath -Raw
        # Extract the [ports] section
        if ($content -match '(?s)\[ports\]\s*\r?\n(.*?)(?=\r?\n\[|$)') {
            $portsSec = $Matches[1]
            if ($portsSec -match "(?m)^\s*$key\s*=\s*([0-9]+)") {
                return [int]$Matches[1]
            }
        }
    }
    return $default
}

$portKeys = @(
    @{ Key = 'hermes'; Default = 8642 },
    @{ Key = 'cockpit'; Default = 8090 },
    @{ Key = 'forge_http'; Default = 8300 },
    @{ Key = 'code_server'; Default = 8800 },
    @{ Key = 'open_webui'; Default = 8033 },
    @{ Key = 'searxng'; Default = 8899 },
    @{ Key = 'llm_light'; Default = 8450 },
    @{ Key = 'agent_pipe'; Default = 8640 },
    @{ Key = 'hermes_dashboard'; Default = 8119 }
)

$ports = foreach ($pk in $portKeys) {
    Get-MiosPort -key $pk.Key -default $pk.Default
}
$cockpitPort = Get-MiosPort -key 'cockpit' -default 8090

Write-Host '--- current portproxy table ---' -ForegroundColor Cyan
& netsh interface portproxy show all

Write-Host ''
Write-Host '--- deleting broken 0.0.0.0:N -> 127.0.0.1:N entries ---' -ForegroundColor Cyan
foreach ($p in $ports) {
    & netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$p 2>&1 | Out-Null
    Write-Host ("  [-] removed portproxy 0.0.0.0:{0}" -f $p) -ForegroundColor Green
}

Write-Host ''
Write-Host '--- portproxy table after cleanup ---' -ForegroundColor Cyan
& netsh interface portproxy show all

Write-Host ''
Write-Host '--- testing WSL2 localhost forwarding ---' -ForegroundColor Cyan
foreach ($p in $ports) {
    $scheme = if ($p -eq $cockpitPort) { 'https' } else { 'http' }
    try {
        $r = Invoke-WebRequest -Uri ("${scheme}://localhost:${p}/") -UseBasicParsing -SkipCertificateCheck -TimeoutSec 3 -ErrorAction Stop
        Write-Host ("  [+] {0}://localhost:{1}/ -> {2}" -f $scheme, $p, $r.StatusCode) -ForegroundColor Green
    } catch {
        $code = 'no-response'
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        Write-Host ("  [!] {0}://localhost:{1}/ -> {2}" -f $scheme, $p, $code) -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host '  Done. Press any key to close this window.' -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
