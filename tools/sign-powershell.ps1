# AI-hint: Opt-in Authenticode signing script for shipped Windows PowerShell scripts.
[CmdletBinding()]
param(
    [string]$CertPath = "",
    # SecureString, never [string]. A plaintext password parameter forces
    # ConvertTo-SecureString -AsPlainText, which PSScriptAnalyzer rejects
    # (PSAvoidUsingConvertToSecureStringWithPlainText) because it puts the
    # secret in process memory and command history in the clear.
    [System.Security.SecureString]$CertPassword,
    [string[]]$ScriptPaths = @()
)

$ErrorActionPreference = 'Stop'
$rootDir = $PSScriptRoot
if (-not $rootDir) { $rootDir = (Get-Location).Path }
$repoRoot = (Get-Item $rootDir).Parent.FullName

# Resolve cert from parameters, env vars, or mios.toml
if (-not $CertPath) {
    $CertPath = $env:MIOS_SECURITY_POWERSHELL_SIGNING_SIGNING_CERT
    if (-not $CertPath) { $CertPath = $env:MIOS_SIGNING_CERT }
}

if (-not $CertPath) {
    $tomlPath = Join-Path $repoRoot "usr\share\mios\mios.toml"
    if (Test-Path $tomlPath) {
        $lines = Get-Content $tomlPath
        $inSec = $false
        foreach ($line in $lines) {
            if ($line -match '^\s*\[security\.powershell_signing\]') { $inSec = $true; continue }
            if ($inSec -and $line -match '^\s*\[') { break }
            if ($inSec -and $line -match '^\s*signing_cert\s*=\s*"(.*)"') {
                $CertPath = $matches[1]
            }
            # NOTE: the signing password is deliberately NOT read from
            # mios.toml. SSOT is committed to git; a signing secret there is
            # a leaked secret. Supply it as a SecureString parameter, or let
            # the prompt below collect it.
        }
    }
}

if (-not $CertPath) {
    Write-Host "[sign-powershell] INFO: No signing cert configured in mios.toml [security.powershell_signing]. Skipping signing (opt-in / degrade open)." -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path $CertPath)) {
    Write-Host "[sign-powershell] WARNING: Signing cert path '$CertPath' does not exist. Skipping signing." -ForegroundColor Yellow
    exit 0
}

# Resolve default script targets if none provided
if ($ScriptPaths.Count -eq 0) {
    $targets = @("Get-MiOS.ps1", "build-mios.ps1", "bootstrap.ps1")
    foreach ($t in $targets) {
        $p = Join-Path $repoRoot $t
        if (Test-Path $p) { $ScriptPaths += $p }
    }
    $winDir = Join-Path $repoRoot "usr\share\mios\windows"
    if (Test-Path $winDir) {
        Get-ChildItem -Path $winDir -Filter "*.ps1" | ForEach-Object { $ScriptPaths += $_.FullName }
    }
}

Write-Host "[sign-powershell] Signing $($ScriptPaths.Count) script(s) with $CertPath..." -ForegroundColor Cyan

$securePass = $CertPassword
if ($CertPath -match '\.pfx$|\.p12$' -and -not $securePass) {
    # Collect interactively rather than accepting plaintext from anywhere.
    $securePass = Read-Host -Prompt "Password for $CertPath" -AsSecureString
}

$cert = $null
if ($CertPath -match '\.pfx$|\.p12$') {
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertPath, $securePass)
} else {
    $cert = Get-Item "Cert:\LocalMachine\My\$CertPath" -ErrorAction SilentlyContinue
    if (-not $cert) {
        $cert = Get-Item "Cert:\CurrentUser\My\$CertPath" -ErrorAction SilentlyContinue
    }
}

if (-not $cert) {
    Write-Host "[sign-powershell] ERROR: Failed to load certificate from '$CertPath'." -ForegroundColor Red
    exit 1
}

$signedCount = 0
foreach ($scriptFile in $ScriptPaths) {
    $sig = Set-AuthenticodeSignature -FilePath $scriptFile -Certificate $cert -ErrorAction SilentlyContinue
    if ($sig.Status -eq 'Valid') {
        Write-Host "  [SIGNED] $scriptFile" -ForegroundColor Green
        $signedCount++
    } else {
        Write-Host "  [WARN] Failed to sign $scriptFile status=$($sig.Status)" -ForegroundColor Yellow
    }
}

Write-Host "[sign-powershell] Successfully signed $signedCount / $($ScriptPaths.Count) scripts." -ForegroundColor Cyan
exit 0
