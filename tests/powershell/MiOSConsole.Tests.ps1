# AI-hint: Pester characterization tests for MiOS.Console.psm1 console formatting module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$consoleModulePath = Join-Path $scriptDir '../../automation/lib/MiOS.Console.psm1'

Describe "MiOS.Console.psm1 Module" {
    # Top-level Import-Module runs during Pester 5 DISCOVERY, not run; the
    # imported commands are not reliably visible to the It blocks.
    BeforeAll {
        Import-Module $consoleModulePath -Force -Global
    }

    It "Should resolve palette RGB tuples" {
        $pal = Get-MiosPalette
        ($pal.Keys -contains 'accent') | Should -Be $true
        $pal.accent.Count | Should -Be 3
    }

    It "Should format bold text" {
        $b = B "test"
        $b | Should -Match "test"
    }
}
