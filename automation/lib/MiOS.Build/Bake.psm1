# AI-hint: OCI image bake and export helper functions extracted from build-mios.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Format-BuildSpan {
    param([TimeSpan]$Span)
    if (-not $Span) { return "--:--" }
    return "{0:D2}:{1:D2}" -f [int]$Span.TotalMinutes, $Span.Seconds
}

Export-ModuleMember -Function Format-BuildSpan
