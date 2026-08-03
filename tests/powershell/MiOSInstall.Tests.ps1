# AI-hint: Pester characterization tests for MiOS.Install module suite.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$installModuleDir = Join-Path $scriptDir '../../automation/lib/MiOS.Install'

Describe "MiOS.Install Sub-modules" {
    # Import once in BeforeAll: Pester 5 isolates each It, so modules imported
    # inside one are invisible to the next.
    BeforeAll {
        # Pester 5 runs BeforeAll in a different scope from the
        # discovery-phase top level, so recompute paths here.
        $installModuleDir = Join-Path $PSScriptRoot '../../automation/lib/MiOS.Install'
        $script:installFiles = @(Get-ChildItem -Path $installModuleDir -Filter '*.psm1')
        foreach ($f in $script:installFiles) {
            Import-Module $f.FullName -Force -Global
        }
    }

    It "Should load all sub-modules" {
        $script:installFiles.Count | Should -BeGreaterThan 0
    }

    It "Should return phase name by ID" {
        $phase = Get-MiosInstallerPhaseName 0
        $phase | Should -Be 'Prerequisites'
    }

    It "Should return verb list array" {
        $verbs = Get-MiosVerbList
        ($verbs -contains 'build') | Should -Be $true
    }

    It "Should return existing target dir when sentinel exists" {
        # $scriptDir is discovery-phase and null here; $env:TEMP does not exist
        # on Linux, where CI runs pwsh; and 'cat\autounattend' is not a path
        # there either.
        $common = Join-Path $PSScriptRoot '../../installation/mios-common.ps1'
        . $common
        $tempRoot = [System.IO.Path]::GetTempPath()
        $tempDir = Join-Path $tempRoot ('mios-test-sentinel-' + [Guid]::NewGuid().ToString('N'))
        $sentinelDir = Join-Path $tempDir 'cat/autounattend'
        New-Item -ItemType Directory -Force -Path $sentinelDir | Out-Null
        Set-Content -Path (Join-Path $sentinelDir 'Build-MiOSXboxISO.ps1') -Value '# test sentinel'
        try {
            $res = Ensure-MiosBootstrapRepo -TargetDir $tempDir
            $res | Should -Be $tempDir
        } finally {
            Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
