# AI-hint: Windows branding and launcher installation helper functions extracted from build-mios.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MiosBrandingTagline {
    param([string]$DefaultTagline = 'Automated Operating System')
    $t = [Environment]::GetEnvironmentVariable('MIOS_BRANDING_TAGLINE')
    if ($t) { return $t }
    return $DefaultTagline
}

Export-ModuleMember -Function Get-MiosBrandingTagline
