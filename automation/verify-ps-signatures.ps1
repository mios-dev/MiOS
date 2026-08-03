# AI-hint: Verification gate for Authenticode signatures on shipped Windows PowerShell scripts.
[CmdletBinding()]
param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = 'Stop'
if (-not $RepoRoot) {
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
    $RepoRoot = (Get-Item $scriptDir).Parent.FullName
}

# Check if signing is enabled in mios.toml
$CertPath = ""
$tomlPath = Join-Path $RepoRoot "usr\share\mios\mios.toml"
if (Test-Path $tomlPath) {
    $lines = Get-Content $tomlPath
    $inSec = $false
    foreach ($line in $lines) {
        if ($line -match '^\s*\[security\.powershell_signing\]') { $inSec = $true; continue }
        if ($inSec -and $line -match '^\s*\[') { break }
        if ($inSec -and $line -match '^\s*signing_cert\s*=\s*"(.*)"') {
            $CertPath = $matches[1]
        }
    }
}

$shippedScripts = @()
$baseTargets = @("Get-MiOS.ps1", "build-mios.ps1", "bootstrap.ps1")
foreach ($t in $baseTargets) {
    $p = Join-Path $RepoRoot $t
    if (Test-Path $p) { $shippedScripts += $p }
}

$winDir = Join-Path $RepoRoot "usr\share\mios\windows"
if (Test-Path $winDir) {
    Get-ChildItem -Path $winDir -Filter "*.ps1" | ForEach-Object { $shippedScripts += $_.FullName }
}

if (-not $CertPath) {
    Write-Host "[verify-ps-signatures] PASS: No signing cert configured in mios.toml (opt-in mode). All $($shippedScripts.Count) shipped scripts are allowlisted as unsigned dev builds." -ForegroundColor Green
    exit 0
}

Write-Host "[verify-ps-signatures] Verifying Authenticode signatures for $($shippedScripts.Count) shipped scripts..." -ForegroundColor Cyan

$invalidCount = 0
foreach ($s in $shippedScripts) {
    $sig = Get-AuthenticodeSignature -FilePath $s -ErrorAction SilentlyContinue
    if ($sig.Status -eq 'Valid') {
        Write-Host "  [OK] $s ($($sig.SignerCertificate.Subject))" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $s - Signature Status: $($sig.Status)" -ForegroundColor Red
        $invalidCount++
    }
}

if ($invalidCount -gt 0) {
    Write-Host "[verify-ps-signatures] FAIL: $invalidCount script(s) failed signature verification." -ForegroundColor Red
    exit 1
}

Write-Host "[verify-ps-signatures] PASS: All $($shippedScripts.Count) shipped scripts carry valid signatures." -ForegroundColor Green
exit 0
