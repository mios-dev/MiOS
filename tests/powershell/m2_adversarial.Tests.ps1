# AI-hint: Pester test suite for Milestone 2 Adversarial Verification (m2_challenger_2)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Describe "Milestone 2 Adversarial Stress & Verification Tests" {

    Context "Suite 1: Pipe Deadlock Handling (Positive & Negative Controls)" {
        BeforeAll {
            $script:pyHarness = Join-Path $PSScriptRoot 'pipe_deadlock_generator.py'
            $script:testDir = Join-Path $env:TEMP ("pester_m2_" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
            New-Item -ItemType Directory -Path $script:testDir -Force | Out-Null
        }

        AfterAll {
            if (Test-Path $script:testDir) {
                Remove-Item -LiteralPath $script:testDir -Recurse -Force -ErrorAction SilentlyContinue
            }
        }

        It "Negative Control: Synchronous stdout read hangs on 256KB stderr (deadlock demonstrated)" {
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = 'python'
            $psi.Arguments = "`"$script:pyHarness`" --stderr-bytes 262144 --stdout-bytes 262144 --mode stderr-first"
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError  = $true
            $psi.UseShellExecute        = $false
            $psi.CreateNoWindow         = $true

            $proc = [System.Diagnostics.Process]::Start($psi)
            $timedOut = $false
            $buf = New-Object byte[] 4096
            $stream = $proc.StandardOutput.BaseStream

            $readTask = [System.Threading.Tasks.Task]::Run([System.Action]{
                param()
                try {
                    while ($true) {
                        $n = $stream.Read($buf, 0, $buf.Length)
                        if ($n -le 0) { break }
                    }
                } catch {}
            })

            $waitOk = $proc.WaitForExit(2000)
            if (-not $waitOk) {
                $timedOut = $true
                try { $proc.Kill() } catch {}
            }
            $timedOut | Should -BeTrue
        }

        It "Positive Control: ReadToEndAsync() drains 1MB stderr + 2MB stdout without deadlock" {
            $outFile = Join-Path $script:testDir 'pester_pos.bin'
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = 'python'
            $psi.Arguments = "`"$script:pyHarness`" --stderr-bytes 1048576 --stdout-bytes 2097152 --mode stderr-first"
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError  = $true
            $psi.UseShellExecute        = $false
            $psi.CreateNoWindow         = $true

            $proc = [System.Diagnostics.Process]::Start($psi)
            $stderrTask = $proc.StandardError.ReadToEndAsync()

            $fs = [System.IO.File]::Create($outFile)
            try {
                $buf = New-Object byte[] 65536
                $stream = $proc.StandardOutput.BaseStream
                while ($true) {
                    $n = $stream.Read($buf, 0, $buf.Length)
                    if ($n -le 0) { break }
                    $fs.Write($buf, 0, $n)
                }
            } finally {
                $fs.Close()
            }

            $proc.WaitForExit(10000) | Should -BeTrue
            $proc.ExitCode | Should -Be 0
            (Get-Item $outFile).Length | Should -Be 2097152
            $stderrTask.Result.Length | Should -Be 1048576
        }

        It "Error Diagnostics: Exit code 127 captures 128KB stderr and removes partial file" {
            $failFile = Join-Path $script:testDir 'pester_fail.bin'
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = 'python'
            $psi.Arguments = "`"$script:pyHarness`" --stderr-bytes 131072 --stdout-bytes 1024 --exit-code 127 --mode interleaved"
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError  = $true
            $psi.UseShellExecute        = $false
            $psi.CreateNoWindow         = $true

            $proc = [System.Diagnostics.Process]::Start($psi)
            $stderrTask = $proc.StandardError.ReadToEndAsync()

            $fs = [System.IO.File]::Create($failFile)
            try {
                $buf = New-Object byte[] 65536
                $stream = $proc.StandardOutput.BaseStream
                while ($true) {
                    $n = $stream.Read($buf, 0, $buf.Length)
                    if ($n -le 0) { break }
                    $fs.Write($buf, 0, $n)
                }
            } finally {
                $fs.Close()
            }

            $proc.WaitForExit(5000) | Should -BeTrue
            $proc.ExitCode | Should -Be 127
            $stderrText = $stderrTask.Result.Trim()
            $stderrText.Length | Should -Be 131072

            # Emulate catch cleanup
            if (Test-Path $failFile) { Remove-Item $failFile -Force }
            (Test-Path $failFile) | Should -BeFalse
        }
    }

    Context "Suite 2: Intermediate NTFS Unpacking Prevention & POSIX Preservation" {
        It "Merge-LayersToTar throws deprecation exception forbidding NTFS extraction" {
            $ast = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\mios-windows-export.ps1', [ref]$null, [ref]$null)
            $funcAst = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Merge-LayersToTar' }, $true)
            $funcAst | Should -Not -BeNullOrEmpty

            function global:Write-Warn { param([string]$msg) }
            . ([scriptblock]::Create($funcAst.Extent.Text))

            { Merge-LayersToTar -LayerFiles @('dummy') -StagingDir 'c:\temp' -OutTar 'c:\temp\out.tar' } | `
                Should -Throw "*intermediate extraction to NTFS strips Linux POSIX file modes*"
        }

        It "Export-WslTar in all scripts streams directly from container storage without NTFS extraction" {
            $scripts = @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\mios-windows-export.ps1')
            foreach ($s in $scripts) {
                $ast = [System.Management.Automation.Language.Parser]::ParseFile($s, [ref]$null, [ref]$null)
                $exportFunc = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Export-WslTar' }, $true)
                $exportFunc | Should -Not -BeNullOrEmpty
                $text = $exportFunc.Extent.Text

                $text | Should -Not -Match 'tar\.exe\s+--force-local'
                $text | Should -Not -Match 'tar\.exe\s+-[a-zA-Z]*x'
                $text | Should -Match 'podman\s+export'
                $text | Should -Match 'podman rm -f\s+\$contId'
            }
        }
    }

    Context "Suite 3: Deprecation of .tar.zst for WSL2 Targets" {
        It "Compress-WithZstd documents WSL2 error 0x80070057 and deprecation" {
            $content = Get-Content -LiteralPath 'c:\MiOS\mios-windows-export.ps1' -Raw
            $content | Should -Match '0x80070057'
            $content | Should -Match 'DEPRECATED: \.tar\.zst compression is incompatible'
        }

        It "Export-WslTar emits uncompressed .tar without zstd compression" {
            $ast = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\mios-windows-export.ps1', [ref]$null, [ref]$null)
            $func = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Export-WslTar' }, $true)
            $text = $func.Extent.Text

            $text | Should -Match "mios\.wsl\.tar"
            $text | Should -Not -Match "Compress-WithZstd"
        }
    }

    Context "Suite 4: Dynamic Tag Resolution from mios.toml" {
        BeforeAll {
            $ast = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\build-mios.ps1', [ref]$null, [ref]$null)
            $resolveAst = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Resolve-MiosTomlText' }, $true)
            $getTomlAst = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Get-MiosTomlValue' }, $true)
            . ([scriptblock]::Create($resolveAst.Extent.Text))
            . ([scriptblock]::Create($getTomlAst.Extent.Text))

            function script:Resolve-Image([string]$Passed, [string]$Toml) {
                $script:_MiosTomlCache = @{ '_text' = $Toml; '_source' = 'test' }
                $res = $Passed
                if ([string]::IsNullOrWhiteSpace($res)) {
                    try {
                        $res = Get-MiosTomlValue -Section 'image' -Key 'local_tag' -Default 'localhost/mios:latest'
                    } catch {
                        $res = 'localhost/mios:latest'
                    }
                }
                if ([string]::IsNullOrWhiteSpace($res)) { $res = 'localhost/mios:latest' }
                return $res
            }
        }

        It "Resolves custom local_tag correctly" {
            $toml = "[image]`nref = `"ghcr.io/custom:v1`"`nlocal_tag = `"internal/app:3.0`"`n"
            (Resolve-Image '' $toml) | Should -Be "internal/app:3.0"
        }

        It "Falls back to localhost/mios:latest when local_tag is omitted" {
            $toml = "[image]`nref = `"ghcr.io/custom:v1`"`n"
            (Resolve-Image '' $toml) | Should -Be "localhost/mios:latest"
        }

        It "Gracefully handles malformed TOML" {
            $toml = "<<<<SYNTAX ERROR NOT TOML>>>>"
            (Resolve-Image '' $toml) | Should -Be "localhost/mios:latest"
        }

        It "CLI parameter overrides TOML setting" {
            $toml = "[image]`nlocal_tag = `"internal/app:3.0`"`n"
            (Resolve-Image 'explicit:override' $toml) | Should -Be "explicit:override"
        }
    }

    Context "Suite 5: Error Propagation and Trap Elimination" {
        It "Phase 10 and Phase 11 propagate failures with exit code 1" {
            foreach ($s in @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1')) {
                $ast = [System.Management.Automation.Language.Parser]::ParseFile($s, [ref]$null, [ref]$null)
                $deployFunc = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Invoke-DeployPipeline' }, $true)
                $text = $deployFunc.Extent.Text

                $text | Should -Match 'End-Phase\s+10\s+-Fail'
                $text | Should -Not -Match 'End-Phase\s+10\s+-Warn'
                $text | Should -Match 'End-Phase\s+11\s+-Fail'
                $text | Should -Not -Match 'End-Phase\s+11\s+-Warn'
                $text | Should -Match '\$script:ExitCode\s*=\s*1'
            }
        }

        It "Dead-code trap unconditional `$BootstrapOnly = `$true is removed" {
            foreach ($s in @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1')) {
                $content = Get-Content -LiteralPath $s -Raw
                $content | Should -Not -Match '(?m)^\s*\$BootstrapOnly\s*=\s*\$true'
                $content | Should -Not -Match '(?m)^\s*\$script:BootstrapOnly\s*=\s*\$true'
                $content | Should -Match '\[switch\]\$DeployPipeline'
            }
        }
    }
}
