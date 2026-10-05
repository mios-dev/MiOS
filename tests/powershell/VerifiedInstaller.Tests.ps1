# AI-hint: Proves Windows agent installer downloads reject corrupted bytes and missing SSOT hashes before execution.
Describe 'MiOS verified agent installer' {
    BeforeAll {
        $source = Join-Path $PSScriptRoot '../../usr/share/mios/windows/mios-agent-cli-setup.ps1'
        $ast = [System.Management.Automation.Language.Parser]::ParseFile($source, [ref]$null, [ref]$null)
        foreach ($name in @('Test-SHA256Integrity', 'Save-MiosVerifiedInstaller')) {
            $functionAst = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true)
            . ([scriptblock]::Create($functionAst.Extent.Text))
        }
        $script:payload = [Text.Encoding]::UTF8.GetBytes('verified installer fixture')
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $script:expected = ([BitConverter]::ToString($sha.ComputeHash($script:payload))).Replace('-', '') } finally { $sha.Dispose() }
    }
    BeforeEach {
        Mock Invoke-WebRequest { param($Uri, $OutFile) [IO.File]::WriteAllBytes($OutFile, $script:payload) }
    }
    It 'accepts bytes matching the SSOT checksum' {
        { Save-MiosVerifiedInstaller 'https://example.invalid/installer' (Join-Path $TestDrive 'good.ps1') $script:expected } | Should -Not -Throw
    }
    It 'rejects a different checksum' {
        { Save-MiosVerifiedInstaller 'https://example.invalid/installer' (Join-Path $TestDrive 'bad.ps1') ('0' * 64) } | Should -Throw '*SHA-256 mismatch*'
    }
    It 'rejects missing checksum without downloading' {
        { Save-MiosVerifiedInstaller 'https://example.invalid/installer' (Join-Path $TestDrive 'missing.ps1') '' } | Should -Throw '*missing or invalid*'
        Should -Invoke Invoke-WebRequest -Times 0 -Exactly
    }
}
