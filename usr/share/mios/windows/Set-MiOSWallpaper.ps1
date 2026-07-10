<#
  Set-MiOSWallpaper.ps1 — resolve the MiOS Living Wallpaper URL from the
  mios.toml [colors] SSOT and write it to HKLM\SOFTWARE\MiOS\WallpaperUrl.

  This is the missing SSOT link: MiOS-Wallpaper-Service reads WallpaperUrl and
  passes it to the host, and living-wallpaper.html reads the 12 palette tokens
  (+ mode) from the URL query string. Without this key the page silently falls
  back to its built-in TOKENS — a hardcode. Run this:
    * as the GLOBAL REFRESH after any palette / theme change, and
    * at image-build / first-boot to bake the factory default (MiOS-Xbox).

  The palette is NEVER hardcoded here — it is read live from mios.toml through
  the standard three-layer overlay (user > host > vendor). The built-in map
  below is only a last-resort default and matches the page's own fallback, so a
  missing key can never surprise.

  Usage:
    Set-MiOSWallpaper.ps1                 # resolve palette + auto (DE) mode, write key
    Set-MiOSWallpaper.ps1 -Mode dark      # force dark
    Set-MiOSWallpaper.ps1 -Mode light     # force light
    Set-MiOSWallpaper.ps1 -Restart        # also restart the wallpaper service
#>
[CmdletBinding()]
param(
    [ValidateSet('auto','dark','light')] [string]$Mode = 'auto',
    [switch]$Restart
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# The 12 wallpaper tokens ARE the mios.toml [colors] semantic keys. Defaults here
# mirror the page's own fallback so a missing key is a no-op, never a surprise.
$Tokens = [ordered]@{
    bg      = '#282262'; fg      = '#E7DFD3'; accent = '#1A407F'; cursor = '#F35C15'
    success = '#3E7765'; warning = '#F35C15'; error  = '#DC271B'; info   = '#1A407F'
    muted   = '#948E8E'; subtle  = '#B7C9D7'; earth  = '#734F39'; silver = '#E0E0E0'
}

# Three-layer overlay candidate paths, ordered HIGHEST priority first.
$Layers = @(
    (Join-Path $env:USERPROFILE '.config\mios\mios.toml'),   # user
    'C:\ProgramData\MiOS\mios.toml',                         # host / admin
    'C:\Windows\Web\MiOS\mios.toml',                         # vendor (deployed)
    (Join-Path $PSScriptRoot '..\mios.toml')                # vendor (repo layout)
)

function Get-ColorsFromToml([string]$path) {
    $out = @{}
    if (-not (Test-Path -LiteralPath $path)) { return $out }
    $inColors = $false
    foreach ($line in Get-Content -LiteralPath $path) {
        $t = $line.Trim()
        if ($t -match '^\[(.+)\]') { $inColors = ($Matches[1].Trim() -eq 'colors'); continue }
        if (-not $inColors) { continue }
        # key = "#rrggbb"   # comment
        if ($t -match '^([A-Za-z0-9_]+)\s*=\s*"?#?([0-9A-Fa-f]{3,8})"?') {
            $out[$Matches[1]] = '#' + $Matches[2]
        }
    }
    return $out
}

# Start from defaults, then apply layers low->high so the highest-priority layer wins.
$resolved = [ordered]@{}
foreach ($k in $Tokens.Keys) { $resolved[$k] = $Tokens[$k] }
for ($i = $Layers.Count - 1; $i -ge 0; $i--) {
    $c = Get-ColorsFromToml $Layers[$i]
    foreach ($k in $Tokens.Keys) { if ($c.ContainsKey($k) -and $c[$k]) { $resolved[$k] = $c[$k] } }
}

# Mode: auto follows the Windows apps light/dark theme (real DE light/dark sync).
if ($Mode -eq 'auto') {
    $useLight = 0
    try {
        $p = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
        $useLight = [int](Get-ItemProperty -Path $p -Name 'AppsUseLightTheme' -ErrorAction Stop).AppsUseLightTheme
    } catch { $useLight = 0 }
    $Mode = if ($useLight -eq 1) { 'light' } else { 'dark' }
}

# Build the query string (hex WITHOUT '#', matching the page's URLSearchParams parser).
$pairs = foreach ($k in $Tokens.Keys) { "$k=" + ($resolved[$k] -replace '^#','') }
$query = ($pairs -join '&') + "&mode=$Mode"
$url   = "file:///C:/Windows/Web/MiOS/living-wallpaper.html?$query"

# Write the SSOT-derived URL + ensure the master toggle exists (default ON).
$root = 'HKLM:\SOFTWARE\MiOS'
if (-not (Test-Path $root)) { New-Item -Path $root -Force | Out-Null }
Set-ItemProperty -Path $root -Name 'WallpaperUrl' -Value $url -Type String -Force

$wp = 'HKLM:\SOFTWARE\MiOS\Wallpaper'
if (-not (Test-Path $wp)) { New-Item -Path $wp -Force | Out-Null }
if (-not (Get-ItemProperty -Path $wp -Name 'Enabled' -ErrorAction SilentlyContinue)) {
    New-ItemProperty -Path $wp -Name 'Enabled' -Value 1 -PropertyType DWord -Force | Out-Null
}

Write-Host "[+] HKLM\SOFTWARE\MiOS\WallpaperUrl set from mios.toml [colors] SSOT (mode=$Mode):" -ForegroundColor Green
Write-Host "    $url"

if ($Restart) {
    try {
        Restart-Service -Name 'MiOS-Wallpaper-Service' -Force -ErrorAction Stop
        Write-Host "[+] Restarted MiOS-Wallpaper-Service." -ForegroundColor Green
    } catch {
        Write-Warning "Could not restart MiOS-Wallpaper-Service: $($_.Exception.Message)"
    }
    # Drop any live hosts so they relaunch against the new URL on the next poll.
    Get-Process -Name 'MiOS-Wallpaper' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
