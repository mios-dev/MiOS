<#
.SYNOPSIS
    'MiOS' bootstrap -- legacy redirector to the canonical bootstrap-side
    Get-MiOS.ps1.

.DESCRIPTION
    The canonical Windows entry point now lives in mios-bootstrap.git
    because that repository owns the user-facing surface: dotfiles,
    mios.toml, and the build orchestrator. The MiOS repo is the system
    FHS overlay (factory defaults baked into the deployed image); it is
    no longer the entry point.

    Canonical one-liner (from PowerShell as Administrator):

        irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex

    This script exists so the legacy MiOS-side URL keeps working: it
    delegates straight to the bootstrap-side equivalent. New callers
    should switch to the bootstrap URL above.
#>
param(
    [string]$RepoUrl  = "https://github.com/mios-dev/mios-bootstrap.git",
    [string]$Branch   = "main",
    [string]$RepoDir  = (Join-Path $env:USERPROFILE "MiOS-bootstrap"),
    [string]$Workflow = ""
)

$ErrorActionPreference = "Stop"

if ($env:MIOS_AGREEMENT_BANNER -notin @('quiet','silent','off','0','false','FALSE')) {
    [Console]::Error.WriteLine(@"
[mios] Get-MiOS.ps1 in mios.git is now a legacy redirector. The canonical
       entry point is mios-bootstrap/Get-MiOS.ps1. Delegating to it now;
       no action required. Update bookmarks to:
           https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1
"@)
}

$bootstrapUrl = "https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1"
& ([scriptblock]::Create((Invoke-RestMethod $bootstrapUrl))) `
    -RepoUrl $RepoUrl -Branch $Branch -RepoDir $RepoDir -Workflow $Workflow
exit $LASTEXITCODE
