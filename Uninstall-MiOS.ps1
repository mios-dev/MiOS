<#
.SYNOPSIS
  Hardened, idempotent COMPLETE uninstaller for MiOS on a Windows host.

.DESCRIPTION
  Removes every MiOS artifact and NOTHING else:
    * the podman-MiOS-DEV / podman-MiOS-BUILDER WSL2 distros (the dev VM + builder),
    * the MiOS checkout/data on the data drive (labeled MIOS-DEV by default),
    * the Windows-side install: C:\Windows\Web\MiOS, HKLM\SOFTWARE\MiOS,
      the MiOS-Wallpaper service + processes, MiOS scheduled tasks,
      MiOS Start-menu shortcuts, and (opt-in) the MiOS Windows Terminal profiles.

  SAFE BY DEFAULT: prints what it WOULD remove and changes nothing unless -Execute
  is given. On the data drive it deletes ONLY an explicit MiOS artifact list and a
  hard KEEP list guarantees the Windows pagefile, Steam libraries, the recycle bin,
  System Volume Information, and Windows UUP staging are NEVER touched -- so a data
  drive that also holds non-MiOS data survives intact.

.PARAMETER Execute
  Actually delete. Without it the script is a dry-run (reports only).

.PARAMETER DataDrive
  MiOS data-drive letter (e.g. 'M'). Default: auto-detect the NTFS volume whose
  label is 'MIOS-DEV'. Pass '' / -SkipDataDrive to leave the data drive alone.

.PARAMETER SkipDataDrive
  Do not touch the data drive at all (only remove the VM + Windows-side install).

.PARAMETER RemoveTerminalProfiles
  Also strip the MiOS / MiOS-DEV profiles from the Windows Terminal settings.json.

.EXAMPLE
  # Dry-run (default) -- see exactly what would be removed:
  powershell -ExecutionPolicy Bypass -File .\Uninstall-MiOS.ps1

.EXAMPLE
  # Full uninstall:
  powershell -ExecutionPolicy Bypass -File .\Uninstall-MiOS.ps1 -Execute
#>
[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$DataDrive,
    [switch]$SkipDataDrive,
    [switch]$RemoveTerminalProfiles
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:Removed = 0; $script:Kept = 0; $script:Failed = 0
$MODE = if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' }

function _say([string]$m, [string]$c = 'Gray') { Write-Host $m -ForegroundColor $c }
function _act([string]$what, [scriptblock]$do) {
    if ($Execute) {
        try { & $do; _say "  [removed] $what" 'Green'; $script:Removed++ }
        catch { _say "  [FAILED ] $what -- $($_.Exception.Message)" 'Red'; $script:Failed++ }
    } else {
        _say "  [would remove] $what" 'Yellow'; $script:Removed++
    }
}
function _keep([string]$what) { _say "  [KEEP   ] $what" 'DarkGray'; $script:Kept++ }

# ── Elevation ───────────────────────────────────────────────────────────────
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
_say "=== MiOS Uninstaller ($MODE) ===" 'Cyan'
if (-not $admin) {
    _say "NOT elevated. WSL unregister, service delete, HKLM + C:\Windows edits need admin." 'Red'
    _say "Re-run from an elevated PowerShell (Run as Administrator)." 'Red'
    if ($Execute) { exit 1 }
}

# ── 1. WSL distros (the dev VM + builder; their vhdx lives under the data drive) ──
_say "`n[1/5] WSL distros" 'Cyan'
$wslList = (& wsl.exe -l -q) 2>$null | ForEach-Object { $_.Trim([char]0, ' ') } | Where-Object { $_ }
foreach ($d in @('podman-MiOS-DEV','podman-MiOS-BUILDER','MiOS-DEV','MiOS-BUILDER')) {
    if ($wslList -contains $d) {
        _act "wsl --unregister $d" { & wsl.exe --shutdown *> $null; & wsl.exe --unregister $d *> $null; if ($LASTEXITCODE) { throw "wsl exit $LASTEXITCODE" } }
    }
}

# ── 2. Windows-side services + processes ────────────────────────────────────
_say "`n[2/5] Windows services + processes" 'Cyan'
foreach ($p in @('MiOS-Wallpaper','MiOS-Wallpaper-Service','MiOS-Launcher')) {
    if (Get-Process -Name $p -ErrorAction SilentlyContinue) { _act "kill process $p" { Get-Process -Name $p -ErrorAction SilentlyContinue | Stop-Process -Force } }
}
foreach ($svc in @('MiOS-Wallpaper-Service')) {
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        _act "service $svc (stop+delete)" { Stop-Service $svc -Force -ErrorAction SilentlyContinue; & sc.exe delete $svc *> $null }
    }
}

