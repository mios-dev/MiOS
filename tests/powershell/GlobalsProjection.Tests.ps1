# AI-hint: Pester characterization test for automation/lib/globals.ps1 constants.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$globalsPath = Join-Path $scriptDir '../../automation/lib/globals.ps1'

Describe "globals.ps1 Constant Projection" {
    It "Should parse and load all script-scoped MIOS_* constants" {
        . $globalsPath
        $script:MIOS_VERSION | Should -Not -BeNullOrEmpty
        $script:MIOS_PORT_SSH | Should -BeGreaterThan 0
    }
}
