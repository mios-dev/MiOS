# AI-hint: Pester characterization tests for MiOS.Build module suite.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildModuleDir = Join-Path $scriptDir '..\..\automation\lib\MiOS.Build'

Describe "MiOS.Build Sub-modules" {
    It "Should load all sub-modules" {
        $files = Get-ChildItem -Path $buildModuleDir -Filter '*.psm1'
        $files.Count | Should BeGreaterThan 0
        foreach ($f in $files) {
            Import-Module $f.FullName -Force
        }
    }

    It "Should format build spans correctly" {
        $ts = [TimeSpan]::FromMinutes(5) + [TimeSpan]::FromSeconds(30)
        $formatted = Format-BuildSpan $ts
        $formatted | Should Be '05:30'
    }

    It "Should return tagline string" {
        $tagline = Get-MiosBrandingTagline 'Custom OS'
        $tagline | Should Not BeNullOrEmpty
    }
}
