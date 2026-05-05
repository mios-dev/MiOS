<#
.NOTES
    CANONICAL ENTRY POINT NOTICE (v0.2.4+):
    The user-facing end-to-end pipeline now lives at
    `./mios-pipeline.ps1`. install.ps1 is invoked BY that pipeline as
    the worker for Phase 9 (Deploy) and Phase 10 (Boot). Operator
    automation should call mios-pipeline.ps1 instead of install.ps1
    directly; calling install.ps1 still works but skips Phases 1-8.

.SYNOPSIS  'MiOS' v0.2.4 -- Unified Windows Installer
.DESCRIPTION
    Entry: irm https://raw.githubusercontent.com/MiOS-DEV/mios/main/install.ps1 | iex
    Normally downloaded + launched by bootstrap.ps1 after collecting credentials.

    Platform entrypoints are thin bootstraps -- all build logic runs against the
    shared codebase (Containerfile + automation/) via `podman build`.

    Expected env vars from bootstrap.ps1 (or set manually):
        GHCR_TOKEN          GitHub PAT for image pull / push
        MIOS_USER           Admin username
        MIOS_PASSWORD       Admin password (plaintext -- hashed before injection)
        MIOS_HOSTNAME       Static hostname (default: mios-XXXXX)
        MIOS_DIR            Repo clone target directory
        MIOS_AUTOINSTALL    Set to "1" for non-interactive defaults
#>
#Requires -Version 7.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Acknowledgment banner (dot-sourced; respects MIOS_AGREEMENT_BANNER and
# MIOS_REQUIRE_AGREEMENT_ACK).
$_bannerPath = Join-Path -Path $PSScriptRoot -ChildPath 'automation/lib/agreements-banner.ps1'
if ($_bannerPath -and (Test-Path $_bannerPath)) {
    . $_bannerPath; Invoke-MiOSAgreementBanner -Entry 'install.ps1'
}
Remove-Variable _bannerPath -ErrorAction SilentlyContinue

# ─── constants ────────────────────────────────────────────────────────────────
$Version        = (Get-Content (Join-Path $PSScriptRoot "VERSION") -EA SilentlyContinue)?.Trim() ?? "0.2.4"
$RepoUrl        = "https://github.com/MiOS-DEV/MiOS.git"
$BibImage       = if ($env:MIOS_BIB_IMAGE) { $env:MIOS_BIB_IMAGE } else { "quay.io/centos-bootc/bootc-image-builder:latest" }
$BuilderMachine = "mios-dev"   # canonical lowercase form (was "mios-builder" pre-v0.2.3)
$ImageName      = "mios"
$ImageTag       = "latest"
$LocalImage     = "localhost/${ImageName}:${ImageTag}"

$MiosDocsDir      = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "MiOS"
$MiosDeployDir    = Join-Path $MiosDocsDir "deployments"
$MiosImagesDir    = Join-Path $MiosDocsDir "images"
$MiosManifestsDir = Join-Path $MiosDocsDir "manifests"
$RepoDir          = if ($env:MIOS_DIR) { $env:MIOS_DIR } else { Join-Path $env:LOCALAPPDATA "'MiOS'\repo" }

$TargetVhdx = Join-Path $MiosDeployDir "mios-hyperv.vhdx"
$TargetWsl  = Join-Path $MiosDeployDir "mios-wsl.tar"
$TargetIso  = Join-Path $MiosImagesDir "mios-installer.iso"

# Shared helper: writes /etc/mios/install.env into a freshly-imported WSL2
# distro so wsl-firstboot.service picks up the operator-supplied identity
# instead of falling back to the literal default password "mios".
. (Join-Path $PSScriptRoot "tools/lib/install-env.ps1")

# ─── masking ──────────────────────────────────────────────────────────────────
$script:MaskList = [System.Collections.Generic.List[string]]::new()

function Register-Secret {
    param([string]$S)
    if (-not [string]::IsNullOrWhiteSpace($S) -and $S.Length -ge 4 -and -not $script:MaskList.Contains($S)) {
        $script:MaskList.Add($S)
    }
}

function Format-Masked {
    param([string]$S)
    $out = $S
    foreach ($m in $script:MaskList) {
        $out = $out -ireplace [regex]::Escape($m), "********"
    }
    return $out
}

@("GHCR_TOKEN","GH_TOKEN","GITHUB_TOKEN","MIOS_PASSWORD","MIOS_GHCR_TOKEN") | ForEach-Object {
    # PowerShell parses $env:$_ as a scope-qualified var ref and rejects it
    # at parse time. Use [Environment]::GetEnvironmentVariable instead.
    $val = [Environment]::GetEnvironmentVariable($_)
    if ($val) { Register-Secret $val }
}

# ─── dashboard state ──────────────────────────────────────────────────────────
$script:DashRow         = 0
$script:DashH           = 0
$script:DashReady       = $false
# Resolved on first Show-Dashboard call: $true if [Console] has a real
# console with usable cursor positioning, $false if we're running under
# captured stdout (background pipeline invocation). $null means "probe
# hasn't run yet".
$script:DashInteractive = $null
$script:BuildStart = [DateTime]::Now
$script:ErrCount   = 0
$script:WarnCount  = 0
$script:Op         = "Initializing..."
$script:LogFile    = ""

