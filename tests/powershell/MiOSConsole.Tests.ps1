# AI-hint: Pester characterization tests for MiOS.Console.psm1 console formatting module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$consoleModulePath = Join-Path $scriptDir '..\..\automation\lib\MiOS.Console.psm1'
Import-Module $consoleModulePath -Force

Describe "MiOS.Console.psm1 Module" {
    It "Should resolve palette RGB tuples" {
        $pal = Get-MiosPalette
        ($pal.Keys -contains 'accent') | Should Be $true
        $pal.accent.Count | Should Be 3
    }

    It "Should format bold text" {
        $b = B "test"
        $b | Should Match "test"
    }
}
