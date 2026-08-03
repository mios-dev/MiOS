# AI-hint: Terminal theming functions extracted from Get-MiOS.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MiosThemeName {
    param([string]$DefaultTheme = 'default')
    $t = [Environment]::GetEnvironmentVariable('MIOS_DESKTOP_THEME')
    if ($t) { return $t }
    return $DefaultTheme
}

Export-ModuleMember -Function Get-MiosThemeName