# Phase definitions -- EstSteps drives the progress denominator
$script:Phases = @(
    [pscustomobject]@{Id=0;  Name="Hardware + Prerequisites";  State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=1;  Name="Detecting environment";     State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=2;  Name="Directories and repos";     State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=3;  Name="MiOS-DEV distro";           State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=4;  Name="WSL2 configuration";        State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=5;  Name="Verifying build context";   State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=6;  Name="Identity";                  State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=7;  Name="Writing identity";          State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=8;  Name="App registration";          State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=9;  Name="Building OCI image";        State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=48; EstSteps=48}
    [pscustomobject]@{Id=10; Name="Exporting WSL2 image";      State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=2}
    [pscustomobject]@{Id=11; Name="Registering 'MiOS' WSL2";     State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=2}
    [pscustomobject]@{Id=12; Name="Building disk images";      State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=4}
    [pscustomobject]@{Id=13; Name="Deploying Hyper-V VM";      State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
)
$TotalEstSteps = ($script:Phases | Measure-Object -Property EstSteps -Sum).Sum  # ≈ 65

# ─── dashboard rendering ──────────────────────────────────────────────────────
$DW = 78  # inner content width

function _dpad { param([string]$S,[int]$W) if($S.Length -ge $W){$S.Substring(0,$W)}else{$S.PadRight($W)} }
function _dsep { param([char]$C='-') '+' + [string]::new($C,$DW) + '+' }

function Show-Dashboard {
    param([switch]$FullRedraw)

    $elapsed = [DateTime]::Now - $script:BuildStart
    $tStr    = "{0:D2}:{1:D2}" -f [int]$elapsed.TotalHours, $elapsed.Minutes

    # Progress calculation
    $stepsCompleted = 0
    $stepsRunning   = 0
    foreach ($ph in $script:Phases) {
        if ($ph.State -eq "ok" -or $ph.State -eq "warn" -or $ph.State -eq "fail") {
            $stepsCompleted += $ph.EstSteps
        } elseif ($ph.State -eq "running") {
            $inner = if ($ph.InnerTotal -gt 0) { [int]($ph.InnerStep * $ph.EstSteps / $ph.InnerTotal) } else { 0 }
            $stepsRunning = $inner
        }
    }
    $stepsDone  = $stepsCompleted + $stepsRunning
    $pct        = [Math]::Min(99, [int]($stepsDone * 100 / [Math]::Max(1, $TotalEstSteps)))
    $barFill    = [int]($pct * 58 / 100)
    $bar        = '[' + [string]::new('=',[Math]::Max(0,$barFill-1)) + '>' + [string]::new(' ',58-$barFill) + ']'

    # Current phase info
    $curPh = $script:Phases | Where-Object { $_.State -eq "running" } | Select-Object -Last 1
    $phStr = if ($curPh) {
        $inner = if ($curPh.InnerTotal -gt 0) { "  ($($curPh.InnerStep)/$($curPh.InnerTotal) steps)" } else { "" }
        "[$($curPh.Id)/13] $($curPh.Name)$inner"
    } else { "Initializing" }

    $op     = _dpad (Format-Masked $script:Op) ($DW - 7)
    $status = if ($pct -ge 100) { "DONE" } else { "RUNNING" }

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add($(_dsep '-'))
    $lines.Add("| $(_dpad "  'MiOS' v$Version  --  Build Dashboard" ($DW-9)) [ $tStr ] |")
    $lines.Add($(_dsep '-'))
    $lines.Add("| Ph : $(_dpad $phStr ($DW-7))|")
    $lines.Add("| Op : $op|")                                                     # offset 4
    $lines.Add("| $(_dpad "Errors:$($script:ErrCount)  Warns:$($script:WarnCount)  Status:$status" ($DW-2))|")
    $lines.Add($(_dsep '-'))
    $lines.Add("| $bar  $("{0,3}" -f $pct)%  $stepsDone/$TotalEstSteps |")
    $lines.Add($(_dsep '-'))
    $lines.Add("| $(_dpad "  #  State  Phase Name" ($DW-10)) Time  |")
    $lines.Add("| $(_dpad (" ---  -----  " + [string]::new('-',44)) ($DW-2))|")

    foreach ($ph in $script:Phases) {
        $stateStr = switch ($ph.State) {
            "ok"      { "[OK] " }
            "running" { "[>>] " }
            "fail"    { "[!!] " }
            "warn"    { "[??] " }
            default   { "[  ] " }
        }
        $tCell = if ($ph.ElapsedS -gt 0) { "{0:D2}:{1:D2}" -f [int]($ph.ElapsedS/60), ($ph.ElapsedS%60) } else { "     " }
        $lines.Add(("| {0,3}  {1}  {2}  {3} |" -f $ph.Id, $stateStr, (_dpad $ph.Name 48), $tCell))
    }

    $lines.Add($(_dsep '-'))
    $logName = if ($script:LogFile) { Split-Path $script:LogFile -Leaf } else { "starting..." }
    $lines.Add("| Log: $(_dpad $logName ($DW-7))|")
    $lines.Add($(_dsep '-'))

    $script:DashH = $lines.Count

    # Probe once whether [Console] is a real console with a usable cursor.
    # Background pipeline invocations (mios-pipeline.ps1 -> install.ps1
    # via Start-Process redirected stdout) have no console handle and
    # CursorTop throws "The handle is invalid." Detect that up front and
    # fall back to plain line writes -- the dashboard becomes a snapshot
    # log instead of an in-place TUI, which is the right shape for
    # captured output anyway.
    if ($null -eq $script:DashInteractive) {
        try {
            $null = [Console]::CursorTop
            $script:DashInteractive = $true
        } catch {
            $script:DashInteractive = $false
        }
    }

    if (-not $script:DashInteractive) {
        # Non-interactive: emit on first call only (full state) then
        # just the changed Op line via Set-Op. Avoids spamming 28 lines
        # for every progress tick.
        if (-not $script:DashReady) {
            foreach ($l in $lines) { Write-Host $l }
            $script:DashReady = $true
        }
        return
    }

    if (-not $script:DashReady) {
        # First render -- write fresh, record position
        $script:DashRow = [Console]::CursorTop
        foreach ($l in $lines) { [Console]::WriteLine($l) }
        $script:DashReady = $true
    } else {
        # In-place redraw -- only rewrite if cursor is still on screen
        try {
            $savedTop = [Console]::CursorTop
            $savedLeft = [Console]::CursorLeft
            [Console]::SetCursorPosition(0, $script:DashRow)
            foreach ($l in $lines) {
                [Console]::Write("`r" + $l.PadRight([Console]::WindowWidth - 1))
                [Console]::WriteLine()
            }
            # Move cursor to below dashboard for any subsequent Write-Host output
            [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH)
        } catch { }
    }
}

# Fast partial update -- just the Op: line, avoids redrawing 28 lines on every build output line
function Set-Op {
    param([string]$NewOp)
    $masked = Format-Masked $NewOp
    if ($masked.Length -gt ($DW - 8)) { $masked = $masked.Substring(0, $DW - 11) + '...' }
    $script:Op = $masked
    try {
        [Console]::SetCursorPosition(0, $script:DashRow + 4)
        [Console]::Write("| Op : $($masked.PadRight($DW - 7))|".PadRight([Console]::WindowWidth - 1))
        [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH)
    } catch { }
}

# ─── phase management ─────────────────────────────────────────────────────────
function Start-Phase {
    param([int]$Id, [string]$InitOp = "")
    $ph = $script:Phases[$Id]
    $ph.State   = "running"
    $ph.StartT  = [DateTime]::Now
    if ($InitOp) { $script:Op = $InitOp }
    Show-Dashboard -FullRedraw
    Write-Log "=== Phase ${Id}: $($ph.Name) ===" -Color Cyan
}

function Finish-Phase {
    param([int]$Id, [string]$State = "ok")
    $ph = $script:Phases[$Id]
    $ph.State    = $State
    $ph.ElapsedS = [int]([DateTime]::Now - $ph.StartT).TotalSeconds
    Show-Dashboard -FullRedraw
}

# ─── logging ──────────────────────────────────────────────────────────────────
function Write-Log {
    param([string]$Msg, [string]$Color = "Gray")
    $ts      = Get-Date -Format "HH:mm:ss"
    $masked  = Format-Masked $Msg
    # Write-Host goes through transcript; console cursor is already below dashboard
    Write-Host "[$ts] $masked" -ForegroundColor $Color
}

function Write-LogOK   { param([string]$M) $script:BuildAudit += "[OK] $M"; Write-Log "  [OK] $M" -Color Green }
function Write-LogWarn { param([string]$M) $script:WarnCount++; Write-Log " [WARN] $M" -Color Yellow }
function Write-LogFail { param([string]$M) $script:ErrCount++;  Write-Log " [FAIL] $M" -Color Red }
function Write-LogFatal {
    param([string]$M)
    $script:ErrCount++
    Write-Log " [FATAL] $M" -Color Red
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

$script:BuildAudit = [System.Collections.Generic.List[string]]::new()

# ─── credential helpers ───────────────────────────────────────────────────────
function Read-Masked {
    param([string]$Prompt, [string]$Default = "")
    # Move cursor below dashboard before prompting
    try { [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH + 1) } catch {}
    Write-Host "  $Prompt " -NoNewline -ForegroundColor DarkCyan
    if ($Default) { Write-Host "[$(if($Default -eq $env:GHCR_TOKEN -or $Default.Length -gt 8){'********'}else{$Default})] " -NoNewline -ForegroundColor DarkGray }
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        $val = Read-Host -MaskInput
    } else {
        $sec  = Read-Host -AsSecureString
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        try   { $val = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
        finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
    if ([string]::IsNullOrWhiteSpace($val) -and $Default) { return $Default }
    if ($val) { Register-Secret $val }
    return $val
}

function Read-Plain {
    param([string]$Prompt, [string]$Default = "")
    try { [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH + 1) } catch {}
    Write-Host "  $Prompt " -NoNewline -ForegroundColor DarkCyan
    if ($Default) { Write-Host "[$Default] " -NoNewline -ForegroundColor DarkGray }
    $val = Read-Host
    if ([string]::IsNullOrWhiteSpace($val)) { return $Default }
    return $val
}

function Get-SHA512Hash {
    param([string]$PlainText, [string]$HImg)
    $salt = -join ((65..90)+(97..122)+(48..57) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    $h = $null
    if ($HImg) {
        $h = (& podman run --rm $HImg openssl passwd -6 -salt $salt $PlainText 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and $h -match '^\$6\$') { return $h }
    }
    $h = (& podman run --rm docker.io/library/alpine:latest sh -c "apk add -q openssl >/dev/null 2>&1 && openssl passwd -6 -salt '$salt' '$PlainText'" 2>$null).Trim()
    if ($h -match '^\$6\$') { return $h }
    # python fallback
    $h = (& podman run --rm docker.io/library/python:3-slim python3 -c "import crypt; print(crypt.crypt('$PlainText', crypt.mksalt(crypt.METHOD_SHA512)))" 2>$null).Trim()
    return $h
}

function Get-FileSize {
    param([string]$P)
    if (-not (Test-Path $P)) { return "N/A" }
    $s = (Get-Item $P).Length
    if ($s -gt 1GB) { "$([Math]::Round($s/1GB,2)) GB" } else { "$([Math]::Round($s/1MB,1)) MB" }
}

# ─── BIB streaming runner ─────────────────────────────────────────────────────
function Invoke-BIBRun {
    param([string[]]$BIBArgs, [string]$Label)
    $n = 0
    Set-Op "Starting $Label..."
    & podman @BIBArgs 2>&1 | ForEach-Object {
        $line = $_
        Write-Log (Format-Masked $line) -Color DarkGray
        $n++
        $stripped = ($line -replace '^\s*#\d+\s+(?:[\d.]+\s+)?','').TrimStart()
        $opCandidate = if ($stripped -match 'org\.osbuild\.\S+') { $Matches[0] }
        elseif ($stripped -match '^(Assembling|Building|Extracting|Installing|Packaging|Stage|Writing)\b') {
            ($stripped -replace '\s+',' ').Trim()
        } elseif (-not [string]::IsNullOrWhiteSpace($stripped)) {
            ($stripped -replace '\s+',' ').Trim()
        }
        if ($opCandidate) {
            if ($opCandidate.Length -gt 72) { $opCandidate = $opCandidate.Substring(0,69) + '...' }
            Set-Op $opCandidate
        }
    }
    return $LASTEXITCODE
}

# ─── elevation ────────────────────────────────────────────────────────────────
# Trust mios-pipeline.ps1's centralized elevation; only self-elevate
# when invoked standalone (the legacy operator path). Skipping when
# MIOS_PIPELINE_ELEVATED=1 prevents the previous failure mode where the
# pipeline's elevated session would re-fork and orphan another UAC
# window on this script's entry.
if (-not $env:MIOS_PIPELINE_ELEVATED) {
    if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
             ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "  Relaunching as Administrator..." -ForegroundColor Cyan
        Start-Process pwsh.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`"" -Verb RunAs -Wait
        return
    }
}

# ─── static header (printed once, scrolls away) ───────────────────────────────
[Console]::WriteLine("")
[Console]::WriteLine('+' + [string]::new('=',78) + '+')
[Console]::WriteLine("| $(_dpad "'MiOS' v$Version  --  Unified Windows Installer" 76) |")
[Console]::WriteLine("| $(_dpad "Immutable Fedora AI Workstation" 76) |")
[Console]::WriteLine("| $(_dpad "WSL2 + Podman  |  Offline Build Pipeline" 76) |")
[Console]::WriteLine('+' + [string]::new('=',78) + '+')
[Console]::WriteLine("")

# ─── log + transcript ─────────────────────────────────────────────────────────
foreach ($d in @($MiosDocsDir,$MiosDeployDir,$MiosImagesDir,$MiosManifestsDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
$script:LogFile = if ($env:MIOS_UNIFIED_LOG) { $env:MIOS_UNIFIED_LOG } else {
    Join-Path $MiosDocsDir "mios-install-$([DateTime]::Now.ToString('yyyyMMdd-HHmmss')).log"
}
[Environment]::SetEnvironmentVariable("MIOS_UNIFIED_LOG", $script:LogFile)
try { Start-Transcript -Path $script:LogFile -Append -Force | Out-Null } catch {}

# Initial dashboard render
Show-Dashboard

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 0 -- Hardware + Prerequisites
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 0 "Checking Windows version..."
$os = Get-CimInstance Win32_OperatingSystem
if ($os.Caption -notmatch "Pro|Enterprise|Education|Server") {
    Write-LogWarn "Windows edition may not support Hyper-V: $($os.Caption)"
} else { Write-LogOK "OS: $($os.Caption)" }

foreach ($feat in @("Microsoft-Hyper-V","VirtualMachinePlatform","Microsoft-Windows-Subsystem-Linux")) {
    $f = Get-WindowsOptionalFeature -Online -FeatureName $feat -EA SilentlyContinue
    if ($f -and $f.State -eq "Enabled") { Write-LogOK "$feat enabled" }
    else { Write-LogWarn "$feat not enabled -- some targets may be unavailable" }
}
try {
    $null = & podman --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
    Write-LogOK "Podman found"
} catch { Write-LogFatal "Podman not found. Install Podman Desktop: https://podman-desktop.io" }
Finish-Phase 0

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 1 -- Detecting environment
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 1 "Detecting hardware..."
$cpu = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
$ram = [Math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$disk = [Math]::Floor((Get-PSDrive C).Free / 1GB)
Write-LogOK "CPU: $cpu cores  RAM: ${ram}GB  Disk free: ${disk}GB"
if ($disk -lt 80) { Write-LogWarn "Low disk space (<80 GB). Build may fail." }
Finish-Phase 1

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 2 -- Directories and repos
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 2 "Preparing directories..."
foreach ($d in @($MiosDocsDir,$MiosDeployDir,$MiosImagesDir,$MiosManifestsDir,(Split-Path $RepoDir -Parent))) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

Set-Op "Cloning / updating 'MiOS' repo..."
if (Test-Path (Join-Path $RepoDir ".git")) {
    Write-Log "Updating existing repo at $RepoDir..."
    Push-Location $RepoDir
    $null = & git fetch origin 2>&1
    $null = & git pull --ff-only origin main 2>&1
    Pop-Location
    Write-LogOK "Repo updated: $RepoDir"
} else {
    Write-Log "Cloning $RepoUrl → $RepoDir..."
    if ($env:GHCR_TOKEN) {
        $authUrl = "https://MiOS-DEV:$($env:GHCR_TOKEN)@github.com/MiOS-DEV/MiOS.git"
        & git clone --depth 1 $authUrl $RepoDir 2>&1 | ForEach-Object { Write-Log $_ }
    } else {
        & git clone --depth 1 $RepoUrl $RepoDir 2>&1 | ForEach-Object { Write-Log $_ }
    }
    if ($LASTEXITCODE -ne 0) { Write-LogFatal "git clone failed. Check network and token." }
    Write-LogOK "Repo cloned: $RepoDir"
}
Set-Location $RepoDir
Finish-Phase 2

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 3 -- MiOS-DEV distro (formerly MiOS-BUILDER pre-v0.2.3)
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 3 "Provisioning $BuilderMachine Podman machine..."
$builderScript = Join-Path $RepoDir "automation\mios-build-builder.ps1"
if (-not (Test-Path $builderScript)) { Write-LogFatal "Missing $builderScript" }
& $builderScript -MachineName $BuilderMachine 2>&1 | ForEach-Object {
    $l = Format-Masked $_
    Set-Op $l
    Write-Log $l
}
if ($LASTEXITCODE -ne 0) { Write-LogFatal "Builder provisioning failed" }
& podman system connection default "${BuilderMachine}-root" 2>$null
Write-LogOK "Connection: ${BuilderMachine}-root"
Finish-Phase 3

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 4 -- WSL2 configuration
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 4 "Writing .wslconfig..."
$wslCfg = Join-Path $env:USERPROFILE ".wslconfig"
$wslRAM = [Math]::Max(16, [Math]::Floor($ram * 0.80))
$wslLines = @(
    "# 'MiOS' v$Version -- WSL2 Configuration"
    "[wsl2]"
    "memory=${wslRAM}GB"
    "processors=${cpu}"
    "swap=8GB"
    "localhostForwarding=true"
    "nestedVirtualization=true"
    "vmIdleTimeout=-1"
    ""
    "[experimental]"
    "networkingMode=mirrored"
    "dnsTunneling=true"
    "autoProxy=true"
)
$wslLines -join "`r`n" | Set-Content $wslCfg -Encoding UTF8
Write-LogOK ".wslconfig: ${wslRAM}GB RAM, $cpu CPUs"
Finish-Phase 4

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 5 -- Verifying build context
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 5 "Checking repo files..."
foreach ($f in @("Containerfile","VERSION","automation/build.sh","automation/31-user.sh")) {
    if (-not (Test-Path (Join-Path $RepoDir $f))) { Write-LogFatal "Missing: $f" }
}
Write-LogOK "Build context verified"
Finish-Phase 5

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 6 -- Identity
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 6 "Collecting credentials..."
$AutoInstall = $env:MIOS_AUTOINSTALL -eq "1"

$U = if ($env:MIOS_USER) { $env:MIOS_USER }
     elseif ($AutoInstall) { 'mios' }
     else { Read-Plain "Admin username:" "mios" }
$P = if ($env:MIOS_PASSWORD) { $env:MIOS_PASSWORD } else {
    if ($AutoInstall) { "mios" } else {
        $pw1 = Read-Masked "Admin password:" ""
        $pw2 = Read-Masked "Confirm password:" ""
        while ($pw1 -ne $pw2) {
            Write-LogWarn "Passwords do not match -- retry"
            $pw1 = Read-Masked "Admin password:" ""
            $pw2 = Read-Masked "Confirm password:" ""
        }
        $pw1
    }
}
Register-Secret $P

$HostIn = if ($env:MIOS_HOSTNAME) { $env:MIOS_HOSTNAME } else {
    if ($AutoInstall) { "mios" } else { Read-Plain "Hostname (blank=mios-XXXXX):" "mios" }
}
if ($HostIn -eq "mios") {
    $HostIn = "mios-$('{0:D5}' -f (Get-Random -Min 10000 -Max 99999))"
}

# GHCR token: only needed for pulling the private MiOS helper image as
# the build base on the *first* build of a new host. AutoInstall (which
# pipeline -NoPrompt sets) skips the prompt; the build then falls back
# to alpine/python helpers, which is the same path a fresh first-time
# build takes anyway.
$GhcrToken = if ($env:GHCR_TOKEN) { $env:GHCR_TOKEN }
             elseif ($AutoInstall) { '' }
             else { Read-Masked "GitHub PAT for ghcr.io base image pull (github.com/settings/tokens):" }
if ($GhcrToken) { Register-Secret $GhcrToken }

$RegUser  = if ($env:MIOS_GHCR_USER) { $env:MIOS_GHCR_USER } else { "MiOS-DEV" }
$GhcrImage = "ghcr.io/$RegUser/${ImageName}:${ImageTag}"

Write-LogOK "User: $U  Hostname: $HostIn  Registry: $GhcrImage"
Finish-Phase 6

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 7 -- Writing identity
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 7 "Hashing password (SHA-512)..."

# Pull helper image for openssl -- try existing 'MiOS' image first
$HelperImage = ""
if ($GhcrToken) {
    $GhcrToken | & podman login ghcr.io --username $RegUser --password-stdin 2>&1 | Out-Null
}
& podman pull $GhcrImage 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $HelperImage = $GhcrImage
    Write-LogOK "Helper image: $GhcrImage (self-building)"
} else {
    & podman image exists $LocalImage 2>$null
    if ($LASTEXITCODE -eq 0) { $HelperImage = $LocalImage }
}

$passHash = Get-SHA512Hash -PlainText $P -HImg $HelperImage
if (-not $passHash -or $passHash -notmatch '^\$6\$') {
    Write-LogFatal "Password hashing failed. Is Podman machine running?"
}
Register-Secret $passHash
Write-LogOK "Password hashed (SHA-512)"

if ($HostIn -ne "mios") {
    Set-Content (Join-Path $RepoDir "etc/hostname") $HostIn -Encoding ascii
    Write-LogOK "Hostname written: $HostIn"
}
Finish-Phase 7

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 8 -- App registration (BIB self-build detection)
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 8 "Checking BIB capability..."
$BIBSelfBuild = $false
if ($HelperImage) {
    $null = & podman run --rm $HelperImage which bootc-image-builder 2>$null
    if ($LASTEXITCODE -eq 0) {
        $BIBImage = $HelperImage; $BIBSelfBuild = $true
        Write-LogOK "Self-building BIB: 'MiOS' image is the builder"
    } else {
        Write-Log "Using centos-bootc BIB ('MiOS' lacks bootc-image-builder binary)"
    }
}
Finish-Phase 8

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 9 -- Building OCI image
#  Every output line from podman build drives Op: -- no frozen dashboard.
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 9 "podman build starting..."
$env:BUILDAH_FORMAT = "docker"
$script:Phases[9].InnerTotal = 48   # will be updated from first STEP marker

$t9 = [DateTime]::Now
& podman build --progress=plain --no-cache `
    --build-arg MAKEFLAGS="-j$cpu" `
    --build-arg MIOS_USER="$U" `
    --build-arg MIOS_HOSTNAME="$HostIn" `
    --build-arg MIOS_PASSWORD_HASH="$passHash" `
    --jobs 2 -t $LocalImage (Get-Location).Path 2>&1 | ForEach-Object {

    $line     = $_
    $stripped = ($line -replace '^\s*#\d+\s+(?:[\d.]+\s+)?','').TrimStart()
    Write-Log (Format-Masked $line) -Color DarkGray

    # build.sh step header: +- STEP 01/48 : 01-repos.sh ---- 00:00 -+
    if ($stripped -match '\+-\s*STEP\s+(\d+)/(\d+)\s*:\s*(\S+)') {
        $script:Phases[9].InnerStep  = [int]$Matches[1]
        $script:Phases[9].InnerTotal = [int]$Matches[2]
        Set-Op "STEP $($Matches[1])/$($Matches[2]) -- $($Matches[3])"
        Show-Dashboard   # full redraw on each script boundary
    } else {
        # Every non-empty line updates Op: for live feedback
        $candidate = ($stripped -replace '\s+',' ').Trim()
        if ($candidate.Length -gt 72) { $candidate = $candidate.Substring(0,69) + '...' }
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            Set-Op (Format-Masked $candidate)
        }
    }
}
$buildExitCode = $LASTEXITCODE

& git -C $RepoDir checkout etc/hostname 2>$null | Out-Null
if ($buildExitCode -ne 0) { Write-LogFatal "podman build failed (exit $buildExitCode)" }

$buildMin = [Math]::Round(([DateTime]::Now - $t9).TotalMinutes, 1)
Write-LogOK "Image built in $buildMin min: $LocalImage"

# Tag with GHCR ref (sets update origin for bootc)
& podman tag $LocalImage $GhcrImage
Write-LogOK "Update origin: $GhcrImage"

# Rechunk
Set-Op "Rechunking OCI layers..."
$ErrorActionPreference = "Continue"
& podman run --rm --privileged -v /var/lib/containers/storage:/var/lib/containers/storage `
    $LocalImage /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 "containers-storage:$LocalImage" "containers-storage:$LocalImage" 2>&1 | ForEach-Object { Set-Op (Format-Masked $_) }
if ($LASTEXITCODE -ne 0) {
    Write-LogWarn "Self rechunk failed; trying external rechunker"
    & podman run --rm --privileged -v /var/lib/containers/storage:/var/lib/containers/storage `
        "quay.io/centos-bootc/centos-bootc:stream10" /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 "containers-storage:$LocalImage" "containers-storage:$LocalImage" 2>&1 | Out-Null
}
$ErrorActionPreference = "Stop"
Write-LogOK "Rechunk complete"

# Update helper image
$HelperImage = $LocalImage
$null = & podman run --rm $LocalImage which bootc-image-builder 2>$null
if ($LASTEXITCODE -eq 0) { $BIBImage = $LocalImage; $BIBSelfBuild = $true }

# Inject build log (pre-BIB snapshot) into OCI image
if ($script:LogFile -and (Test-Path $script:LogFile)) {
    Set-Op "Injecting build log into image..."
    try { Stop-Transcript | Out-Null } catch {}
    $cid = (& podman create $LocalImage sh 2>$null).Trim()
    if ($cid) {
        & podman cp $script:LogFile "${cid}:/usr/share/mios/build-log.txt" 2>$null | Out-Null
        & podman commit --quiet --pause=false $cid $LocalImage 2>$null | Out-Null
        & podman rm -f $cid 2>$null | Out-Null
        Write-LogOK "Build log baked into image: /usr/share/mios/build-log.txt"
    }
    try { Start-Transcript -Path $script:LogFile -Append -Force | Out-Null } catch {}
}
Finish-Phase 9

# ══════════════════════════════════════════════════════════════════════════════
#  PHASES 10-12 -- Export / register / disk images
# ══════════════════════════════════════════════════════════════════════════════
$bibConf     = Join-Path $RepoDir "config\bib.toml"
if (-not (Test-Path $bibConf)) { $bibConf = Join-Path $RepoDir "config\bib.json" }
$bibConfDest = $null; $bibMountPath = "/config.toml"
if (Test-Path $bibConf) {
    $bibConfDest = Join-Path $MiosDeployDir "bib-config.toml"
    Copy-Item $bibConf $bibConfDest -Force
}

function Get-BIBArgs {
    param([string]$Type)
    $a = @("run","--rm","-it","--privileged","--security-opt","label=type:unconfined_t",
           "-v","/var/lib/containers/storage:/var/lib/containers/storage",
           "-v","${MiosDeployDir}:/output:z")
    if ($bibConfDest) { $a += @("-v","${bibConfDest}:${bibMountPath}:ro") }
    $a += @($BIBImage,"build","--type",$Type,"--rootfs","ext4","--local",$LocalImage)
    return $a
}

# Phase 10 -- WSL2 export
Start-Phase 10 "Exporting WSL2 image..."
$ErrorActionPreference = "Continue"
if ($HelperImage) {
    & podman run --rm --privileged -v "${MiosDeployDir}:/output:z" $HelperImage bootc container export --format=tar --output /output/mios-wsl.tar "containers-storage:$LocalImage" 2>&1 | ForEach-Object { Set-Op (Format-Masked $_) }
}
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $TargetWsl)) {
    $wslCid = (& podman create $LocalImage 2>$null).Trim()
    if ($wslCid) { & podman export $wslCid -o $TargetWsl; & podman rm $wslCid 2>$null | Out-Null }
}
if (Test-Path $TargetWsl) { Write-LogOK "WSL: $(Get-FileSize $TargetWsl)" } else { Write-LogWarn "WSL export failed" }
$ErrorActionPreference = "Stop"
Finish-Phase 10

# Phase 11 -- WSL2 registration
Start-Phase 11 "Importing WSL2 distro..."
$ErrorActionPreference = "Continue"
if (Test-Path $TargetWsl) {
    $WslName = "MiOS"; $WslPath = Join-Path $env:USERPROFILE "WSL\$WslName"
    $existing = wsl --list --quiet 2>$null | Where-Object { $_ -match "^$WslName" }
    if ($existing) { wsl --unregister $WslName 2>$null | Out-Null }
    New-Item -ItemType Directory -Path $WslPath -Force | Out-Null
    wsl --import $WslName $WslPath $TargetWsl --version 2 2>&1 | ForEach-Object { Set-Op $_ }
    if ($LASTEXITCODE -eq 0) {
        Write-LogOK "WSL2 distro '$WslName' registered"
        # Seed /etc/mios/install.env so wsl-firstboot.service uses the
        # operator-supplied identity instead of the default 'mios' password.
        if (Write-MiosInstallEnv -WslDistro $WslName -User $U -PasswordHash $passHash -Hostname $HostIn) {
            Write-LogOK "Seeded /etc/mios/install.env (user=$U, host=$HostIn)"
        } else {
            Write-LogWarn "install.env not written -- first-boot will fall back to default 'mios' password"
        }
    } else {
        Write-LogWarn "WSL import failed"
    }
}
$ErrorActionPreference = "Stop"
Finish-Phase 11

# Phase 12 -- Disk images (VHDX + ISO via BIB)
Start-Phase 12 "Building disk images (BIB)..."
$script:Phases[12].InnerTotal = 2
$ErrorActionPreference = "Continue"

# VHDX
Set-Op "BIB: building VHDX..."
$vhdArgs = Get-BIBArgs "vhd"
$vhdExit = Invoke-BIBRun -BIBArgs $vhdArgs -Label "VHDX"
if ($vhdExit -eq 0) {
    $script:Phases[12].InnerStep = 1
    $vhdFile = Get-ChildItem $MiosDeployDir -Recurse -Include "*.vhd","*.vpc" -EA SilentlyContinue | Select-Object -First 1
    if ($vhdFile) {
        Set-Op "Converting VHD → VHDX..."
        if ($HelperImage) {
            & podman run --rm -v "${MiosDeployDir}:/data:z" $HelperImage qemu-img convert -m 16 -W -f vpc -O vhdx /data/$($vhdFile.Name) /data/mios-hyperv.vhdx 2>&1 | Out-Null
        }
        Remove-Item $vhdFile.FullName -Force -EA SilentlyContinue
        if (Test-Path $TargetVhdx) { Write-LogOK "VHDX: $(Get-FileSize $TargetVhdx)" }
    }
} else { Write-LogWarn "VHDX build failed" }

# ISO
Set-Op "BIB: building ISO..."
$isoArgs = Get-BIBArgs "anaconda-iso"
$isoExit = Invoke-BIBRun -BIBArgs $isoArgs -Label "ISO"
$script:Phases[12].InnerStep = 2
if ($isoExit -eq 0) {
    $isoFile = Get-ChildItem $MiosDeployDir -Recurse -Filter "*.iso" -EA SilentlyContinue | Select-Object -First 1
    if ($isoFile) { Move-Item $isoFile.FullName $TargetIso -Force; Write-LogOK "ISO: $(Get-FileSize $TargetIso)" }
} else { Write-LogWarn "ISO build failed" }

$ErrorActionPreference = "Stop"
Finish-Phase 12

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 13 -- Hyper-V deployment
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 13 "Preparing Hyper-V VM..."
$ErrorActionPreference = "Continue"

if (Test-Path $TargetVhdx) {
    $vmName = "MiOS"
    $doDeploy = ($AutoInstall -or $env:MIOS_FORCE_DEPLOY -eq "1")
    if (-not $doDeploy) {
        $ans = Read-Plain "Deploy/Update Hyper-V VM '$vmName'? (y/N)" "N"
        $doDeploy = $ans -match "^[yY]"
    }

    if ($doDeploy) {
        try {
            if (Get-VM -Name $vmName -EA SilentlyContinue) {
                Stop-VM -Name $vmName -Force -EA SilentlyContinue
                Remove-VM -Name $vmName -Force
            }
            $vmSwitch = (Get-VMSwitch | Where-Object SwitchType -eq "External" | Select-Object -First 1)?.Name ?? "Default Switch"
            $totalMem = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
            $vmRam    = [int64]([Math]::Floor($totalMem * 0.80 / 2MB) * 2MB)
            $minRam   = [int64]([Math]::Floor($totalMem * 0.50 / 2MB) * 2MB)
            New-VM -Name $vmName -MemoryStartupBytes $minRam -Generation 2 -VHDPath $TargetVhdx -SwitchName $vmSwitch | Out-Null
            Set-VM -Name $vmName -ProcessorCount $cpu -DynamicMemory -MemoryMinimumBytes $minRam -MemoryMaximumBytes $vmRam -MemoryStartupBytes $minRam
            Set-VMFirmware -VMName $vmName -SecureBootTemplate "MicrosoftUEFICertificateAuthority"
            Start-VM -Name $vmName
            Write-LogOK "Hyper-V VM '$vmName' created and started"

            # Wait for heartbeat
            $timeout = 120; $elapsed = 0
            while ($elapsed -lt $timeout) {
                $hb = (Get-VMIntegrationService -VMName $vmName | Where-Object Name -eq "Heartbeat").PrimaryStatusDescription
                if ($hb -eq "OK") { break }
                Start-Sleep 5; $elapsed += 5
                Set-Op "Waiting for VM heartbeat... ${elapsed}s"
            }
            Stop-VM -Name $vmName -Force -EA SilentlyContinue
            Set-VM -Name $vmName -EnhancedSessionTransportType HvSocket
            Start-VM -Name $vmName
            Write-LogOK "Hyper-V VM ready: vmconnect.exe localhost $vmName"
        } catch { Write-LogWarn "Hyper-V deploy error: $_" }
    }
}
$ErrorActionPreference = "Stop"
Finish-Phase 13

# ══════════════════════════════════════════════════════════════════════════════
#  FINAL -- Summary
# ══════════════════════════════════════════════════════════════════════════════
Set-Op "Build complete."
Show-Dashboard

# Copy unified log to all output dirs
$logName = Split-Path $script:LogFile -Leaf
foreach ($d in @($MiosImagesDir, $MiosDeployDir)) {
    Copy-Item $script:LogFile (Join-Path $d $logName) -Force -EA SilentlyContinue
}
Write-LogOK "Unified log: $($script:LogFile)"

Write-Host ""
Write-Host "  Targets produced:" -ForegroundColor Cyan
foreach ($p in @($TargetVhdx,$TargetWsl,$TargetIso)) {
    if (Test-Path $p) { Write-Host "    [OK] $(Split-Path $p -Leaf)  $(Get-FileSize $p)" -ForegroundColor Green }
}
Write-Host ""
Write-Host "  irm | iex → build → VHDX → Hyper-V  |  bootc upgrade on deployed 'MiOS'" -ForegroundColor DarkGray
Write-Host ""

try { Stop-Transcript | Out-Null } catch {}

# Wipe credentials from memory
$P = $null; $passHash = $null; $GhcrToken = $null
[GC]::Collect()
