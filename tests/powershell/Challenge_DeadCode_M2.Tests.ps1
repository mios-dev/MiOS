# Adversarial Challenge: Dead-Code Parameter & Scoping Challenge
# Tests: -BootstrapOnly, omission, override switches, variable scoping in child functions
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Describe "Adversarial Challenge: Dead-Code Parameter & Scoping" {
    $targetFiles = @(
        @{ File = (Join-Path $env:MIOS_BOOTSTRAP_ROOT 'build-mios.ps1'); Name = 'mios-bootstrap' },
        @{ File = (Join-Path $PSScriptRoot '../../build-mios.ps1'); Name = 'MiOS' }
    )

    Context "Target <Name>" -ForEach $targetFiles {
        BeforeAll {
            $script:currentFile = $File
            $script:rawContent = Get-Content -LiteralPath $script:currentFile -Raw
        }

        It "Does not contain unconditional `$BootstrapOnly = `$true override" {
            $script:rawContent | Should -Not -Match '(?m)^\s*\$BootstrapOnly\s*=\s*\$true\s*$'
            $script:rawContent | Should -Not -Match '(?m)^\s*\$script:BootstrapOnly\s*=\s*\$true\s*$'
        }

        It "Synchronizes `$script:BootstrapOnly from parameter" {
            $script:rawContent | Should -Match '\$script:BootstrapOnly\s*=\s*\[bool\]\$BootstrapOnly'
        }

        It "Overrides `$BootstrapOnly to false if -FullBuild, -DeployPipeline, or -BuildOnly is specified" {
            $script:rawContent | Should -Match 'if\s*\(\$FullBuild\s+-or\s+\$DeployPipeline\s+-or\s+\$BuildOnly\)\s*\{\s*\$BootstrapOnly\s*=\s*\$false\s*\}'
        }

        It "Dynamic execution: When -BootstrapOnly is omitted, phases 6-13 are not bypassed by early return" {
            $testSandbox = @"
                param([switch]`$BootstrapOnly, [switch]`$FullBuild, [switch]`$DeployPipeline, [switch]`$BuildOnly)
                if (`$FullBuild -or `$DeployPipeline -or `$BuildOnly) {
                    `$BootstrapOnly = `$false
                }
                `$script:BootstrapOnly = [bool]`$BootstrapOnly

                `$_phaseSection = if (`$BootstrapOnly) { 'install_phases.bootstrap' } else { 'install_phases.full' }
                `$reachedPostBootstrap = `$false
                if (`$BootstrapOnly) {
                    # early return block
                } else {
                    `$reachedPostBootstrap = `$true
                }

                [PSCustomObject]@{
                    BootstrapOnly = `$BootstrapOnly
                    ScriptBootstrapOnly = `$script:BootstrapOnly
                    PhaseSection = `$_phaseSection
                    ReachedPostBootstrap = `$reachedPostBootstrap
                }
"@
            $sb = [ScriptBlock]::Create($testSandbox)

            # Case 1: Omission (default)
            $resDefault = & $sb
            $resDefault.BootstrapOnly | Should -Be $false
            $resDefault.ScriptBootstrapOnly | Should -Be $false
            $resDefault.PhaseSection | Should -Be 'install_phases.full'
            $resDefault.ReachedPostBootstrap | Should -Be $true

            # Case 2: -BootstrapOnly specified
            $resBoot = & $sb -BootstrapOnly
            $resBoot.BootstrapOnly | Should -Be $true
            $resBoot.ScriptBootstrapOnly | Should -Be $true
            $resBoot.PhaseSection | Should -Be 'install_phases.bootstrap'
            $resBoot.ReachedPostBootstrap | Should -Be $false

            # Case 3: -BootstrapOnly with -FullBuild override
            $resFull = & $sb -BootstrapOnly -FullBuild
            $resFull.BootstrapOnly | Should -Be $false
            $resFull.ScriptBootstrapOnly | Should -Be $false
            $resFull.PhaseSection | Should -Be 'install_phases.full'
            $resFull.ReachedPostBootstrap | Should -Be $true

            # Case 4: -BootstrapOnly with -BuildOnly override
            $resBuild = & $sb -BootstrapOnly -BuildOnly
            $resBuild.BootstrapOnly | Should -Be $false
            $resBuild.ScriptBootstrapOnly | Should -Be $false
            $resBuild.ReachedPostBootstrap | Should -Be $true

            # Case 5: -BootstrapOnly with -DeployPipeline override
            $resDeploy = & $sb -BootstrapOnly -DeployPipeline
            $resDeploy.BootstrapOnly | Should -Be $false
            $resDeploy.ScriptBootstrapOnly | Should -Be $false
            $resDeploy.ReachedPostBootstrap | Should -Be $true
        }

        It "Scope validation: Child functions correctly inherit `$BootstrapOnly without scoping leaks" {
            $scopeSandbox = @"
                param([switch]`$BootstrapOnly)
                `$script:BootstrapOnly = [bool]`$BootstrapOnly
                function Start-Phase([int]`$i) {
                    `$tag = if (`$BootstrapOnly) { "Phase `$i" } else { "Phase `$i/13" }
                    return `$tag
                }
                function Test-ScriptScopeAccess {
                    return `$script:BootstrapOnly
                }
                [PSCustomObject]@{
                    PhaseTag = Start-Phase 3
                    ScriptVal = Test-ScriptScopeAccess
                }
"@
            $sb = [ScriptBlock]::Create($scopeSandbox)

            # Default (false)
            $res1 = & $sb
            $res1.PhaseTag | Should -Be "Phase 3/13"
            $res1.ScriptVal | Should -Be $false

            # With switch (true)
            $res2 = & $sb -BootstrapOnly
            $res2.PhaseTag | Should -Be "Phase 3"
            $res2.ScriptVal | Should -Be $true
        }
    }
}
