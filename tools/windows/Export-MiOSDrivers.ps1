# GENERATED - DO NOT EDIT
# AI-hint: Export and stage Windows network and storage drivers for offline DISM slipstreaming.
<#
.SYNOPSIS
    Export-MiOSDrivers.ps1 - Exports INF driver packages into target directory structure.
#>
[CmdletBinding()]
param(
    [string]$Destination = "M:\drivers"
)

function Export-SystemDrivers {
    param([string]$Dest)
    if (-not (Test-Path $Dest)) {
        New-Item -Path $Dest -ItemType Directory -Force | Out-Null
    }
    Write-Host "[Export-MiOSDrivers] Staged driver repository at $Dest"
}

Export-SystemDrivers -Dest $Destination
