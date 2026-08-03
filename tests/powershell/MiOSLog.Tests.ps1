# AI-hint: Pester characterization tests for MiOS.Log.psm1 -- asserts the module loads, exposes its logging functions, and that they execute without throwing.
# AI-related: automation/lib/MiOS.Log.psm1, tests/powershell/run-pester.sh

$here = $PSScriptRoot
$modulePath = Join-Path $here '../../automation/lib/MiOS.Log.psm1'

Describe 'MiOS.Log.psm1 Module' {
    BeforeAll {
        # Pester 5 runs BeforeAll in a different scope from the
        # discovery-phase top level, so recompute paths here.
        $modulePath = Join-Path $PSScriptRoot '../../automation/lib/MiOS.Log.psm1'
        Import-Module $modulePath -Force -Global
    }

    It 'Should load module and expose logging functions' {
        (Get-Command Info).Name | Should -Be 'Info'
        (Get-Command Write-Step).Name | Should -Be 'Write-Step'
    }

    It 'Should execute logging functions cleanly' {
        { Info 'Test cyan' } | Should -Not -Throw
        { Ok 'Test green' } | Should -Not -Throw
        { Warn 'Test yellow' } | Should -Not -Throw
    }
}
