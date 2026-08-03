#!/usr/bin/env bash
# AI-hint: Runner for PSScriptAnalyzer static analysis across tracked *.ps1 files. Degrades open if PSScriptAnalyzer is absent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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
    echo "[lint-ps-analyzer] WARNING: pwsh/powershell is missing, skipping PSScriptAnalyzer gate" >&2
    exit 0
fi

SETTINGS_FILE="$ROOT/automation/PSScriptAnalyzerSettings.psd1"
win_settings="$SETTINGS_FILE"
if [[ "$win_settings" =~ ^/mnt/c/ ]]; then
    win_settings="C:/${win_settings#/mnt/c/}"
elif [[ "$win_settings" =~ ^/c/ ]]; then
    win_settings="C:/${win_settings#/c/}"
fi

# Check if PSScriptAnalyzer module is available
HAS_PSSA=$("$PS_BIN" -NoProfile -NonInteractive -Command "
    if (Get-Module -ListAvailable -Name PSScriptAnalyzer) {
        Write-Output 'YES'
    } else {
        try {
            Install-Module -Name PSScriptAnalyzer -Scope CurrentUser -Force -SkipPublisherCheck -EA Stop
            Write-Output 'YES'
        } catch {
            Write-Output 'NO'
        }
    }
" 2>&1 || true)

if ! echo "$HAS_PSSA" | grep -q "YES"; then
    echo "[lint-ps-analyzer] WARNING: PSScriptAnalyzer module is missing and could not be provisioned" >&2
    exit 0
fi

echo "[lint-ps-analyzer] Running PSScriptAnalyzer static analysis..."

win_root="$ROOT"
if [[ "$win_root" =~ ^/mnt/c/ ]]; then
    win_root="C:/${win_root#/mnt/c/}"
elif [[ "$win_root" =~ ^/c/ ]]; then
    win_root="C:/${win_root#/c/}"
fi

OUT=$("$PS_BIN" -NoProfile -NonInteractive -Command "
    \$results = Invoke-ScriptAnalyzer -Path '${win_root}' -Recurse -Settings '${win_settings}' -Severity Error -EA SilentlyContinue
    if (\$results) {
        foreach (\$r in \$results) {
            Write-Output (\"PSSA_ERROR: \" + \$r.ScriptPath + \":\" + \$r.Line + \": \" + \$r.RuleName + \" - \" + \$r.Message)
        }
    }
" 2>&1 || true)

if echo "$OUT" | grep -q "PSSA_ERROR:"; then
    echo "$OUT" | grep "PSSA_ERROR:" >&2
    echo "[lint-ps-analyzer] FAIL: PSScriptAnalyzer found Error-severity static analysis issues" >&2
    exit 1
fi

echo "[lint-ps-analyzer] PASS: PSScriptAnalyzer reports zero Error-severity findings"
exit 0
