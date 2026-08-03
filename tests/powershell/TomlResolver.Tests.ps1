# AI-hint: Pester characterization tests for MiOS.Toml.psm1 TOML reader module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$modulePath = Join-Path $scriptDir '../../automation/lib/MiOS.Toml.psm1'

Describe "MiOS.Toml.psm1 Module" {
    BeforeAll {
        # Pester 5 runs BeforeAll in a different scope from the
        # discovery-phase top level, so recompute paths here.
        $modulePath = Join-Path $PSScriptRoot '../../automation/lib/MiOS.Toml.psm1'
        Import-Module $modulePath -Force -Global
        # The resolver must find the repo's SSOT when no MiOS host install
        # exists (CI runs pwsh on a bare Linux runner).
        $env:MIOS_TOML = (Resolve-Path (Join-Path $PSScriptRoot '../../usr/share/mios/mios.toml')).Path
    }

    Context "Get-MiosTomlValue resolution" {
        It "Should resolve [ports].ssh" {
            $val = Get-MiosTomlValue 'ports' 'ssh' 22
            $val | Should -BeGreaterThan 0
        }

        It "Should resolve [desktop].theme" {
            $val = Get-MiosTomlValue 'desktop' 'theme' 'default'
            $val | Should -Not -BeNullOrEmpty
        }

        It "Should return default when key is missing" {
            $val = Get-MiosTomlValue 'nonexistent_section' 'nonexistent_key' 9999
            $val | Should -Be 9999
        }
    }
}
