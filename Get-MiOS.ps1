<#
.SYNOPSIS
    'MiOS' bootstrap -- one-liner entry point.

.DESCRIPTION
    Designed for:  irm https://raw.githubusercontent.com/MiOS-DEV/MiOS/main/Get-MiOS.ps1 | iex

    What it does:
      1. Elevates to Administrator if needed.
      2. Ensures Git + Podman are present.
      3. Clones / updates the 'MiOS' repo into $env:USERPROFILE\MiOS.
      4. Sets MIOS_UNIFIED_LOG so the entire session writes one flat transcript.
      5. Starts Start-Transcript (unified log).
      6. Calls mios-build-local.ps1 from the repo root.
      7. Stops the transcript on exit.

    The unified log is written to ~/Documents/MiOS/mios-build-<timestamp>.log and
    copied into the build output directories by mios-build-local.ps1 at the end.
#>
param(
    [string]$RepoUrl  = "https://github.com/MiOS-DEV/MiOS.git",
    [string]$Branch   = "main",
    [string]$RepoDir  = (Join-Path $env:USERPROFILE "MiOS"),
    [string]$Workflow = ""         # passed through to mios-build-local.ps1
)

$ErrorActionPreference = "Stop"

# ── 1. Elevation ──────────────────────────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $args_ = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($Workflow) { $args_ += " -Workflow $Workflow" }
    Start-Process powershell.exe -ArgumentList $args_ -Verb RunAs
    return
}

# ── 2. Helpers ────────────────────────────────────────────────────────────────
function Write-Info  { param([string]$M) Write-Host "  [*] $M" -ForegroundColor Cyan }
function Write-Good  { param([string]$M) Write-Host "  [+] $M" -ForegroundColor Green }
function Write-Err   { param([string]$M) Write-Host "  [!] $M" -ForegroundColor Red }
function Require-Cmd {
    param([string]$Cmd, [string]$InstallHint)
    if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) {
        Write-Err "$Cmd not found. $InstallHint"
        exit 1
    }
}

Write-Host "'MiOS' Bootstrap  (irm | iex entry)" -ForegroundColor Cyan

# ── 3. Prerequisites ──────────────────────────────────────────────────────────
Require-Cmd "git"    "Install Git from https://git-scm.com/download/win"
Require-Cmd "podman" "Install Podman Desktop from https://podman-desktop.io"
Write-Good "Prerequisites OK (git, podman)"

# ── 4. Unified log path (before transcript starts) ────────────────────────────
$LogDir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "MiOS"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogFile = Join-Path $LogDir "mios-build-$([DateTime]::Now.ToString('yyyyMMdd-HHmmss')).log"
[Environment]::SetEnvironmentVariable("MIOS_UNIFIED_LOG", $LogFile)
Write-Info "Unified log → $LogFile"

# ── 5. Start transcript ───────────────────────────────────────────────────────
try { Start-Transcript -Path $LogFile -Force | Out-Null } catch {}

# ── 6. Clone / update repo ────────────────────────────────────────────────────
if (Test-Path (Join-Path $RepoDir ".git")) {
    Write-Info "Updating existing repo at $RepoDir ..."
    Push-Location $RepoDir
    & git fetch origin 2>&1 | Write-Host
    & git checkout $Branch 2>&1 | Write-Host
    & git pull --ff-only origin $Branch 2>&1 | Write-Host
    Pop-Location
} else {
    Write-Info "Cloning $RepoUrl → $RepoDir ..."
    & git clone --branch $Branch --depth 1 $RepoUrl $RepoDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "git clone failed"
        try { Stop-Transcript | Out-Null } catch {}
        exit 1
    }
}
Write-Good "Repo ready at $RepoDir"

# ── 7. Launch build script ────────────────────────────────────────────────────
$buildScript = Join-Path $RepoDir "mios-build-local.ps1"
if (-not (Test-Path $buildScript)) {
    Write-Err "mios-build-local.ps1 not found in $RepoDir"
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

if ($Workflow) { $env:MIOS_WORKFLOW = $Workflow }

Write-Info "Entering repo root and launching mios-build-local.ps1 ..."
Push-Location $RepoDir
try {
    & $buildScript
} finally {
    Pop-Location
    try { Stop-Transcript | Out-Null } catch {}
}
