#Requires -Version 5.1
<#
.SYNOPSIS
    MiOS local build entry point for Windows (Docker Desktop + WSL2).

.DESCRIPTION
    Builds the MiOS OCI image locally using Docker Desktop (WSL2 backend),
    then uses bootc-image-builder to produce a VHDX for Hyper-V import.

.PARAMETER OutputFormat
    Disk image format to produce: vhdx (default), raw, qcow2, wsl2

.PARAMETER Tag
    Local image tag (default: mios:local)

.PARAMETER SkipBib
    Build the container image only; skip bootc-image-builder disk conversion.

.EXAMPLE
    .\Build-MiOS.ps1
    .\Build-MiOS.ps1 -OutputFormat wsl2
    .\Build-MiOS.ps1 -SkipBib
#>
param(
    [ValidateSet('vhdx','raw','qcow2','wsl2')]
    [string]$OutputFormat = 'vhdx',
    [string]$Tag = 'mios:local',
    [switch]$SkipBib
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Colour helpers ─────────────────────────────────────────────────────────
function Write-Step   { param([string]$Msg) Write-Host "==> $Msg" -ForegroundColor Cyan }
function Write-Ok     { param([string]$Msg) Write-Host " ok $Msg" -ForegroundColor Green }
function Write-Warn   { param([string]$Msg) Write-Host "WARN $Msg" -ForegroundColor Yellow }
function Write-Fail   { param([string]$Msg) Write-Host "FAIL $Msg" -ForegroundColor Red; exit 1 }

# ── Preflight ──────────────────────────────────────────────────────────────
Write-Step "Preflight checks"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Fail "docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
}
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Docker daemon not running. Start Docker Desktop and try again."
}
if ($dockerInfo -notmatch 'WSL') {
    Write-Warn "Docker Desktop does not appear to be using the WSL2 backend. Build may be slower."
}

if (-not (Test-Path 'Containerfile')) {
    Write-Fail "Containerfile not found. Run this script from the MiOS repo root."
}
Write-Ok "Docker Desktop + Containerfile found"

# ── Environment variables ──────────────────────────────────────────────────
Write-Step "Loading build environment"

# Load from ~/.config/mios/env.toml if present
$EnvToml = "$HOME\.config\mios\env.toml"
if (Test-Path $EnvToml) {
    Write-Ok "Reading $EnvToml"
    Get-Content $EnvToml | ForEach-Object {
        if ($_ -match '^\s*(\w+)\s*=\s*"?([^"#]+)"?') {
            $k = $Matches[1]; $v = $Matches[2].Trim()
            if (-not [System.Environment]::GetEnvironmentVariable($k)) {
                [System.Environment]::SetEnvironmentVariable($k, $v)
                Write-Host "  $k = $v"
            }
        }
    }
}

# Mandatory secrets — prompt if not set
if (-not $env:MIOS_USER_PASSWORD_HASH) {
    $pw = Read-Host -Prompt "MIOS_USER_PASSWORD_HASH (openssl passwd -6 <password>)"
    $env:MIOS_USER_PASSWORD_HASH = $pw
}
if (-not $env:MIOS_SSH_PUBKEY) {
    $key = Read-Host -Prompt "MIOS_SSH_PUBKEY (your SSH public key, or Enter to skip)"
    if ($key) { $env:MIOS_SSH_PUBKEY = $key }
}

# ── Build OCI image ────────────────────────────────────────────────────────
Write-Step "Building MiOS OCI image ($Tag)"

$BuildArgs = @(
    'build',
    '--tag', $Tag,
    '--file', 'Containerfile',
    '--build-arg', "MIOS_USER_PASSWORD_HASH=$env:MIOS_USER_PASSWORD_HASH"
)
if ($env:MIOS_SSH_PUBKEY) {
    $BuildArgs += '--build-arg', "MIOS_SSH_PUBKEY=$env:MIOS_SSH_PUBKEY"
}
$BuildArgs += '.'

docker @BuildArgs
if ($LASTEXITCODE -ne 0) { Write-Fail "docker build failed (exit $LASTEXITCODE)" }
Write-Ok "OCI image built: $Tag"

if ($SkipBib) {
    Write-Ok "Done (SkipBib set — skipping disk image conversion)"
    exit 0
}

# ── bootc-image-builder ────────────────────────────────────────────────────
Write-Step "Converting OCI → $OutputFormat via bootc-image-builder"

$OutputDir = Join-Path (Get-Location) 'output'
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Map format to BIB --type value
$BibType = switch ($OutputFormat) {
    'vhdx'  { 'vhd'   }
    'raw'   { 'raw'   }
    'qcow2' { 'qcow2' }
    'wsl2'  { 'wsl2'  }
}

# BIB config — substitute env vars
$BibConfig = @"
[[customizations.user]]
name = "mios"
password = "$env:MIOS_USER_PASSWORD_HASH"
$(if ($env:MIOS_SSH_PUBKEY) { 'key = "' + $env:MIOS_SSH_PUBKEY + '"' } else { '' })
groups = ["wheel"]
"@
$BibConfigPath = Join-Path $env:TEMP 'mios-bib.toml'
Set-Content -Path $BibConfigPath -Value $BibConfig -Encoding UTF8

docker run --rm --privileged `
    --security-opt label=type:unconfined_t `
    -v "${OutputDir}:/output" `
    -v "/var/run/docker.sock:/var/run/docker.sock" `
    -v "${BibConfigPath}:/config.toml" `
    "ghcr.io/osbuild/bootc-image-builder:latest" `
    --type $BibType `
    --config /config.toml `
    --local `
    $Tag

if ($LASTEXITCODE -ne 0) { Write-Fail "bootc-image-builder failed (exit $LASTEXITCODE)" }

# Rename vhd → vhdx
if ($OutputFormat -eq 'vhdx') {
    $VhdPath  = Join-Path $OutputDir 'disk.vhd'
    $VhdxPath = Join-Path $OutputDir 'disk.vhdx'
    if (Test-Path $VhdPath) {
        Move-Item -Force $VhdPath $VhdxPath
        Write-Ok "Disk image: $VhdxPath"
    }
} else {
    Write-Ok "Disk image: $(Join-Path $OutputDir "disk.$OutputFormat")"
}

Write-Step "Build complete"
Write-Host ""
Write-Host "  Image tag : $Tag"
Write-Host "  Output    : $OutputDir"
if ($OutputFormat -eq 'vhdx') {
    Write-Host ""
    Write-Host "  Import into Hyper-V:"
    Write-Host "    New-VM -Name MiOS -BootDevice VHD -VHDPath '$OutputDir\disk.vhdx' -Generation 2"
}
