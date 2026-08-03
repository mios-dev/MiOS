# AI-hint: Windows tool installation helper functions extracted from Get-MiOS.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-CommandAvailable {
    param([string]$CommandName)
    if (-not $CommandName) { return $false }
    return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

Export-ModuleMember -Function Test-CommandAvailable
