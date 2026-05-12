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
# Operator-flagged 2026-05-12: "WEB SERVICES ARENT REACHABLE IN LOCAL
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

$ports = 8642,9090,3000,8080,3030,8888,11434,9119

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
    $scheme = if ($p -eq 9090) { 'https' } else { 'http' }
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
