# AI-hint: Pester characterization tests for MiOS.Build module suite.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$buildModuleDir = Join-Path $scriptDir '../../automation/lib/MiOS.Build'

Describe "MiOS.Build Sub-modules" {
    # Pester 5 runs each It in its own scope, so a module imported inside one It
    # is invisible to the next -- which is why Format-BuildSpan was reported as
    # "not recognized". Import once, in BeforeAll.
    BeforeAll {
        $script:buildFiles = @(Get-ChildItem -Path $buildModuleDir -Filter '*.psm1')
        foreach ($f in $script:buildFiles) {
            Import-Module $f.FullName -Force -Global
        }
    }

    It "Should load all sub-modules" {
        $script:buildFiles.Count | Should -BeGreaterThan 0
    }

    It "Should format build spans correctly" {
        $ts = [TimeSpan]::FromMinutes(5) + [TimeSpan]::FromSeconds(30)
        $formatted = Format-BuildSpan $ts
        $formatted | Should -Be '05:30'
    }

    It "Should return tagline string" {
        $tagline = Get-MiosBrandingTagline 'Custom OS'
        $tagline | Should -Not -BeNullOrEmpty
    }
}
