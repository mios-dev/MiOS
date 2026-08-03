# AI-hint: Pester characterization tests for MiOS.Install module suite.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$installModuleDir = Join-Path $scriptDir '..\..\automation\lib\MiOS.Install'

Describe "MiOS.Install Sub-modules" {
    It "Should load all sub-modules" {
        $files = Get-ChildItem -Path $installModuleDir -Filter '*.psm1'
        $files.Count | Should BeGreaterThan 0
        foreach ($f in $files) {
            Import-Module $f.FullName -Force
        }
    }

    It "Should return phase name by ID" {
        $phase = Get-MiosInstallerPhaseName 0
        $phase | Should Be 'Prerequisites'
    }

    It "Should return verb list array" {
        $verbs = Get-MiosVerbList
        ($verbs -contains 'build') | Should Be $true
    }
}
