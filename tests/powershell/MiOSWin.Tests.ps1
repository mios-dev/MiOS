# AI-hint: Pester characterization tests for MiOS.Win.psm1 Windows helper module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$winModulePath = Join-Path $scriptDir '../../automation/lib/MiOS.Win.psm1'

Describe "MiOS.Win.psm1 Module" {
    BeforeAll {
        # Pester 5 runs BeforeAll in a different scope from the
        # discovery-phase top level, so recompute paths here.
        $winModulePath = Join-Path $PSScriptRoot '../../automation/lib/MiOS.Win.psm1'
        Import-Module $winModulePath -Force -Global
    }

    # Resolving a Windows interpreter is meaningless on Linux, where CI runs
    # pwsh -- there is no pwsh.exe and no %WINDIR%. Assert the real contract on
    # Windows; on Linux only assert the function does not throw.
    It "Should resolve concrete interpreter path avoiding WindowsApps alias" -Skip:(-not $IsWindows) {
        $exe = Get-MiosPowerShellExe
        $exe | Should -Not -BeNullOrEmpty
        ($exe -like '*\WindowsApps\*') | Should -Be $false
    }

    It "Should not throw when no Windows interpreter exists" {
        { Get-MiosPowerShellExe } | Should -Not -Throw
    }
}
