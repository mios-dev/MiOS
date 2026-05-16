# tools/refresh-flatpak-shortcuts.ps1
#
# Windows-side helper that creates Start Menu .lnk entries for every
# installed flatpak in the MiOS-DEV distro that WSLg's auto-discovery
# silently dropped. Run after `mios-flatpak-install` (or any time the
# flatpak set changes) and the new apps appear under Start ->
# "MiOS Apps" within seconds.
#
# Background: WSLg's wslservice scans /usr/share/applications/ inside
# the distro and writes .lnk files into
# %APPDATA%\Microsoft\Windows\Start Menu\Programs\<distro>\ -- but
# its icon-conversion step silently fails for many flatpak .desktop
# files (operator-confirmed 2026-05-15: ChromeDev, Codium, gedit,
# ExtensionManager, Flatseal all skipped despite valid Categories,
# Type=Application, present .svg icons under
# /var/lib/flatpak/exports/share/icons). When the icon-conversion
# step fails, WSLg drops the entire entry instead of using a
# fallback icon. Net: missing apps in the Start Menu.
#
# Fix: this script bypasses WSLg's batch by:
#   1. enumerating flatpak .desktop files inside the distro
#   2. parsing Name + Exec from each
#   3. writing one .lnk per flatpak to a SEPARATE folder (
#      "MiOS Apps") so WSLg's next scan won't clobber what we wrote
#   4. using generic imageres.dll icons -- the operator can right-
#      click + "Change Icon" if they want a custom one
#
# Idempotent: skips .lnk files that already exist + are current.
# Removes stale .lnk files whose flatpak was uninstalled.
#
# Usage:
#   pwsh -File tools/refresh-flatpak-shortcuts.ps1            # default distro
#   pwsh -File tools/refresh-flatpak-shortcuts.ps1 -Distro X  # other distro
#
# Operators can wire it into mios-flatpak-install via a Scheduled
# Task or just re-run when needed.

[CmdletBinding()]
param(
    [string]$Distro = "podman-MiOS-DEV",
    [string]$FolderName = "MiOS Apps"
)

$ErrorActionPreference = "Stop"

$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\$FolderName"
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

$wslg = "C:\Program Files\WSL\wslg.exe"
if (-not (Test-Path $wslg)) {
    throw "wslg.exe not found at $wslg -- is WSL installed?"
}

# Enumerate flatpak .desktop files inside the distro
$desktopPaths = wsl.exe -d $Distro --user root -- ls /var/lib/flatpak/exports/share/applications/*.desktop 2>$null
if (-not $desktopPaths) {
    Write-Output "no flatpaks installed in $Distro -- nothing to do"
    exit 0
}

$wsh = New-Object -ComObject WScript.Shell
$created = 0; $skipped = 0; $stale = 0

# Build the current set of expected .lnk names so we can detect stale ones later
$expected = @{}

foreach ($path in $desktopPaths) {
    $path = $path.Trim()
    if (-not $path) { continue }
    # -url-handler companions are confusing extras -- skip
    if ($path -match "-url-handler\.desktop$") { continue }

    # Parse Name + Exec from the .desktop file. Multiple Name[lang]= lines
    # exist; take the non-localised Name= (no bracket).
    $content = wsl.exe -d $Distro --user root -- cat $path 2>$null
    $name = ($content | Select-String -Pattern '^Name=' | Select-Object -First 1) -replace '^Name=', ''
    $exec = ($content | Select-String -Pattern '^Exec=' | Select-Object -First 1) -replace '^Exec=', ''
    if (-not $name -or -not $exec) { continue }

    # Sanitise the name for use as a Windows filename
    $safeName = $name -replace '[<>:"/\\|?*]', '_'
    $lnkName = "$safeName.lnk"
    $expected[$lnkName] = $true
    $lnkPath = Join-Path $startMenu $lnkName

    # Translate Exec percent-codes -> WSLg @@u idiom that wslg.exe expects
    $args_ = $exec `
        -replace '@@u %U @@', '@@u' `
        -replace '@@ %F @@', '@@u' `
        -replace ' %[UFufNn]', ''

    if (Test-Path $lnkPath) {
        # Check if existing .lnk matches the current Args; rewrite if drifted
        $existing = $wsh.CreateShortcut($lnkPath)
        $expectedArgs = "-d $Distro --cd `"~`" -- $args_"
        if ($existing.Arguments -eq $expectedArgs) {
            $skipped++
            continue
        }
    }

    $lnk = $wsh.CreateShortcut($lnkPath)
    $lnk.TargetPath = $wslg
    $lnk.Arguments = "-d $Distro --cd `"~`" -- $args_"
    $lnk.WorkingDirectory = "C:\WINDOWS\system32"
    $lnk.IconLocation = "$env:windir\System32\imageres.dll,150"
    $lnk.Description = "$name ($Distro)"
    $lnk.Save()
    $created++
    Write-Output "  created: $lnkName"
}

# Stale-detection: remove .lnk files in MiOS Apps whose flatpak no longer exists
Get-ChildItem $startMenu -Filter "*.lnk" | ForEach-Object {
    if (-not $expected.ContainsKey($_.Name)) {
        # Only remove if it was clearly one we wrote (Description matches our pattern)
        $existing = $wsh.CreateShortcut($_.FullName)
        if ($existing.Description -match "\($Distro\)$") {
            Remove-Item $_.FullName -Force
            $stale++
            Write-Output "  removed stale: $($_.Name)"
        }
    }
}

Write-Output ""
Write-Output "refresh-flatpak-shortcuts: created=$created skipped=$skipped stale-removed=$stale"
Write-Output "folder: $startMenu"
