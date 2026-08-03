$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $here '..\..\automation\lib\MiOS.Log.psm1'

Describe 'MiOS.Log.psm1 Module' {
    It 'Should load module and expose logging functions' {
        Import-Module $modulePath -Force
        (Get-Command Info).Name | Should Be 'Info'
        (Get-Command Write-Step).Name | Should Be 'Write-Step'
    }

    It 'Should execute logging functions cleanly' {
        Import-Module $modulePath -Force
        { Info 'Test cyan' } | Should Not Throw
        { Ok 'Test green' } | Should Not Throw
        { Warn 'Test yellow' } | Should Not Throw
    }
}
