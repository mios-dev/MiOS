# AI-hint: mios-* verb wrappers dispatch functions extracted from Get-MiOS.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MiosVerbList {
    return @(
        'build',
        'status',
        'doctor',
        'lan-status',
        'new',
        'template',
        'clean'
    )
}

Export-ModuleMember -Function Get-MiosVerbList
