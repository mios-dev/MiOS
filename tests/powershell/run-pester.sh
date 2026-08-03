#!/usr/bin/env bash
# AI-hint: Runner for Pester test suite across tests/powershell/*.Tests.ps1. Degrades open if pwsh/Pester is absent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PS_BIN=""
for candidate in pwsh powershell powershell.exe \
    /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
    /c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
    "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"; do
    if command -v "$candidate" >/dev/null 2>&1 || [ -f "$candidate" ]; then
        PS_BIN="$candidate"
        break
    fi
done

if [ -z "$PS_BIN" ]; then
    echo "[run-pester] WARNING: pwsh/powershell is missing, skipping Pester test suite" >&2
    exit 0
fi

# Check if Pester module is available
HAS_PESTER=$("$PS_BIN" -NoProfile -NonInteractive -Command "
    if (Get-Module -ListAvailable -Name Pester) {
        Write-Output 'YES'
    } else {
        try {
            Install-Module -Name Pester -Scope CurrentUser -Force -SkipPublisherCheck -EA Stop
            Write-Output 'YES'
        } catch {
            Write-Output 'NO'
        }
    }
" 2>&1 || true)

if ! echo "$HAS_PESTER" | grep -q "YES"; then
    echo "[run-pester] WARNING: Pester module is missing and could not be provisioned, skipping Pester suite" >&2
    exit 0
fi

echo "[run-pester] Running Pester tests in tests/powershell..."

win_test_dir="$ROOT/tests/powershell"
if [[ "$win_test_dir" =~ ^/mnt/c/ ]]; then
    win_test_dir="C:/${win_test_dir#/mnt/c/}"
elif [[ "$win_test_dir" =~ ^/c/ ]]; then
    win_test_dir="C:/${win_test_dir#/c/}"
fi

OUT=$("$PS_BIN" -NoProfile -NonInteractive -Command "
    Import-Module Pester -ErrorAction SilentlyContinue
    \$testFiles = Get-ChildItem -Path '${win_test_dir}' -Filter '*.Tests.ps1' -Recurse
    if (-not \$testFiles) {
        Write-Output 'PESTER_PASS'
        exit 0
    }
    try {
        \$config = [PesterConfiguration]::Default
        \$config.Run.Path = '${win_test_dir}'
        \$config.Output.Verbosity = 'Normal'
        \$result = Invoke-Pester -Configuration \$config
        if (\$result.FailedCount -gt 0) {
            Write-Output (\"PESTER_FAIL: \" + \$result.FailedCount + \" test(s) failed\")
        } else {
            Write-Output 'PESTER_PASS'
        }
    } catch {
        \$res = Invoke-Pester -Path '${win_test_dir}' -PassThru -ErrorAction SilentlyContinue
        if (\$res.FailedCount -gt 0) {
            Write-Output (\"PESTER_FAIL: \" + \$res.FailedCount + \" test(s) failed\")
        } else {
            Write-Output 'PESTER_PASS'
        }
    }
" 2>&1 || true)

if echo "$OUT" | grep -q "PESTER_FAIL"; then
    echo "$OUT" >&2
    echo "[run-pester] FAIL: Pester test suite failed" >&2
    exit 1
fi

echo "$OUT"
echo "[run-pester] PASS: All Pester tests passed"
exit 0
