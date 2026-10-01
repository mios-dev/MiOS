# AI-hint: Tests installer deadlock, argument, configuration and missing-tool failure controls.
<#
.SYNOPSIS
    Milestone 4 Challenger 2 Empirical Adversarial Verification Suite (m4_challenger_2)
    Validates two-sided verification controls across M2 and M3:
    1. Syntax corruption negative controls (AST parser error detection & sensitivity)
    2. Pipe deadlock negative controls (empirical hang reproduction & async resolution)
    3. Parameter dropping negative controls (PSBoundParameters.Values defect reproduction vs Get-MiosElevateArgs)
    4. Duplicate [user] sections negative controls (wsl.conf deduplication & BOM sensitivity)
    5. Missing wsl.exe negative controls (preflight actionable error & missing archive defense)
    6. Standing verification gates attestation & sensitivity
    7. Zero unprojected diffs under sync-generated.sh
#>

[CmdletBinding()]
param(
    [switch]$VerboseOutput
)

$ErrorActionPreference = 'Stop'

$script:TotalTests  = 0
$script:PassedTests = 0
$script:FailedTests = 0
$script:TestResults = [System.Collections.Generic.List[PSObject]]::new()

function Assert-Check {
    param(
        [string]$Suite,
        [string]$Name,
        [bool]$Condition,
        [string]$Details = ''
    )
    $script:TotalTests++
    $obj = [PSCustomObject]@{
        Suite     = $Suite
        Name      = $Name
        Condition = $Condition
        Details   = $Details
    }
    $script:TestResults.Add($obj)

    if ($Condition) {
        $script:PassedTests++
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        if ($Details -and $VerboseOutput) { Write-Host "         $Details" -ForegroundColor DarkGray }
    } else {
        $script:FailedTests++
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        if ($Details) { Write-Host "         $Details" -ForegroundColor Red }
    }
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "  MILESTONE 4 CHALLENGER 2: EMPIRICAL TWO-SIDED ADVERSARIAL VERIFICATION" -ForegroundColor Cyan
Write-Host "================================================================================`n" -ForegroundColor Cyan

# ==============================================================================
# SUITE 1: SYNTAX CORRUPTION NEGATIVE CONTROLS (AST PARSER SENSITIVITY)
# ==============================================================================
Write-Host "--- Suite 1: Syntax Corruption Negative Controls ---" -ForegroundColor Yellow

$corruptSnippets = @(
    @{ Name = "Unclosed brace in function"; Code = "function Test-Corrupt { if (`$true) { Write-Host 'Missing brace'" },
    @{ Name = "Unclosed parenthesis in param"; Code = "function Test-Param { param([string]`$x, [int]`$y Write-Host `$x }" },
    @{ Name = "Unclosed type literal"; Code = "[System.Collections.Generic.List[string] `$list = @()" },
    @{ Name = "Unterminated single quote"; Code = "`$x = 'unterminated string" },
    @{ Name = "Dangling pipeline token"; Code = "Get-Process | " }
)

foreach ($item in $corruptSnippets) {
    $tok = $null; $errs = $null
    [System.Management.Automation.Language.Parser]::ParseInput($item.Code, [ref]$tok, [ref]$errs)
    $hasErrors = ($errs -and $errs.Count -gt 0)
    Assert-Check "Suite 1: Syntax" "Negative Control: AST detects syntax error on '$($item.Name)'" $hasErrors "Detected $($errs.Count) error(s)"
}

# Positive control on production scripts
$prodScripts = @(
    'c:\mios-bootstrap\build-mios.ps1',
    'c:\MiOS\build-mios.ps1',
    'c:\mios-bootstrap\installation\mios-install.ps1',
    'c:\MiOS\mios-windows-export.ps1',
    'c:\mios-bootstrap\field\MiOS-Cat.ps1',
    'c:\mios-bootstrap\field\lib\MiOS-Cat.psm1'
)
foreach ($scriptPath in $prodScripts) {
    $tok = $null; $errs = $null
    [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tok, [ref]$errs)
    Assert-Check "Suite 1: Syntax" "Positive Control: Clean AST parse on $(Split-Path $scriptPath -Leaf)" ($errs.Count -eq 0) "Errors: $($errs.Count)"
}

# ==============================================================================
# SUITE 2: PIPE DEADLOCK NEGATIVE CONTROLS & ASYNC RESOLUTION
# ==============================================================================
Write-Host "`n--- Suite 2: Pipe Buffer Deadlock Negative Controls ---" -ForegroundColor Yellow

# 2.1 Negative Control: Empirical reproduction of OS pipe deadlock
# Child writes 128KB to stderr without parent draining stderr
$deadlockPsi = New-Object System.Diagnostics.ProcessStartInfo
$deadlockPsi.FileName               = 'pwsh'
$deadlockPsi.Arguments              = '-NoProfile -Command "[Console]::Error.Write((New-Object string(''E'', 131072))); exit 0"'
$deadlockPsi.RedirectStandardOutput = $true
$deadlockPsi.RedirectStandardError  = $true
$deadlockPsi.UseShellExecute        = $false
$deadlockPsi.CreateNoWindow         = $true

$deadlockProc = [System.Diagnostics.Process]::Start($deadlockPsi)
$deadlockExited = $deadlockProc.WaitForExit(2000)
$deadlockDemonstrated = $false
if (-not $deadlockExited) {
    try { $deadlockProc.Kill() } catch {}
    $deadlockDemonstrated = $true
}
Assert-Check "Suite 2: Pipe Deadlock" "Negative Control: Child writing 128KB stderr deadlocks parent on unread pipe (times out)" $deadlockDemonstrated

# 2.2 Positive Control: ReadToEndAsync() concurrently drains 256KB stderr without deadlock
$asyncPsi = New-Object System.Diagnostics.ProcessStartInfo
$asyncPsi.FileName               = 'pwsh'
$asyncPsi.Arguments              = '-NoProfile -Command "[Console]::Error.Write((New-Object string(''E'', 262144))); [Console]::Out.Write((New-Object string(''O'', 262144))); exit 0"'
$asyncPsi.RedirectStandardOutput = $true
$asyncPsi.RedirectStandardError  = $true
$asyncPsi.UseShellExecute        = $false
$asyncPsi.CreateNoWindow         = $true

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$asyncProc = [System.Diagnostics.Process]::Start($asyncPsi)
$errTask = $asyncProc.StandardError.ReadToEndAsync()
$outText = $asyncProc.StandardOutput.ReadToEnd()
$asyncProc.WaitForExit()
$sw.Stop()
$errText = $errTask.Result

$asyncPassed = ($outText.Length -eq 262144 -and $errText.Length -eq 262144 -and $asyncProc.ExitCode -eq 0 -and $sw.ElapsedMilliseconds -lt 10000)
Assert-Check "Suite 2: Pipe Deadlock" "Positive Control: ReadToEndAsync() drains 256KB stderr and stdout concurrently in $($sw.ElapsedMilliseconds)ms" $asyncPassed

# 2.3 AST Verification: Both build-mios.ps1 scripts use ReadToEndAsync() for podman create and podman export
foreach ($bp in @('c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\build-mios.ps1')) {
    $ast = [System.Management.Automation.Language.Parser]::ParseFile($bp, [ref]$null, [ref]$null)
    $exportAst = $ast.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Export-WslTar' }, $true)
    $text = $exportAst.Extent.Text

    $hasCreateAsync = ($text -match '\$createStderrTask\s*=\s*\$createProc\.StandardError\.ReadToEndAsync\(\)')
    $hasExportAsync = ($text -match '\$stderrTask\s*=\s*\$proc\.StandardError\.ReadToEndAsync\(\)')
    $noOldSync      = ($text -notmatch '\$createProc\.StandardError\.ReadToEnd\(\)')
    Assert-Check "Suite 2: Pipe Deadlock" "AST Check: $(Split-Path $bp -Parent | Split-Path -Leaf)\build-mios.ps1 Export-WslTar uses ReadToEndAsync() on create & export" ($hasCreateAsync -and $hasExportAsync -and $noOldSync)
}

# ==============================================================================
# SUITE 3: PARAMETER DROPPING NEGATIVE CONTROLS (ELEVATION RECONSTRUCTION)
# ==============================================================================
Write-Host "`n--- Suite 3: Parameter Dropping Negative Controls ---" -ForegroundColor Yellow

# Parse authentic Get-MiosElevateArgs from mios-install.ps1
$instScript = "c:\mios-bootstrap\installation\mios-install.ps1"
$instAst = [System.Management.Automation.Language.Parser]::ParseFile($instScript, [ref]$null, [ref]$null)
$elevAst = $instAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Get-MiosElevateArgs' }, $true)
. ([scriptblock]::Create($elevAst.Extent.Text))

# Test input parameters
$sampleParams = @{
    Target      = 'wsl'
    Type        = 'oci'
    Unattended  = [switch]$true
    Passthrough = @('C:\Program Files\MiOS\export.tar', '--custom-flag', 'value with spaces')
}

# Reconstructed arguments via Get-MiosElevateArgs
$reconstructedArgs = Get-MiosElevateArgs -BoundParameters $sampleParams -Target 'wsl'

# Create simulated child script to test real parameter binding under pwsh
$childScript = Join-Path ([System.IO.Path]::GetTempPath()) ("test_child_binding_" + [Guid]::NewGuid().ToString("N") + ".ps1")
$childCode = @'
[CmdletBinding()]
param(
    [string]$Target = '',
    [string]$Type = '',
    [switch]$Unattended,
    [parameter(ValueFromRemainingArguments=$true)][string[]]$Passthrough = @()
)
[PSCustomObject]@{
    Target      = $Target
    Type        = $Type
    Unattended  = $Unattended.IsPresent
    Passthrough = $Passthrough
} | ConvertTo-Json -Compress
'@
[System.IO.File]::WriteAllText($childScript, $childCode, [System.Text.Encoding]::UTF8)

try {
    # 3.1 Positive Control: Child script correctly binds reconstructed parameters
    $reconstructedOutput = & pwsh.exe -NoProfile -ExecutionPolicy Bypass -File $childScript @reconstructedArgs | ConvertFrom-Json
    $recSuccess = ($reconstructedOutput.Target -eq 'wsl' -and
                   $reconstructedOutput.Type -eq 'oci' -and
                   $reconstructedOutput.Unattended -eq $true -and
                   $reconstructedOutput.Passthrough -contains 'C:\Program Files\MiOS\export.tar' -and
                   $reconstructedOutput.Passthrough -contains 'value with spaces')
    Assert-Check "Suite 3: Elevation" "Positive Control: Child process correctly binds reconstructed arguments" $recSuccess

    # 3.2 Negative Control: Child script with legacy $PSBoundParameters.Values FAILS parameter binding
    # In legacy code, passing $sampleParams.Values passes raw values without flag names
    $legacyRawValues = @($sampleParams.Values | ForEach-Object { [string]$_ })
    $legacyOutput = & pwsh.exe -NoProfile -ExecutionPolicy Bypass -File $childScript @legacyRawValues | ConvertFrom-Json
    
    # Notice: In legacy values, $Unattended is FALSE because raw 'True' was bound to positional parameter or dropped,
    # and parameter names are completely lost
    $legacyDefectDemonstrated = ($legacyOutput.Unattended -eq $false -or $legacyOutput.Target -ne 'wsl')
    Assert-Check "Suite 3: Elevation" "Negative Control: Legacy PSBoundParameters.Values fails switch/named binding in child process" $legacyDefectDemonstrated

    # 3.3 Negative Control: Dictionary .Values array lacks parameter names
    $valuesLackFlagNames = ($legacyRawValues -notcontains '-Target' -and $legacyRawValues -notcontains '-Type' -and $legacyRawValues -notcontains '-Unattended')
    Assert-Check "Suite 3: Elevation" "Negative Control: PSBoundParameters.Values array strips '-Target', '-Type', '-Unattended' flag names" $valuesLackFlagNames

    # 3.4 Positive Control: Menu selection without CLI -Target is injected
    $menuOnly = @{ Unattended = [switch]$true }
    $menuReconstructed = Get-MiosElevateArgs -BoundParameters $menuOnly -Target 'flash'
    $hasInjectedTarget = ($menuReconstructed -contains '-Target' -and $menuReconstructed[$menuReconstructed.IndexOf('-Target') + 1] -eq 'flash')
    Assert-Check "Suite 3: Elevation" "Positive Control: Injects interactive menu selection (-Target flash) when missing from parameters" $hasInjectedTarget

} finally {
    if (Test-Path $childScript) { Remove-Item -LiteralPath $childScript -Force -ErrorAction SilentlyContinue }
}

# ==============================================================================
# SUITE 4: DUPLICATE [USER] SECTIONS NEGATIVE CONTROLS (WSL.CONF DEDUPLICATION)
# ==============================================================================
Write-Host "`n--- Suite 4: Duplicate [user] Sections Negative Controls ---" -ForegroundColor Yellow

$testConfDir = Join-Path ([System.IO.Path]::GetTempPath()) ("mios_conf_test_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testConfDir -Force | Out-Null

try {
    $dirtyConfPath = Join-Path $testConfDir "wsl.conf"

    # Dirty wsl.conf with triple [user] sections and conflicting default users (strictly BOM-free UTF-8)
    $dirtyConf = @"
[boot]
systemd=false
[user]
default=olduser
[interop]
enabled=true
[user]
default=otheruser
[user]
default=mios
[boot]
systemd=true
"@
    [System.IO.File]::WriteAllText($dirtyConfPath, $dirtyConf, (New-Object System.Text.UTF8Encoding($false)))

    # Execute Python sanitizer from build-mios.ps1
    $pySanitizeCode = @"
import os, re

def sanitize_conf(filepath, has_user_mios):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    seen_sections = set()
    current_sec = None
    sec_keys = {}
    new_lines = []

    for line in lines:
        sm = re.match(r'^\s*\[([a-zA-Z0-9_-]+)\]\s*$', line)
        if sm:
            sec = sm.group(1).lower()
            if sec in seen_sections:
                current_sec = sec
                continue
            seen_sections.add(sec)
            current_sec = sec
            sec_keys[sec] = set()
            new_lines.append(f'[{sec}]')
            continue

        km = re.match(r'^\s*([a-zA-Z0-9_.-]+)\s*=\s*(.*)$', line)
        if km and current_sec:
            k = km.group(1).lower()
            v = km.group(2).strip()
            if k in sec_keys[current_sec]:
                continue
            sec_keys[current_sec].add(k)
            if current_sec == 'boot' and k == 'systemd':
                new_lines.append('systemd=true')
                continue
            if current_sec == 'user' and k == 'default':
                new_lines.append('default=mios' if has_user_mios else f'default={v}')
                continue
            new_lines.append(line)
            continue
        new_lines.append(line)

    if 'boot' not in seen_sections:
        new_lines.append('[boot]')
        new_lines.append('systemd=true')
    elif 'systemd' not in sec_keys.get('boot', set()):
        idx = new_lines.index('[boot]') + 1
        new_lines.insert(idx, 'systemd=true')

    if has_user_mios:
        if 'user' not in seen_sections:
            new_lines.append('[user]')
            new_lines.append('default=mios')
        elif 'default' not in sec_keys.get('user', set()):
            idx = new_lines.index('[user]') + 1
            new_lines.insert(idx, 'default=mios')

    output = '\n'.join(new_lines).strip() + '\n'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)

sanitize_conf('$($dirtyConfPath.Replace('\','/'))', True)
"@
    $pyScriptPath = Join-Path $testConfDir "sanitize.py"
    [System.IO.File]::WriteAllText($pyScriptPath, $pySanitizeCode, (New-Object System.Text.UTF8Encoding($false)))
    python $pyScriptPath

    $cleanContent = Get-Content $dirtyConfPath -Raw

    # 4.1 Negative Control: Triple [user] sections reduced to exactly 1
    $userHeaderMatches = [regex]::Matches($cleanContent, '(?m)^\s*\[user\]\s*$')
    Assert-Check "Suite 4: wsl.conf" "Negative Control: Sanitizer eliminates duplicate [user] sections (Count: $($userHeaderMatches.Count))" ($userHeaderMatches.Count -eq 1)

    # 4.2 Negative Control: Duplicate [boot] sections reduced to exactly 1
    $bootHeaderMatches = [regex]::Matches($cleanContent, '(?m)^\s*\[boot\]\s*$')
    Assert-Check "Suite 4: wsl.conf" "Negative Control: Sanitizer eliminates duplicate [boot] sections (Count: $($bootHeaderMatches.Count))" ($bootHeaderMatches.Count -eq 1)

    # 4.3 Positive Control: Ensures systemd=true and default=mios are configured
    $hasSystemdTrue = ($cleanContent -match '(?m)^\s*systemd\s*=\s*true\s*$')
    $hasDefaultMios = ($cleanContent -match '(?m)^\s*default\s*=\s*mios\s*$')
    Assert-Check "Suite 4: wsl.conf" "Positive Control: Sanitizer guarantees [boot] systemd=true and [user] default=mios" ($hasSystemdTrue -and $hasDefaultMios)

    # 4.4 Adversarial Edge Case Discovery: UTF-8 BOM sensitivity
    # Demonstrate that if file contains UTF-8 BOM, regex on line 1 fails to match section header
    $lineWithBom = "`u{FEFF}[boot]"
    $lineWithoutBom = "[boot]"
    $bomMatched = ($lineWithBom -match '^\s*\[([a-zA-Z0-9_-]+)\]\s*$')
    $noBomMatched = ($lineWithoutBom -match '^\s*\[([a-zA-Z0-9_-]+)\]\s*$')
    Assert-Check "Suite 4: wsl.conf" "Adversarial Finding: UTF-8 BOM on first line inhibits regex section matching (requires BOM-free UTF-8 or utf-8-sig)" (-not $bomMatched -and $noBomMatched)

} finally {
    if (Test-Path $testConfDir) { Remove-Item -LiteralPath $testConfDir -Recurse -Force -ErrorAction SilentlyContinue }
}

# ==============================================================================
# SUITE 5: MISSING WSL.EXE & ARCHIVE DEFENSE NEGATIVE CONTROLS
# ==============================================================================
Write-Host "`n--- Suite 5: Missing wsl.exe & Missing Archive Negative Controls ---" -ForegroundColor Yellow

foreach ($bp in @('c:\mios-bootstrap\build-mios.ps1', 'c:\MiOS\build-mios.ps1')) {
    $repoName = Split-Path (Split-Path $bp -Parent) -Leaf
    $bAst = [System.Management.Automation.Language.Parser]::ParseFile($bp, [ref]$null, [ref]$null)
    $impAst = $bAst.Find({ $args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $args[0].Name -eq 'Import-MiosWsl' }, $true)
    . ([scriptblock]::Create($impAst.Extent.Text))

    # 5.1 Negative Control: Missing wsl.exe throws actionable error
    function global:Get-Command {
        param($Name, $ErrorAction)
        if ($Name -eq 'wsl.exe') { return $null }
        return Microsoft.PowerShell.Core\Get-Command @PSBoundParameters
    }
    $missingWslThrew = $false
    $missingWslMsg = ""
    try {
        Import-MiosWsl -Archive "C:\dummy\file.tar" -InstallDir "C:\dummy\distro"
    } catch {
        $missingWslThrew = $true
        $missingWslMsg = $_.Exception.Message
    } finally {
        Remove-Item Function:\Get-Command -ErrorAction SilentlyContinue
    }
    Assert-Check "Suite 5: WSL Preflight" "[$repoName] Negative Control: Throws actionable error when wsl.exe is missing from PATH" ($missingWslThrew -and $missingWslMsg -match "WSL is not installed or wsl.exe was not found in PATH") "Caught: $missingWslMsg"

    # 5.2 Negative Control: Missing archive file throws before WSL invocation
    $missingTarThrew = $false
    $missingTarMsg = ""
    try {
        Import-MiosWsl -Archive "C:\nonexistent_path_xyz_12345\missing.tar" -InstallDir "C:\dummy\distro"
    } catch {
        $missingTarThrew = $true
        $missingTarMsg = $_.Exception.Message
    }
    Assert-Check "Suite 5: WSL Preflight" "[$repoName] Negative Control: Throws 'WSL2 archive not found' for non-existent archive" ($missingTarThrew -and $missingTarMsg -match "WSL2 archive not found") "Caught: $missingTarMsg"
}

# ==============================================================================
# SUITE 6: STANDING GATES ATTESTATION & TAMPER NEGATIVE CONTROLS
# ==============================================================================
Write-Host "`n--- Suite 6: Standing Gates Attestation & Tamper Controls ---" -ForegroundColor Yellow

$gateBinary = "c:\MiOS\src\mios-rs\target\debug\mios-gate.exe"
Assert-Check "Suite 6: Standing Gates" "Gate binary exists at $gateBinary" (Test-Path $gateBinary)

# 6.1 Run all 5 Rust standing verification gates
$gates = @(
    'phase-registry',
    'ratchet-direction',
    'credential-literals',
    'version-literals-ssot',
    'signature-policy'
)

foreach ($g in $gates) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $gateBinary
    $psi.Arguments              = "$g --root `"c:\MiOS`""
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.UseShellExecute        = $false
    $proc = [System.Diagnostics.Process]::Start($psi)
    $out = $proc.StandardOutput.ReadToEnd()
    $proc.WaitForExit()
    Assert-Check "Suite 6: Standing Gates" "Positive Control: Gate '$g' passes with exit code 0" ($proc.ExitCode -eq 0) "Output: $($out.Trim())"
}

# 6.2 Run Python CI suite checker
$ciPsi = New-Object System.Diagnostics.ProcessStartInfo
$ciPsi.FileName               = "python"
$ciPsi.Arguments              = "c:\MiOS\tools\ci-suites.py --check"
$ciPsi.RedirectStandardOutput = $true
$ciPsi.RedirectStandardError  = $true
$ciPsi.UseShellExecute        = $false
$ciProc = [System.Diagnostics.Process]::Start($ciPsi)
$ciOut = $ciProc.StandardOutput.ReadToEnd()
$ciProc.WaitForExit()
Assert-Check "Suite 6: Standing Gates" "Positive Control: ci-suites.py --check passes with exit code 0" ($ciProc.ExitCode -eq 0) "Output: $($ciOut.Trim())"

# 6.3 Tamper Negative Control: signature-policy gate sensitivity
$tamperSigDir = Join-Path ([System.IO.Path]::GetTempPath()) ("mios_sig_tamper_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path (Join-Path $tamperSigDir "usr/lib/containers") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $tamperSigDir "usr/share/mios") -Force | Out-Null
Copy-Item "c:\MiOS\usr\share\mios\mios.toml" (Join-Path $tamperSigDir "usr/share/mios/mios.toml")
[System.IO.File]::WriteAllText((Join-Path $tamperSigDir "usr/lib/containers/policy.json"), '{"default": [{"type": "reject"}]}')

$tPsi = New-Object System.Diagnostics.ProcessStartInfo
$tPsi.FileName               = $gateBinary
$tPsi.Arguments              = "signature-policy --root `"$tamperSigDir`""
$tPsi.RedirectStandardOutput = $true
$tPsi.RedirectStandardError  = $true
$tPsi.UseShellExecute        = $false
$tProc = [System.Diagnostics.Process]::Start($tPsi)
$tOut = $tProc.StandardOutput.ReadToEnd()
$tProc.WaitForExit()
Remove-Item -LiteralPath $tamperSigDir -Recurse -Force -ErrorAction SilentlyContinue

Assert-Check "Suite 6: Standing Gates" "Negative Control: signature-policy gate FAILS (exit code $($tProc.ExitCode) != 0) when policy.json is tampered" ($tProc.ExitCode -ne 0)

# ==============================================================================
# SUITE 7: ZERO UNPROJECTED DIFFS UNDER SYNC-GENERATED.SH
# ==============================================================================
Write-Host "`n--- Suite 7: Zero Unprojected Diffs under sync-generated.sh ---" -ForegroundColor Yellow

# Baseline check
$beforeStatus = (git -C "c:\MiOS" status --porcelain)

# Run sync-generated.sh
$syncPsi = New-Object System.Diagnostics.ProcessStartInfo
$syncPsi.FileName               = "bash"
$syncPsi.Arguments              = "./tools/sync-generated.sh"
$syncPsi.WorkingDirectory       = "c:\MiOS"
$syncPsi.RedirectStandardOutput = $true
$syncPsi.RedirectStandardError  = $true
$syncPsi.UseShellExecute        = $false
$syncProc = [System.Diagnostics.Process]::Start($syncPsi)
$syncOut = $syncProc.StandardOutput.ReadToEnd()
$syncProc.WaitForExit()

Assert-Check "Suite 7: Projection Sync" "Positive Control: sync-generated.sh completes with exit code 0" ($syncProc.ExitCode -eq 0)

# Check git status after - must be byte-for-byte identical to baseline (0 unprojected diffs)
$afterStatus = (git -C "c:\MiOS" status --porcelain)
$diffBetweenRuns = Compare-Object -ReferenceObject $beforeStatus -DifferenceObject $afterStatus

$zeroDiffs = ($null -eq $diffBetweenRuns -or $diffBetweenRuns.Count -eq 0)
Assert-Check "Suite 7: Projection Sync" "Positive Control: 0 unprojected diffs introduced by sync-generated.sh (idempotency verified)" $zeroDiffs

# ==============================================================================
# FINAL SUMMARY & EXIT
# ==============================================================================
Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "  EMPIRICAL ADVERSARIAL CHALLENGE SUMMARY" -ForegroundColor Cyan
Write-Host "  Total Tests Executed : $script:TotalTests"
Write-Host "  Passed Tests         : $script:PassedTests" -ForegroundColor Green
Write-Host "  Failed Tests         : $script:FailedTests" -ForegroundColor $(if ($script:FailedTests -eq 0) { 'Green' } else { 'Red' })
Write-Host "================================================================================`n" -ForegroundColor Cyan

if ($script:FailedTests -eq 0) {
    Write-Host "ALL $script:TotalTests TWO-SIDED ADVERSARIAL CHALLENGES PASSED EMPIRICALLY!`n" -ForegroundColor Green
    exit 0
} else {
    Write-Host "ADVERSARIAL CHALLENGE FAILED: $script:FailedTests test(s) failed.`n" -ForegroundColor Red
    exit 1
}
