# AI-hint: Pester characterization tests for MiOS.Toml.psm1 TOML reader module.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $scriptDir '..\..\automation\lib\MiOS.Toml.psm1'
Import-Module $modulePath -Force

Describe "MiOS.Toml.psm1 Module" {
    Context "Get-MiosTomlValue resolution" {
        It "Should resolve [ports].ssh" {
            $val = Get-MiosTomlValue 'ports' 'ssh' 22
            $val | Should BeGreaterThan 0
        }

        It "Should resolve [desktop].theme" {
            $val = Get-MiosTomlValue 'desktop' 'theme' 'default'
            $val | Should Not BeNullOrEmpty
        }

        It "Should return default when key is missing" {
            $val = Get-MiosTomlValue 'nonexistent_section' 'nonexistent_key' 9999
            $val | Should Be 9999
        }
    }
}
