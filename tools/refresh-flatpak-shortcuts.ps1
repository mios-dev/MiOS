# AI-hint: Powershell script that manually generates Windows Start Menu .lnk shortcuts for Flatpak applications in the MiOS-DEV distro to bypass WSLg's failure to aut...
# AI-doc: usr/share/doc/mios/manual/tools.md

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

$modulePath = Join-Path $PSScriptRoot '..\usr\libexec\mios\MiOSShortcutUtils.psm1'
if (Test-Path $modulePath) { Import-Module $modulePath -ErrorAction SilentlyContinue }

    New-MiosWslShortcut -LnkPath $lnkPath -Distro $Distro -ExecCmd $args_ -Description "$name ($Distro)"
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
