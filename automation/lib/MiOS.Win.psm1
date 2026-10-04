# AI-hint: Windows Task Scheduler and interpreter resolution helper module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-MiosPowerShellExe {
    # Get-Command returns $null when pwsh.exe is absent (any non-Windows host,
    # e.g. the Linux runner that lints and Pester-tests this module), and
    # $null.Source throws PropertyNotFoundException under StrictMode. Resolve
    # the command object first, then read .Source only if we got one.
    $cmd = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command pwsh -ErrorAction SilentlyContinue }
    $psExe = if ($cmd) { $cmd.Source } else { $null }

    if (-not $psExe -or $psExe -like '*\WindowsApps\*' -or -not (Test-Path -LiteralPath $psExe)) {
        if ($env:WINDIR) {
            $psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
        }
    }
    return $psExe
}
Export-ModuleMember -Function Get-MiosPowerShellExe
