# AI-hint: Thin shim invoking canonical /usr/libexec/mios/Setup-MiOSLanPortProxy.ps1 with -AiNode switch.
# AI-related: /usr/libexec/mios/Setup-MiOSLanPortProxy.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$canonical = Join-Path $scriptDir '..\..\..\libexec\mios\Setup-MiOSLanPortProxy.ps1'

if (Test-Path $canonical) {
    & $canonical -AiNode @args
} else {
    Write-Error "Canonical Setup-MiOSLanPortProxy.ps1 not found at $canonical"
}
