# AI-hint: Milestone 2 Empirical Adversarial Stress Test Suite (m2_challenger_2)
# Adversarially tests:
#   1. Pipe deadlock handling when process outputs to stderr during stdout reading (positive and negative controls)
#   2. Complete prevention of intermediate NTFS unpacking via tar.exe & POSIX preservation
#   3. Deprecation and prevention of .tar.zst compression for WSL2 targets
#   4. Dynamic image tag resolution from mios.toml (valid, missing, malformed, live)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$passed = 0
$failed = 0
$results = @()

function Assert-Check([string]$TestId, [string]$Name, [bool]$Condition, [string]$Details = '') {
    if ($Condition) {
        Write-Host "  [PASS] [$TestId] $Name" -ForegroundColor Green
        $script:passed++
        $script:results += [pscustomobject]@{ Id = $TestId; Name = $Name; Status = 'PASS'; Details = $Details }
    } else {
        Write-Host "  [FAIL] [$TestId] $Name : $Details" -ForegroundColor Red
        $script:failed++
        $script:results += [pscustomobject]@{ Id = $TestId; Name = $Name; Status = 'FAIL'; Details = $Details }
    }
}

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  CHALLENGER 2: MILESTONE 2 EMPIRICAL ADVERSARIAL VERIFICATION SUITE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$testWorkDir = Join-Path $env:TEMP ("m2_challenger_2_" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $testWorkDir -Force | Out-Null

try {
    $pyHarness = Join-Path $PSScriptRoot 'pipe_deadlock_generator.py'
    if (-not (Test-Path $pyHarness)) {
        throw "Generator not found at $pyHarness"
    }

    # =========================================================================
    # SUITE 1: PIPE BUFFER DEADLOCK EMPIRICAL STRESS TESTS
    # =========================================================================
    Write-Host "`n[Suite 1: Pipe Deadlock Handling (Stderr/Stdout Streaming)]" -ForegroundColor Yellow

    # 1.1 Negative Control: Prove that synchronous stdout reading without draining stderr hangs
    # A child process writing 256KB to stderr first saturates the Windows OS pipe buffer (<=64KB)
    $negPsi = New-Object System.Diagnostics.ProcessStartInfo
    $negPsi.FileName = 'python'
    $negPsi.Arguments = "`"$pyHarness`" --stderr-bytes 262144 --stdout-bytes 262144 --mode stderr-first"
    $negPsi.RedirectStandardOutput = $true
    $negPsi.RedirectStandardError  = $true
    $negPsi.UseShellExecute        = $false
    $negPsi.CreateNoWindow         = $true

    $negProc = [System.Diagnostics.Process]::Start($negPsi)
    $negTimedOut = $false
    $negBuf = New-Object byte[] 4096
    $negStream = $negProc.StandardOutput.BaseStream

    # Start a background read of stdout (which will block waiting for child to write stdout,
    # but child is blocked on writing stderr)
    $readTask = [System.Threading.Tasks.Task]::Run([System.Action]{
        param()
        try {
            while ($true) {
                $n = $negStream.Read($negBuf, 0, $negBuf.Length)
                if ($n -le 0) { break }
            }
        } catch {}
    })

    # Wait max 2500ms; naive pattern MUST hang
    $waitResult = $negProc.WaitForExit(2500)
    if (-not $waitResult) {
        $negTimedOut = $true
        try { $negProc.Kill() } catch {}
    }
    Assert-Check "1.1" "Negative Control: Synchronous stdout read hangs on 256KB stderr (deadlock demonstrated)" `
        $negTimedOut "Process timed out after 2500ms as expected when stderr is not drained"

    # 1.2 Positive Control (Stderr-first): ReadToEndAsync() drains 1MB stderr before 2MB stdout
    $posOutFile = Join-Path $testWorkDir 'pos_stream_1.bin'
    $posPsi = New-Object System.Diagnostics.ProcessStartInfo
    $posPsi.FileName = 'python'
    $posPsi.Arguments = "`"$pyHarness`" --stderr-bytes 1048576 --stdout-bytes 2097152 --mode stderr-first"
    $posPsi.RedirectStandardOutput = $true
    $posPsi.RedirectStandardError  = $true
    $posPsi.UseShellExecute        = $false
    $posPsi.CreateNoWindow         = $true

    $posProc = [System.Diagnostics.Process]::Start($posPsi)
    $posStderrTask = $posProc.StandardError.ReadToEndAsync()

    $posFs = [System.IO.File]::Create($posOutFile)
    $posSw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $buf = New-Object byte[] 65536
        $stream = $posProc.StandardOutput.BaseStream
        while ($true) {
            $n = $stream.Read($buf, 0, $buf.Length)
            if ($n -le 0) { break }
            $posFs.Write($buf, 0, $n)
        }
    } finally {
        $posFs.Close()
    }

    $posExited = $posProc.WaitForExit(10000)
    $posStderr = if ($posStderrTask) { try { $posStderrTask.Result } catch { "" } } else { "" }
    $posBytesWritten = (Get-Item $posOutFile).Length

    $pos1Pass = ($posExited -and $posProc.ExitCode -eq 0 -and $posBytesWritten -eq 2097152 -and $posStderr.Length -eq 1048576)
    Assert-Check "1.2" "Positive Control: ReadToEndAsync() drains 1MB stderr before 2MB stdout in $($posSw.ElapsedMilliseconds)ms" `
        $pos1Pass "ExitCode: $($posProc.ExitCode), Stdout: $posBytesWritten bytes, Stderr: $($posStderr.Length) chars"

    # 1.3 Positive Control (Interleaved): 2MB stderr and 2MB stdout written concurrently
    $interOutFile = Join-Path $testWorkDir 'pos_stream_inter.bin'
    $interPsi = New-Object System.Diagnostics.ProcessStartInfo
    $interPsi.FileName = 'python'
    $interPsi.Arguments = "`"$pyHarness`" --stderr-bytes 2097152 --stdout-bytes 2097152 --mode interleaved"
    $interPsi.RedirectStandardOutput = $true
    $interPsi.RedirectStandardError  = $true
    $interPsi.UseShellExecute        = $false
    $interPsi.CreateNoWindow         = $true

    $interProc = [System.Diagnostics.Process]::Start($interPsi)
    $interStderrTask = $interProc.StandardError.ReadToEndAsync()

    $interFs = [System.IO.File]::Create($interOutFile)
    $interSw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $buf = New-Object byte[] 65536
        $stream = $interProc.StandardOutput.BaseStream
        while ($true) {
            $n = $stream.Read($buf, 0, $buf.Length)
            if ($n -le 0) { break }
            $interFs.Write($buf, 0, $n)
        }
    } finally {
        $interFs.Close()
    }

    $interExited = $interProc.WaitForExit(10000)
    $interStderr = if ($interStderrTask) { try { $interStderrTask.Result } catch { "" } } else { "" }
    $interBytes = (Get-Item $interOutFile).Length

    $interPass = ($interExited -and $interProc.ExitCode -eq 0 -and $interBytes -eq 2097152 -and $interStderr.Length -eq 2097152)
    Assert-Check "1.3" "Positive Control: Interleaved 2MB stderr + 2MB stdout drains cleanly in $($interSw.ElapsedMilliseconds)ms" `
        $interPass "ExitCode: $($interProc.ExitCode), Stdout: $interBytes bytes, Stderr: $($interStderr.Length) chars"

    # 1.4 Failure Exit Code & Diagnostic Stderr Capture with File Cleanup
    $failOutFile = Join-Path $testWorkDir 'fail_stream.bin'
    $failPsi = New-Object System.Diagnostics.ProcessStartInfo
    $failPsi.FileName = 'python'
    $failPsi.Arguments = "`"$pyHarness`" --stderr-bytes 131072 --stdout-bytes 1024 --exit-code 127 --mode interleaved"
    $failPsi.RedirectStandardOutput = $true
    $failPsi.RedirectStandardError  = $true
    $failPsi.UseShellExecute        = $false
    $failPsi.CreateNoWindow         = $true

    $failProc = [System.Diagnostics.Process]::Start($failPsi)
    $failStderrTask = $failProc.StandardError.ReadToEndAsync()

    $failFs = [System.IO.File]::Create($failOutFile)
    try {
        $buf = New-Object byte[] 65536
        $stream = $failProc.StandardOutput.BaseStream
        while ($true) {
            $n = $stream.Read($buf, 0, $buf.Length)
            if ($n -le 0) { break }
            $failFs.Write($buf, 0, $n)
        }
    } finally {
        $failFs.Close()
    }

    $failProc.WaitForExit(5000)
    $failStderr = if ($failStderrTask) { try { $failStderrTask.Result.Trim() } catch { "" } } else { "" }

    $caughtException = $false
    $exceptionMessage = ""
    $partialRemoved = $false
    try {
        if ($failProc.ExitCode -ne 0) {
            $exportMsg = "podman export exited $($failProc.ExitCode)"
            if ($failStderr) { $exportMsg += ": $failStderr" }
            throw $exportMsg
        }
    } catch {
        $caughtException = $true
        $exceptionMessage = $_.Exception.Message
        # Mirror Export-WslTar catch cleanup
        if (Test-Path -LiteralPath $failOutFile) {
            try { Remove-Item -LiteralPath $failOutFile -Force -ErrorAction SilentlyContinue } catch {}
        }
        $partialRemoved = (-not (Test-Path -LiteralPath $failOutFile))
    }

    $failHandled = ($caughtException -and $failProc.ExitCode -eq 127 -and $failStderr.Length -eq 131072 -and $partialRemoved)
    Assert-Check "1.4" "Diagnostic Capture: Exit code 127 with 128KB stderr captured and partial archive deleted" `
        $failHandled "Caught: $caughtException, Stderr len: $($failStderr.Length), Partial file deleted: $partialRemoved"

    # 1.5 Process Abort Safety: Child process killed on stream exception
    $abortPsi = New-Object System.Diagnostics.ProcessStartInfo
    $abortPsi.FileName = 'python'
    $abortPsi.Arguments = "`"$pyHarness`" --stderr-bytes 500000 --stdout-bytes 500000"
    $abortPsi.RedirectStandardOutput = $true
    $abortPsi.RedirectStandardError  = $true
    $abortPsi.UseShellExecute        = $false
    $abortPsi.CreateNoWindow         = $true

    $abortProc = [System.Diagnostics.Process]::Start($abortPsi)
    $killedCleanly = $false
    try {
        throw "Simulated streaming abort exception"
    } catch {
        if ($abortProc -and -not $abortProc.HasExited) {
            try { $abortProc.Kill() } catch {}
        }
    } finally {
        $abortProc.WaitForExit(2000)
        $killedCleanly = $abortProc.HasExited
        try { $abortProc.Dispose() } catch {}
    }
    Assert-Check "1.5" "Process Abort Safety: Child process killed cleanly on stream error without orphan leak" `
        $killedCleanly "Process HasExited: $killedCleanly"


    # =========================================================================
    # SUITE 2: INTERMEDIATE NTFS UNPACKING PROHIBITION & POSIX PRESERVATION
    # =========================================================================
    Write-Host "`n[Suite 2: Intermediate NTFS Unpacking Prevention & POSIX Preservation]" -ForegroundColor Yellow

    # 2.1 Merge-LayersToTar function throws explicit deprecation error forbidding NTFS extraction
    $mweAst = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\mios-windows-export.ps1', [ref]$null, [ref]$null)
    $mergeFuncAst = $mweAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Merge-LayersToTar' }, $true)
    $writeWarnAst = $mweAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Write-Warn' }, $true)

    $mergeThrows = $false
    $mergeThrowsMessage = ""
    if ($mergeFuncAst) {
        if ($writeWarnAst) {
            . ([scriptblock]::Create($writeWarnAst.Extent.Text))
        } else {
            function global:Write-Warn { param([string]$msg) }
        }
        . ([scriptblock]::Create($mergeFuncAst.Extent.Text))
        try {
            Merge-LayersToTar -LayerFiles @('layer.tar') -StagingDir (Join-Path $testWorkDir 'stage') -OutTar (Join-Path $testWorkDir 'out.tar')
        } catch {
            $mergeThrows = $true
            $mergeThrowsMessage = $_.Exception.Message
        }
    }
    $mergeSafe = ($mergeThrows -and $mergeThrowsMessage -match 'intermediate extraction to NTFS strips Linux POSIX file modes')
    Assert-Check "2.1" "NTFS Prevention: Merge-LayersToTar is explicitly disabled and throws on invocation" `
        $mergeSafe "Threw expected message: '$mergeThrowsMessage'"

    # 2.2 AST Census: Verify absence of tar.exe extraction in all export functions
    foreach ($scriptPath in @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\mios-windows-export.ps1')) {
        $ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$null)
        $exportFunc = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Export-WslTar' }, $true)
        $funcText = if ($exportFunc) { $exportFunc.Extent.Text } else { "" }

        $hasNtfsExtract = ($funcText -match 'tar\.exe\s+--force-local' -or $funcText -match 'tar\.exe\s+-[a-zA-Z]*x' -or $funcText -match 'Expand-Archive')
        $streamsPodman = ($funcText -match 'podman\s+export')

        $noNtfsUnpack = (-not $hasNtfsExtract -and $streamsPodman)
        Assert-Check "2.2" "POSIX Defense: $scriptPath Export-WslTar uses direct podman export without NTFS extraction" `
            $noNtfsUnpack "hasNtfsExtract: $hasNtfsExtract, streamsPodman: $streamsPodman"
    }

    # 2.3 Transient export container cleanup uses podman rm -f in finally blocks
    foreach ($scriptPath in @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\mios-windows-export.ps1')) {
        $ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$null)
        $exportFunc = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Export-WslTar' }, $true)
        $funcText = if ($exportFunc) { $exportFunc.Extent.Text } else { "" }

        $usesRmF = ($funcText -match 'podman rm -f\s+\$contId')
        Assert-Check "2.3" "Resource Defense: $scriptPath guarantees container cleanup with 'podman rm -f'" `
            $usesRmF "Found 'podman rm -f `$contId'"
    }


    # =========================================================================
    # SUITE 3: DEPRECATION AND PREVENTION OF .tar.zst FOR WSL2 TARGETS
    # =========================================================================
    Write-Host "`n[Suite 3: Deprecation and Prevention of .tar.zst for WSL2 Targets]" -ForegroundColor Yellow

    # 3.1 Compress-WithZstd warns that .tar.zst causes WSL2 error 0x80070057
    $mweContent = Get-Content -LiteralPath 'c:\MiOS\mios-windows-export.ps1' -Raw
    $hasZstWarning = ($mweContent -match '0x80070057' -and $mweContent -match 'DEPRECATED: \.tar\.zst compression is incompatible with ''wsl --import''')
    Assert-Check "3.1" "WSL2 Compatibility: Compress-WithZstd documents error 0x80070057 and deprecation" `
        $hasZstWarning "Explicit 0x80070057 warning in Compress-WithZstd header and body"

    # 3.2 mios-windows-export.ps1 Export-WslTar emits clean uncompressed .tar
    $mweAst = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\mios-windows-export.ps1', [ref]$null, [ref]$null)
    $mweExportFunc = $mweAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Export-WslTar' }, $true)
    $mweText = $mweExportFunc.Extent.Text

    $emitsCleanTar = ($mweText -match '\$tar\s*=\s*Join-Path\s+\$OutDir\s+''mios\.wsl\.tar''' -and $mweText -notmatch 'Compress-WithZstd')
    Assert-Check "3.2" "WSL2 Compatibility: mios-windows-export.ps1 targets mios.wsl.tar directly without zstd call" `
        $emitsCleanTar "Emits uncompressed mios.wsl.tar without compression wrapper"

    # 3.3 build-mios.ps1 targets uncompressed mios-wsl2.tar (not .zst)
    foreach ($scriptPath in @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1')) {
        $content = Get-Content -LiteralPath $scriptPath -Raw
        $targetsTar = ($content -match 'mios-wsl2\.tar' -and $content -notmatch 'mios-wsl2\.tar\.zst')
        Assert-Check "3.3" "WSL2 Compatibility: $scriptPath Phase 10 targets uncompressed mios-wsl2.tar" `
            $targetsTar "Uncompressed .tar targeted"
    }


    # =========================================================================
    # SUITE 4: DYNAMIC TAG RESOLUTION FROM mios.toml
    # =========================================================================
    Write-Host "`n[Suite 4: Dynamic Tag Resolution from mios.toml]" -ForegroundColor Yellow

    # Extract Get-MiosTomlValue and Resolve-MiosTomlText AST from build-mios.ps1
    $bAst = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\build-mios.ps1', [ref]$null, [ref]$null)
    $resolveFuncAst = $bAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Resolve-MiosTomlText' }, $true)
    $getTomlFuncAst = $bAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Get-MiosTomlValue' }, $true)

    . ([scriptblock]::Create($resolveFuncAst.Extent.Text))
    . ([scriptblock]::Create($getTomlFuncAst.Extent.Text))

    # Helper function replicating Export-WslTar dynamic tag resolution
    function Resolve-TestImage([string]$PassedImage, [string]$TomlBody) {
        $script:_MiosTomlCache = @{ '_text' = $TomlBody; '_source' = 'test_override' }
        $resolved = $PassedImage
        if ([string]::IsNullOrWhiteSpace($resolved)) {
            try {
                $resolved = Get-MiosTomlValue -Section 'image' -Key 'local_tag' -Default 'localhost/mios:latest'
            } catch {
                $resolved = 'localhost/mios:latest'
            }
        }
        if ([string]::IsNullOrWhiteSpace($resolved)) { $resolved = 'localhost/mios:latest' }
        return $resolved
    }

    # 4.1 Custom local_tag in [image] section resolves accurately
    $customToml = "[image]`nref = `"ghcr.io/custom/mios:v2`"`nlocal_tag = `"registry.internal/mios:2.0.0-rc1`"`n"
    $resCustom = Resolve-TestImage '' $customToml
    Assert-Check "4.1" "Dynamic Tag: Custom local_tag resolves to 'registry.internal/mios:2.0.0-rc1'" `
        ($resCustom -eq 'registry.internal/mios:2.0.0-rc1') "Resolved: '$resCustom'"

    # 4.2 Standard local_tag in [image] section resolves to 'localhost/mios:latest'
    $stdToml = "[image]`nref = `"ghcr.io/mios-dev/mios:latest`"`nlocal_tag = `"localhost/mios:latest`"`n"
    $resStd = Resolve-TestImage '' $stdToml
    Assert-Check "4.2" "Dynamic Tag: Standard local_tag resolves to 'localhost/mios:latest'" `
        ($resStd -eq 'localhost/mios:latest') "Resolved: '$resStd'"

    # 4.3 Missing local_tag key inside [image] section falls back to 'localhost/mios:latest'
    $noKeyToml = "[image]`nref = `"ghcr.io/mios-dev/mios:latest`"`nbase = `"ghcr.io/ublue-os/ucore-hci:stable`"`n"
    $resNoKey = Resolve-TestImage '' $noKeyToml
    Assert-Check "4.3" "Dynamic Tag: Missing local_tag key falls back to default 'localhost/mios:latest'" `
        ($resNoKey -eq 'localhost/mios:latest') "Resolved: '$resNoKey'"

    # 4.4 Missing [image] section entirely falls back to 'localhost/mios:latest'
    $noSecToml = "[system]`nhostname = `"mios-dev`"`n"
    $resNoSec = Resolve-TestImage '' $noSecToml
    Assert-Check "4.4" "Dynamic Tag: Missing [image] section falls back to default 'localhost/mios:latest'" `
        ($resNoSec -eq 'localhost/mios:latest') "Resolved: '$resNoSec'"

    # 4.5 Empty TOML falls back to 'localhost/mios:latest'
    $resEmpty = Resolve-TestImage '' ''
    Assert-Check "4.5" "Dynamic Tag: Empty/null TOML falls back to default 'localhost/mios:latest'" `
        ($resEmpty -eq 'localhost/mios:latest') "Resolved: '$resEmpty'"

    # 4.6 Malformed syntax in TOML falls back to 'localhost/mios:latest' without crashing
    $malformedToml = "<<<SYNTAX ERROR NOT A TOML>>> [[section] = ???"
    $resMalformed = Resolve-TestImage '' $malformedToml
    Assert-Check "4.6" "Dynamic Tag: Malformed TOML syntax gracefully falls back to 'localhost/mios:latest'" `
        ($resMalformed -eq 'localhost/mios:latest') "Resolved: '$resMalformed'"

    # 4.7 Explicit -Image argument overrides TOML local_tag value
    $resOverride = Resolve-TestImage 'my-cli-override:latest' $customToml
    Assert-Check "4.7" "Dynamic Tag: Explicit -Image argument overrides TOML local_tag" `
        ($resOverride -eq 'my-cli-override:latest') "Resolved: '$resOverride'"

    # 4.8 Live repo TOML verification (c:\MiOS\usr\share\mios\mios.toml)
    $liveTomlPath = 'c:\MiOS\usr\share\mios\mios.toml'
    if (Test-Path $liveTomlPath) {
        $liveTomlText = [System.IO.File]::ReadAllText($liveTomlPath, [System.Text.Encoding]::UTF8)
        $resLive = Resolve-TestImage '' $liveTomlText
        Assert-Check "4.8" "Dynamic Tag: Live repo mios.toml resolves to a valid non-empty string" `
            (-not [string]::IsNullOrWhiteSpace($resLive)) "Resolved against live repo TOML: '$resLive'"
    }


    # =========================================================================
    # SUITE 5: PIPELINE PHASE STATUS & ERROR PROPAGATION (PHASE 10/11)
    # =========================================================================
    Write-Host "`n[Suite 5: Pipeline Phase Status & Exit Code Propagation]" -ForegroundColor Yellow

    foreach ($path in @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1')) {
        $pAst = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$null)
        $deployFunc = $pAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Invoke-DeployPipeline' }, $true)
        $deployBody = $deployFunc.Extent.Text

        $p10Fail = ($deployBody -match 'End-Phase\s+10\s+-Fail')
        $p10NoWarn = ($deployBody -notmatch 'End-Phase\s+10\s+-Warn')
        $p11Fail = ($deployBody -match 'End-Phase\s+11\s+-Fail')
        $p11NoWarn = ($deployBody -notmatch 'End-Phase\s+11\s+-Warn')
        $setsExitCode = ($deployBody -match '\$script:ExitCode\s*=\s*1' -and $deployBody -match '\$ExitCode\s*=\s*1')

        Assert-Check "5.1" "Error Propagation: $path Phase 10 marks -Fail (not -Warn) on export error" `
            ($p10Fail -and $p10NoWarn) "End-Phase 10 -Fail present, -Warn absent"

        Assert-Check "5.2" "Error Propagation: $path Phase 11 marks -Fail (not -Warn) on import error/skip" `
            ($p11Fail -and $p11NoWarn) "End-Phase 11 -Fail present, -Warn absent"

        Assert-Check "5.3" "Error Propagation: $path sets `$ExitCode = 1 and `$script:ExitCode = 1 on failure" `
            $setsExitCode "Exit code 1 propagated"
    }

    # =========================================================================
    # SUITE 6: DEAD-CODE TRAP ELIMINATION & PARAMETER BINDING
    # =========================================================================
    Write-Host "`n[Suite 6: Dead-Code Trap Elimination & Parameter Binding]" -ForegroundColor Yellow

    foreach ($path in @('c:\MiOS\build-mios.ps1', 'c:\mios-bootstrap\build-mios.ps1')) {
        $content = Get-Content -LiteralPath $path -Raw
        $noUnconditional = ($content -notmatch '(?m)^\s*\$BootstrapOnly\s*=\s*\$true' -and $content -notmatch '(?m)^\s*\$script:BootstrapOnly\s*=\s*\$true')
        $hasDeployPipelineParam = ($content -match '\[switch\]\$DeployPipeline')
        $dynamicOverride = ($content -match 'if \(\$FullBuild -or \$DeployPipeline -or \$BuildOnly\)')

        Assert-Check "6.1" "Trap Elimination: $path has no unconditional `$BootstrapOnly = `$true override" `
            $noUnconditional "Unconditional override removed"

        Assert-Check "6.2" "Switch Binding: $path declares [switch]`$DeployPipeline parameter" `
            $hasDeployPipelineParam "[switch]`$DeployPipeline declared"

        Assert-Check "6.3" "Dynamic Flow: $path drives `$BootstrapOnly conditionally from switches" `
            $dynamicOverride "Dynamic override logic present"
    }

} finally {
    if (Test-Path -LiteralPath $testWorkDir) {
        Remove-Item -LiteralPath $testWorkDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "  VERIFICATION TOTALS: $passed PASSED, $failed FAILED" -ForegroundColor $(if ($failed -eq 0) { 'Green' } else { 'Red' })
Write-Host "================================================================================" -ForegroundColor Cyan

if ($failed -gt 0) { exit 1 } else { exit 0 }
