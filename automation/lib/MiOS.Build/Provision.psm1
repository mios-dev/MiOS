# AI-hint: Builder distro and WSL machine provisioning helper functions extracted from build-mios.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-WslDistroExists {
    param([string]$DistroName)
    if (-not $DistroName) { return $false }
    $distros = & wsl.exe -l -q 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $distros) { return $false }
    foreach ($d in $distros) {
        $clean = $d.Replace("`0", "").Trim()
        if ($clean -eq $DistroName) { return $true }
    }
    return $false
}

Export-ModuleMember -Function Test-WslDistroExists
