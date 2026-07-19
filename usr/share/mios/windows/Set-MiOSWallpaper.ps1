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

# The wallpaper's colours ARE the mios.toml [colors] SSOT — the FULL 16-colour systemwide set
# (ansi_0..ansi_15), passed to the page as a0..a15, plus bg/fg which anchor the dark/light grade.
# $AnsiSrc maps each a{i} -> the [colors] key that feeds it; $Tokens holds the defaults, which
# mirror mios.toml so a missing key is a no-op, never a surprise.
$AnsiSrc = [ordered]@{
    a0  = 'ansi_0_black';         a1  = 'ansi_1_red';            a2  = 'ansi_2_green';          a3  = 'ansi_3_yellow'
    a4  = 'ansi_4_blue';          a5  = 'ansi_5_magenta';        a6  = 'ansi_6_cyan';           a7  = 'ansi_7_white'
    a8  = 'ansi_8_bright_black';  a9  = 'ansi_9_bright_red';     a10 = 'ansi_10_bright_green';  a11 = 'ansi_11_bright_yellow'
    a12 = 'ansi_12_bright_blue';  a13 = 'ansi_13_bright_magenta';a14 = 'ansi_14_bright_cyan';   a15 = 'ansi_15_bright_white'
    bg  = 'bg';                   fg  = 'fg'
}
$Tokens = [ordered]@{
    a0  = '#282262'; a1  = '#DC271B'; a2  = '#3E7765'; a3  = '#F35C15'
    a4  = '#1A407F'; a5  = '#734F39'; a6  = '#B7C9D7'; a7  = '#E7DFD3'
    a8  = '#948E8E'; a9  = '#FF6B5C'; a10 = '#5FAA8E'; a11 = '#FF8540'
    a12 = '#3D6BA8'; a13 = '#9D7660'; a14 = '#E0E0E0'; a15 = '#FFFFFF'
    bg  = '#282262'; fg  = '#E7DFD3'
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
    foreach ($k in $Tokens.Keys) { $src = $AnsiSrc[$k]; if ($c.ContainsKey($src) -and $c[$src]) { $resolved[$k] = $c[$src] } }
}

# Mode: 'auto' (default) omits the mode param so the page follows the host light/dark theme LIVE
# via prefers-color-scheme (WebView2/Chromium tracks the OS theme; the page re-grades on change --
# same media query works on Linux). Only an explicit -Mode dark|light pins it. This is the real
# cross-platform theme sync: no reload needed when the user toggles Windows (or a Linux DE) theme.
$modeQuery = if ($Mode -eq 'dark' -or $Mode -eq 'light') { "&mode=$Mode" } else { '' }

# Build the query string (hex WITHOUT '#', matching the page's URLSearchParams parser).
$pairs = foreach ($k in $Tokens.Keys) { "$k=" + ($resolved[$k] -replace '^#','') }
$query = ($pairs -join '&') + $modeQuery
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
