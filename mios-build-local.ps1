# AI-hint: Legacy PowerShell redirector that routes local build commands to build-mios.ps1 to maintain backward compatibility for existing MiOS build scripts and one-liners.
# AI-doc: usr/share/doc/mios/manual/root.md

$ErrorActionPreference = "Stop"
$target = Join-Path $PSScriptRoot 'build-mios.ps1'
if (-not (Test-Path $target)) {
    Write-Error "build-mios.ps1 not found in $PSScriptRoot. Re-clone the repo."
    exit 1
}
& $target @args
exit $LASTEXITCODE
