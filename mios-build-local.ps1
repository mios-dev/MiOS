#Requires -Version 5.1
# 'MiOS' Windows build orchestrator -- legacy redirector.
#
# This file was renamed to build-mios.ps1 to align with the cross-platform
# entry-point convention (build-mios.{sh,ps1}). This redirector exists so
# existing irm | iex one-liners and shortcuts that point at the old
# mios-build-local.ps1 URL keep working.

$ErrorActionPreference = "Stop"
$target = Join-Path $PSScriptRoot 'build-mios.ps1'
if (-not (Test-Path $target)) {
    Write-Error "build-mios.ps1 not found in $PSScriptRoot. Re-clone the repo."
    exit 1
}
& $target @args
exit $LASTEXITCODE
