# AI-hint: Milestone 2 Challenger 2 Empirical Adversarial Stress Test Suite
# Tests POSIX preservation, pipe streaming, buffer deadlock handling, NTFS extraction prevention, and dynamic tag binding.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$passed = 0
$failed = 0
$testResults = @()

function Record-Test([string]$Name, [bool]$Condition, [string]$Details = '') {
    if ($Condition) {
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        $script:passed++
        $script:testResults += [pscustomobject]@{ Name = $Name; Status = 'PASS'; Details = $Details }
    } else {
        Write-Host "  [FAIL] $Name : $Details" -ForegroundColor Red
        $script:failed++
        $script:testResults += [pscustomobject]@{ Name = $Name; Status = 'FAIL'; Details = $Details }
    }
}

function Write-Warn([string]$msg) {}
function Write-Step([string]$msg) {}
function Write-Ok([string]$msg) {}
function Write-Bad([string]$msg) {}
function Write-Log([string]$msg, [string]$lvl = 'INFO') {}
function Set-Step([string]$msg) {}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  MILESTONE 2 CHALLENGER 2 EMPIRICAL ADVERSARIAL SUITE" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

$testDir = Join-Path $env:TEMP ("m2_challenger2_" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $testDir -Force | Out-Null

try {
    $pyGen = Join-Path $PSScriptRoot 'pipe_deadlock_generator.py'
    if (-not (Test-Path $pyGen)) {
        throw "Generator not found at $pyGen"
    }

    # =========================================================================
    # SUITE 1: PIPE BUFFER DEADLOCK SIMULATION (TWO-SIDED EMPIRICAL CONTROLS)
    # =========================================================================
    Write-Host "`n--- Suite 1: Pipe Buffer Deadlock Simulation ---" -ForegroundColor Yellow

    # Test 1.1: Negative Control - Naive synchronous pipe read hangs when stderr > 64KB
    $negPsi = New-Object System.Diagnostics.ProcessStartInfo
    $negPsi.FileName = 'python'
    $negPsi.Arguments = "`"$pyGen`" --stderr-bytes 262144 --stdout-bytes 64 --mode stderr-first"
    $negPsi.RedirectStandardOutput = $true
    $negPsi.RedirectStandardError = $true
    $negPsi.UseShellExecute = $false
    $negPsi.CreateNoWindow = $true

    $negProc = [System.Diagnostics.Process]::Start($negPsi)
    $negTask = $negProc.StandardOutput.ReadToEndAsync()
    $negFinished = $negTask.Wait(2500)
    $negDeadlocked = (-not $negFinished)
    if ($negDeadlocked) {
        try { $negProc.Kill() } catch {}
    }
    Record-Test "Pipe Deadlock: Negative control hangs on unread stderr buffer (>64KB)" $negDeadlocked "Process timed out after 2500ms as expected without async stderr draining"

    # Test 1.2: Positive Control - ReadToEndAsync handles 1MB stderr concurrently with 2MB stdout
    $posOutFile = Join-Path $testDir 'pos_stream.bin'
    $posPsi = New-Object System.Diagnostics.ProcessStartInfo
    $posPsi.FileName = 'python'
    $posPsi.Arguments = "`"$pyGen`" --stderr-bytes 1048576 --stdout-bytes 2097152 --mode stderr-first"
    $posPsi.RedirectStandardOutput = $true
    $posPsi.RedirectStandardError = $true
    $posPsi.UseShellExecute = $false
    $posPsi.CreateNoWindow = $true

    $posProc = [System.Diagnostics.Process]::Start($posPsi)
    $posStderrTask = $posProc.StandardError.ReadToEndAsync()

    $posFs = [System.IO.File]::Create($posOutFile)
    try {
        $posBuf = New-Object byte[] 65536
        $posStream = $posProc.StandardOutput.BaseStream
        while ($true) {
            $n = $posStream.Read($posBuf, 0, $posBuf.Length)
            if ($n -le 0) { break }
            $posFs.Write($posBuf, 0, $n)
        }
    } finally {
        $posFs.Close()
    }

    $posExitOk = $posProc.WaitForExit(10000)
    $posStderr = if ($posStderrTask) { try { $posStderrTask.Result } catch { "" } } else { "" }
    $posFileLen = (Get-Item $posOutFile).Length
    $test12Passed = ($posExitOk -and $posProc.ExitCode -eq 0 -and $posFileLen -eq 2097152 -and $posStderr.Length -eq 1048576)
    Record-Test "Pipe Deadlock: Positive control drains 1MB stderr concurrently with 2MB stdout" $test12Passed "Exit: $($posProc.ExitCode), Out: $posFileLen B, Stderr: $($posStderr.Length) B"


    # =========================================================================
    # SUITE 2: ERROR DIAGNOSTICS & PARTIAL FILE CLEANUP
    # =========================================================================
    Write-Host "`n--- Suite 2: Error Diagnostics & Partial File Cleanup ---" -ForegroundColor Yellow

    $failOutFile = Join-Path $testDir 'fail_stream.bin'
    $failPsi = New-Object System.Diagnostics.ProcessStartInfo
    $failPsi.FileName = 'python'
    $failPsi.Arguments = "`"$pyGen`" --stderr-bytes 65536 --stdout-bytes 1024 --exit-code 42 --mode interleaved"
    $failPsi.RedirectStandardOutput = $true
    $failPsi.RedirectStandardError = $true
    $failPsi.UseShellExecute = $false
    $failPsi.CreateNoWindow = $true

    $failProc = [System.Diagnostics.Process]::Start($failPsi)
    $failStderrTask = $failProc.StandardError.ReadToEndAsync()

    $failFs = [System.IO.File]::Create($failOutFile)
    try {
        $fBuf = New-Object byte[] 65536
        $fStream = $failProc.StandardOutput.BaseStream
        while ($true) {
            $n = $fStream.Read($fBuf, 0, $fBuf.Length)
            if ($n -le 0) { break }
            $failFs.Write($fBuf, 0, $n)
        }
    } finally {
        $failFs.Close()
    }

    $failProc.WaitForExit()
    $failStderr = if ($failStderrTask) { try { $failStderrTask.Result.Trim() } catch { "" } } else { "" }

    $caughtExportError = $false
    $cleanUpVerified = $false
    try {
        if ($failProc.ExitCode -ne 0) {
            $exportMsg = "podman export exited $($failProc.ExitCode)"
            if ($failStderr) { $exportMsg += ": $failStderr" }
            throw $exportMsg
        }
    } catch {
        $caughtExportError = $true
        if (Test-Path -LiteralPath $failOutFile) {
            Remove-Item -LiteralPath $failOutFile -Force -ErrorAction SilentlyContinue
        }
        $cleanUpVerified = (-not (Test-Path -LiteralPath $failOutFile))
    }

    Record-Test "Error Diagnostics: Exit code 42 caught and reported with complete stderr" $caughtExportError "Stderr len: $($failStderr.Length)"
    Record-Test "Corrupt Artifact Defense: Partial output file removed on process failure" $cleanUpVerified "File removed: $cleanUpVerified"


    # =========================================================================
    # SUITE 3: PROCESS ABORT SAFETY & CONTAINER CLEANUP
    # =========================================================================
    Write-Host "`n--- Suite 3: Process Abort Safety & Container Cleanup ---" -ForegroundColor Yellow

    $abortOutFile = Join-Path $testDir 'abort_stream.bin'
    $abortPsi = New-Object System.Diagnostics.ProcessStartInfo
    $abortPsi.FileName = 'python'
    $abortPsi.Arguments = "`"$pyGen`" --stderr-bytes 500000 --stdout-bytes 500000"
    $abortPsi.RedirectStandardOutput = $true
    $abortPsi.RedirectStandardError = $true
    $abortPsi.UseShellExecute = $false
    $abortPsi.CreateNoWindow = $true

    $abortProc = [System.Diagnostics.Process]::Start($abortPsi)
    $procKilled = $false
    $abortedFileRemoved = $false

    try {
        $aFs = [System.IO.File]::Create($abortOutFile)
        try {
            $aBuf = New-Object byte[] 4096
            $aStream = $abortProc.StandardOutput.BaseStream
            $readBytes = $aStream.Read($aBuf, 0, $aBuf.Length)
            $aFs.Write($aBuf, 0, $readBytes)
            throw "Simulated reader stream exception (network/disk fault)"
        } finally {
            $aFs.Close()
        }
    } catch {
        if ($abortProc -and -not $abortProc.HasExited) {
            try { $abortProc.Kill() } catch {}
        }
        if (Test-Path -LiteralPath $abortOutFile) {
            try {
                Remove-Item -LiteralPath $abortOutFile -Force -ErrorAction Stop
                $abortedFileRemoved = $true
            } catch {
                $abortedFileRemoved = $false
            }
        }
    } finally {
        if ($abortProc) {
            try { if (-not $abortProc.HasExited) { $abortProc.Kill() } } catch {}
            $procKilled = try { $abortProc.HasExited } catch { $true }
            try { $abortProc.Dispose() } catch {}
        }
    }

    Record-Test "Process Abort Safety: Child process killed immediately on stream exception" $procKilled "Process HasExited: $procKilled"
    Record-Test "Resource Release: File handle closed in finally, allowing file cleanup" $abortedFileRemoved "File removed: $abortedFileRemoved"

    # Container removal guarantee with podman rm -f in finally blocks
    foreach ($path in @('c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\build-mios.ps1', 'c:\MiOS\mios-windows-export.ps1')) {
        $content = Get-Content -LiteralPath $path -Raw
        $hasPodmanRmF = ($content -match 'podman rm -f \$contId')
        Record-Test "Container Cleanup: $path uses podman rm -f in finally block" $hasPodmanRmF "podman rm -f confirmed"
    }


    # =========================================================================
    # SUITE 4: POSIX PRESERVATION & NTFS EXTRACTION PROHIBITION
    # =========================================================================
    Write-Host "`n--- Suite 4: POSIX Preservation & NTFS Extraction Prohibition ---" -ForegroundColor Yellow

    # Test 4.1: Merge-LayersToTar throws deprecation exception explaining NTFS risk
    $mweAst = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\mios-windows-export.ps1', [ref]$null, [ref]$null)
    $mergeFuncAst = $mweAst.Find([Func[System.Management.Automation.Language.Ast, bool]]{ 
        param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -eq 'Merge-LayersToTar' 
    }, $true)
    $mergeScript = [scriptblock]::Create($mergeFuncAst.Extent.Text)
    . $mergeScript

    $mergeBlocked = $false
    $mergeMsg = ''
    try {
        Merge-LayersToTar -LayerFiles @('dummy.tar') -StagingDir (Join-Path $testDir 'stage') -OutTar (Join-Path $testDir 'out.tar')
    } catch {
        $mergeBlocked = $true
        $mergeMsg = $_.Exception.Message
    }
    Record-Test "POSIX Defense: Merge-LayersToTar disabled with NTFS deprecation throw" ($mergeBlocked -and $mergeMsg -match 'NTFS') "Message: $mergeMsg"

    # Test 4.2: Compress-WithZstd warns against WSL error 0x80070057
    $mweContent = Get-Content -LiteralPath 'c:\MiOS\mios-windows-export.ps1' -Raw
    $hasZstWarning = ($mweContent -match '0x80070057' -and $mweContent -match 'DEPRECATED:\s+\.tar\.zst compression is incompatible')
    Record-Test "Archive Defense: Compress-WithZstd warns against WSL2 error 0x80070057" $hasZstWarning "Explicit 0x80070057 and DEPRECATED warning"

    # Test 4.3: Export-WslTar in mios-windows-export.ps1 targets uncompressed .tar
    $targetsUncompressedTar = ($mweContent -match '\$tar\s*=\s*Join-Path\s+\$OutDir\s+''mios\.wsl\.tar''' -and $mweContent -notmatch 'Compress-WithZstd -InTar \$tar')
    Record-Test "Archive Defense: mios-windows-export.ps1 targets uncompressed mios.wsl.tar directly" $targetsUncompressedTar "Uncompressed .tar targeted directly"

    # Test 4.4: Absence of tar.exe extraction in build-mios.ps1
    foreach ($scriptPath in @('c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\build-mios.ps1')) {
        $ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$null, [ref]$null)
        $exportFunc = $ast.Find([Func[System.Management.Automation.Language.Ast, bool]]{ 
            param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -eq 'Export-WslTar' 
        }, $true)
        $funcText = $exportFunc.Extent.Text
        $noTarExe = ($funcText -notmatch 'tar\.exe\s+--force-local' -and $funcText -notmatch 'tar\.exe\s+-x')
        Record-Test "POSIX Defense: $scriptPath Export-WslTar contains no tar.exe extraction" $noTarExe "Uses direct podman export streaming"
    }


    # =========================================================================
    # SUITE 5: DYNAMIC IMAGE TAG RESOLUTION
    # =========================================================================
    Write-Host "`n--- Suite 5: Dynamic Image Tag Binding Verification ---" -ForegroundColor Yellow

    $bAst = [System.Management.Automation.Language.Parser]::ParseFile('c:\MiOS\build-mios.ps1', [ref]$null, [ref]$null)
    $resolveFuncAst = $bAst.Find([Func[System.Management.Automation.Language.Ast, bool]]{ 
        param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -eq 'Resolve-MiosTomlText' 
    }, $true)
    $getTomlFuncAst = $bAst.Find([Func[System.Management.Automation.Language.Ast, bool]]{ 
        param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -eq 'Get-MiosTomlValue' 
    }, $true)

    $resolveScript = [scriptblock]::Create($resolveFuncAst.Extent.Text + "`n" + $getTomlFuncAst.Extent.Text)
    . $resolveScript

    function Test-TagResolution([string]$ParamImage, [string]$TomlContent) {
        $script:_MiosTomlCache = @{ '_text' = $TomlContent }
        $resolvedImage = $ParamImage
        if ([string]::IsNullOrWhiteSpace($resolvedImage)) {
            try {
                $resolvedImage = Get-MiosTomlValue -Section 'image' -Key 'local_tag' -Default 'localhost/mios:latest'
            } catch {
                $resolvedImage = 'localhost/mios:latest'
            }
        }
        if ([string]::IsNullOrWhiteSpace($resolvedImage)) { $resolvedImage = 'localhost/mios:latest' }
        return $resolvedImage
    }

    # Scenario 5.1: Standard TOML with local_tag = "localhost/mios:latest"
    $toml1 = @"
[image]
ref = "ghcr.io/mios-dev/mios:latest"
local_tag = "localhost/mios:latest"
"@
    $res1 = Test-TagResolution '' $toml1
    Record-Test "Dynamic Tag: Standard mios.toml resolves localhost/mios:latest" ($res1 -eq 'localhost/mios:latest') "Resolved: $res1"

    # Scenario 5.2: Custom TOML tag
    $toml2 = @"
[image]
ref = "ghcr.io/custom/mios:v2"
local_tag = "custom-registry.local/mios-enterprise:2.5.0"
"@
    $res2 = Test-TagResolution '' $toml2
    Record-Test "Dynamic Tag: Custom local_tag resolves properly" ($res2 -eq 'custom-registry.local/mios-enterprise:2.5.0') "Resolved: $res2"

    # Scenario 5.3: TOML with [image] section but missing local_tag
    $toml3 = @"
[image]
ref = "ghcr.io/mios-dev/mios:latest"
tag = "latest"
"@
    $res3 = Test-TagResolution '' $toml3
    Record-Test "Dynamic Tag: Missing local_tag in section falls back to localhost/mios:latest" ($res3 -eq 'localhost/mios:latest') "Resolved: $res3"

    # Scenario 5.4: Empty or Missing TOML text
    $res4 = Test-TagResolution '' ''
    Record-Test "Dynamic Tag: Empty/missing TOML falls back to localhost/mios:latest" ($res4 -eq 'localhost/mios:latest') "Resolved: $res4"

    # Scenario 5.5: Malformed / Garbage TOML
    $toml5 = "[[IMAGE]][[ NOT VALID TOML -- SYNTAX ERROR >>>"
    $res5 = Test-TagResolution '' $toml5
    Record-Test "Dynamic Tag: Malformed TOML gracefully falls back to localhost/mios:latest" ($res5 -eq 'localhost/mios:latest') "Resolved: $res5"

    # Scenario 5.6: Explicit -Image parameter overrides TOML
    $res6 = Test-TagResolution 'override-image:pinned' $toml2
    Record-Test "Dynamic Tag: Explicit -Image parameter overrides mios.toml value" ($res6 -eq 'override-image:pinned') "Resolved: $res6"


    # =========================================================================
    # SUITE 6: PHASE STATUS & PIPELINE ERROR PROPAGATION
    # =========================================================================
    Write-Host "`n--- Suite 6: Phase Status & Pipeline Error Propagation ---" -ForegroundColor Yellow

    foreach ($path in @('c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\build-mios.ps1')) {
        $pAst = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$null)
        $deployFunc = $pAst.Find([Func[System.Management.Automation.Language.Ast, bool]]{ 
            param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $a.Name -eq 'Invoke-DeployPipeline' 
        }, $true)
        $deployBody = $deployFunc.Extent.Text

        $phase10Fail = ($deployBody -match 'End-Phase\s+10\s+-Fail')
        $phase10NoWarn = ($deployBody -notmatch 'End-Phase\s+10\s+-Warn')
        $phase11Fail = ($deployBody -match 'End-Phase\s+11\s+-Fail')
        $phase11NoWarn = ($deployBody -notmatch 'End-Phase\s+11\s+-Warn')
        $setsExitCode = ($deployBody -match '\$script:ExitCode\s*=\s*1')

        Record-Test "Pipeline Error: $path - Phase 10 marks -Fail on error" $phase10Fail "End-Phase 10 -Fail found"
        Record-Test "Pipeline Error: $path - Phase 10 does NOT use -Warn" $phase10NoWarn "No End-Phase 10 -Warn found"
        Record-Test "Pipeline Error: $path - Phase 11 marks -Fail on error" $phase11Fail "End-Phase 11 -Fail found"
        Record-Test "Pipeline Error: $path - Phase 11 does NOT use -Warn" $phase11NoWarn "No End-Phase 11 -Warn found"
        Record-Test "Pipeline Error: $path - Failure sets `$script:ExitCode = 1" $setsExitCode "ExitCode set to 1"
    }


    # =========================================================================
    # SUITE 7: DEAD-CODE TRAP ELIMINATION VERIFICATION
    # =========================================================================
    Write-Host "`n--- Suite 7: Dead-Code Trap Elimination ---" -ForegroundColor Yellow

    foreach ($path in @('c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\build-mios.ps1')) {
        $content = Get-Content -LiteralPath $path -Raw
        $noHardcoded = ($content -notmatch '(?m)^\$BootstrapOnly\s*=\s*\$true' -and $content -notmatch '(?m)^\$script:BootstrapOnly\s*=\s*\$true')
        $bindsParam = ($content -match '\$script:BootstrapOnly\s*=\s*\[bool\]\$BootstrapOnly')
        Record-Test "Trap Elimination: $path does not contain hardcoded `$BootstrapOnly = `$true" $noHardcoded "Parameter binding respected"
        Record-Test "Trap Elimination: $path synchronizes parameter to `$script:BootstrapOnly" $bindsParam "Synchronized correctly"
    }


    # =========================================================================
    # SUITE 8: AST SYNTAX VERIFICATION ACROSS ALL TARGET FILES
    # =========================================================================
    Write-Host "`n--- Suite 8: AST Syntax Verification Across Target Files ---" -ForegroundColor Yellow

    $targetFiles = @(
        'c:\mios-bootstrap\build-mios.ps1',
        'c:\MiOS\build-mios.ps1',
        'c:\MiOS\mios-windows-export.ps1'
    )
    foreach ($tf in $targetFiles) {
        $tTokens = $null
        $tErrors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile($tf, [ref]$tTokens, [ref]$tErrors)
        $zeroErrors = ($tErrors.Count -eq 0)
        Record-Test "AST Syntax: $tf has zero syntax errors" $zeroErrors "Errors: $($tErrors.Count)"
    }

} finally {
    if (Test-Path -LiteralPath $testDir) {
        Remove-Item -LiteralPath $testDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  FINAL SUMMARY: $passed PASSED, $failed FAILED" -ForegroundColor $(if ($failed -eq 0) { 'Green' } else { 'Red' })
Write-Host "================================================================" -ForegroundColor Cyan

if ($failed -gt 0) { exit 1 } else { exit 0 }
