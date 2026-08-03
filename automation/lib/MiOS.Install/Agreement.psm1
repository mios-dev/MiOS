# AI-hint: Agreement gate UI functions extracted from Get-MiOS.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MiosAgreementAckState {
    param([string]$EnvVarName = 'MIOS_REQUIRE_AGREEMENT_ACK')
    $v = [Environment]::GetEnvironmentVariable($EnvVarName)
    if ($v -eq '0' -or $v -eq 'false') { return $false }
    return $true
}

Export-ModuleMember -Function Get-MiosAgreementAckState