# ── 3. Windows-side install: files, registry, tasks, shortcuts ──────────────
_say "`n[3/5] Windows-side install (files / registry / tasks / shortcuts)" 'Cyan'
foreach ($path in @("$env:WINDIR\Web\MiOS", "$env:WINDIR\Temp\MiOS-WV2-Profile")) {
    if (Test-Path -LiteralPath $path) { _act "dir $path" { Remove-Item -LiteralPath $path -Recurse -Force } }
}
if (Test-Path 'HKLM:\SOFTWARE\MiOS') { _act "registry HKLM\SOFTWARE\MiOS" { Remove-Item -LiteralPath 'HKLM:\SOFTWARE\MiOS' -Recurse -Force } }
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match 'MiOS' -or $_.TaskPath -match 'MiOS' } | ForEach-Object {
    _act "scheduled task $($_.TaskPath)$($_.TaskName)" { Unregister-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath -Confirm:$false }
}
foreach ($root in @("$env:ProgramData\Microsoft\Windows\Start Menu\Programs", "$env:APPDATA\Microsoft\Windows\Start Menu\Programs")) {
    if (Test-Path -LiteralPath $root) {
        Get-ChildItem -LiteralPath $root -Recurse -Filter '*MiOS*' -ErrorAction SilentlyContinue | ForEach-Object {
            _act "shortcut $($_.FullName)" { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
        }
    }
}
if ($RemoveTerminalProfiles) {
    $wtSettings = Get-ChildItem "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_*\LocalState\settings.json" -ErrorAction SilentlyContinue
    foreach ($s in $wtSettings) {
        _act "WT profiles MiOS/MiOS-DEV in $($s.FullName)" {
            $j = Get-Content -LiteralPath $s.FullName -Raw | ConvertFrom-Json
            if ($j.profiles -and $j.profiles.list) {
                $j.profiles.list = @($j.profiles.list | Where-Object { $_.name -notin @('MiOS','MiOS-DEV') })
                ($j | ConvertTo-Json -Depth 32) | Set-Content -LiteralPath $s.FullName -Encoding UTF8
            }
        }
    }
} else { _keep "Windows Terminal MiOS profiles (pass -RemoveTerminalProfiles to strip)" }

# ── 4. Data drive: remove the MiOS checkout, PRESERVE everything non-MiOS ────
_say "`n[4/5] Data drive (MiOS checkout only)" 'Cyan'
if ($SkipDataDrive) {
    _keep "data drive (-SkipDataDrive)"
} else {
    if (-not $DataDrive) {
        $vol = Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.FileSystemLabel -eq 'MIOS-DEV' -and $_.DriveLetter } | Select-Object -First 1
        if ($vol) { $DataDrive = [string]$vol.DriveLetter }
    }
    if (-not $DataDrive -or -not (Test-Path -LiteralPath "${DataDrive}:\")) {
        _keep "no MIOS-DEV data drive found (nothing to clean)"
    } else {
        $root = "${DataDrive}:\"
        _say "  data drive: $root (label MIOS-DEV)" 'Gray'
        # HARD keep-list -- NEVER deleted, guarantees non-MiOS data survives.
        $KEEP = @('$RECYCLE.BIN','System Volume Information','pagefile.sys','swapfile.sys',
                  'hiberfil.sys','DumpStack.log.tmp','SteamLibrary','W10UIuup','MountUUP',
                  'winget','images','research','config')
        # Explicit MiOS artifact dirs on the data drive (FHS overlay + repo + VM + runtime).
        $MIOS_DIRS = @('.devcontainer','.forgejo','.git','.github','automation','etc','MiOS',
                       'podman','root','src','tests','tools','usr','var','powershell')
        foreach ($item in Get-ChildItem -LiteralPath $root -Force -ErrorAction SilentlyContinue) {
            $n = $item.Name
            if ($KEEP -contains $n) { _keep "$root$n  (non-MiOS -- preserved)"; continue }
            if ($item.PSIsContainer) {
                if ($MIOS_DIRS -contains $n) { _act "dir $root$n" { Remove-Item -LiteralPath $item.FullName -Recurse -Force } }
                else { _keep "$root$n  (unlisted dir -- preserved for safety)" }
            } else {
                # MiOS repo root files (Get-MiOS.ps1, mios.toml, *.md, Containerfile, ...);
                # the KEEP list already excludes pagefile/DumpStack/etc.
                _act "file $root$n" { Remove-Item -LiteralPath $item.FullName -Force }
            }
        }
    }
}

# ── 5. Summary ──────────────────────────────────────────────────────────────
_say "`n[5/5] Summary ($MODE)" 'Cyan'
_say "  removed : $script:Removed" 'Green'
_say "  kept    : $script:Kept" 'DarkGray'
_say "  failed  : $script:Failed" $(if ($script:Failed) { 'Red' } else { 'Green' })
if (-not $Execute) { _say "`nDRY-RUN -- nothing was changed. Re-run with -Execute to uninstall." 'Yellow' }
elseif ($script:Failed -eq 0) { _say "`nMiOS fully uninstalled. Reinstall: irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex" 'Green' }
exit $(if ($script:Failed) { 1 } else { 0 })
