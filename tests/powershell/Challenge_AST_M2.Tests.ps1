# Adversarial Challenge: AST Syntax and Parsing Ambiguity Stress Test
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Describe "Adversarial Challenge: AST Syntax Validation" {
    $targetFiles = @(
        @{ File = 'c:\mios-bootstrap\build-mios.ps1'; Name = 'c:\mios-bootstrap\build-mios.ps1' },
        @{ File = 'c:\MiOS\build-mios.ps1'; Name = 'c:\MiOS\build-mios.ps1' },
        @{ File = 'c:\MiOS\mios-windows-export.ps1'; Name = 'c:\MiOS\mios-windows-export.ps1' }
    )

    Context "ParseFile on <Name>" -ForEach $targetFiles {
        BeforeAll {
            $script:currentFile = $_.File
            $script:tokens = $null
            $script:errors = $null
            $script:ast = [System.Management.Automation.Language.Parser]::ParseFile(
                $script:currentFile,
                [ref]$script:tokens,
                [ref]$script:errors
            )
        }

        It "Parses with zero syntax errors" {
            $script:errors.Count | Should -Be 0
        }

        It "Has valid Root ScriptBlockAst without null body" {
            $script:ast | Should -Not -BeNullOrEmpty
            $script:ast.EndBlock | Should -Not -BeNullOrEmpty
        }

        It "Contains no unclosed string interpolation or subexpression parsing errors" {
            $parseErrors = $script:ast.FindAll({
                $args[0] -is [System.Management.Automation.Language.ErrorStatementAst] -or
                $args[0] -is [System.Management.Automation.Language.ErrorExpressionAst]
            }, $true)
            $parseErrors.Count | Should -Be 0
        }
    }
}
