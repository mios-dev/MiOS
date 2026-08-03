# AI-hint: Dashboard state & phase tracking functions extracted from build-mios.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Show-MiosProgressBar {
    param(
        [hashtable]$PhStat,
        [int]$TotalPhases
    )
    if (-not $PhStat) { return }
    $done = [int]($PhStat.Values | Where-Object { $_ -ge 2 } | Measure-Object).Count
    if ($TotalPhases -le 0) { return }
    $pct = [int](($done / $TotalPhases) * 100)
    $barW = 50
    $filled = [int](($done / $TotalPhases) * $barW)
    if ($filled -lt 0) { $filled = 0 }
    if ($filled -gt $barW) { $filled = $barW }
    $empty = $barW - $filled

    $fStr = "=" * $filled
    $eStr = "." * $empty
    $ts = [datetime]::Now.ToString("HH:mm:ss")
    Write-Host "[$ts] Progress: [$fStr$eStr] $pct% ($done/$TotalPhases phases)" -ForegroundColor Cyan
}

Export-ModuleMember -Function Show-MiosProgressBar
