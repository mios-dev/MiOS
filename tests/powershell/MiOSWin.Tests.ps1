# AI-hint: Pester characterization tests for MiOS.Win.psm1 Windows helper module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$winModulePath = Join-Path $scriptDir '../../automation/lib/MiOS.Win.psm1'

Describe "MiOS.Win.psm1 Module" {
    BeforeAll {
        Import-Module $winModulePath -Force -Global
    }

    It "Should resolve concrete interpreter path avoiding WindowsApps alias" {
        $exe = Get-MiosPowerShellExe
        $exe | Should -Not -BeNullOrEmpty
        ($exe -like '*\WindowsApps\*') | Should -Be $false
    }
}
