# AI-hint: Live installer dashboard functions extracted from Get-MiOS.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MiosInstallerPhaseName {
    param([int]$PhaseId)
    $phases = @{
        0 = 'Prerequisites'
        1 = 'Podman Engine'
        2 = 'WSL Engine'
        3 = 'Dev Distro'
        4 = 'SSH Bridge'
        5 = 'Final Handoff'
    }
    if ($phases.ContainsKey($PhaseId)) { return $phases[$PhaseId] }
    return "Phase $PhaseId"
}

Export-ModuleMember -Function Get-MiosInstallerPhaseName
