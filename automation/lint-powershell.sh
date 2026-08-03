#!/usr/bin/env bash
# AI-hint: Runner for PowerShell AST parser check across tracked *.ps1 files. Degrades open if pwsh/powershell is absent.
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
    echo "[lint-powershell] WARNING: pwsh/powershell is missing, skipping AST parse-gate" >&2
    exit 0
fi

# Gather tracked .ps1 files
files=()
if [ -d "$ROOT/.git" ] && command -v git >/dev/null 2>&1; then
    while IFS= read -r f; do
        if [ -f "$ROOT/$f" ] && [[ "$f" =~ \.ps1$ ]]; then
            files+=("$ROOT/$f")
        fi
    done < <(git -C "$ROOT" ls-files "*.ps1" 2>/dev/null || true)
fi

if [ ${#files[@]} -eq 0 ]; then
    while IFS= read -r f; do
        files+=("$f")
    done < <(find "$ROOT" -name "*.ps1" -type f 2>/dev/null || true)
fi

if [ ${#files[@]} -eq 0 ]; then
    echo "[lint-powershell] No .ps1 files found to lint"
    exit 0
fi

echo "[lint-powershell] Parsing AST for ${#files[@]} PowerShell (.ps1) files using $PS_BIN..."

ERRORS_FOUND=0

for file in "${files[@]}"; do
    win_file="$file"
    if [[ "$win_file" =~ ^/mnt/c/ ]]; then
        win_file="C:/${win_file#/mnt/c/}"
    elif [[ "$win_file" =~ ^/c/ ]]; then
        win_file="C:/${win_file#/c/}"
    fi

    OUT=$("$PS_BIN" -NoProfile -NonInteractive -Command "
        \$t = \$null
        \$e = \$null
        \$text = [System.IO.File]::ReadAllText('${win_file//\'/\'\'}', [System.Text.Encoding]::UTF8)
        [System.Management.Automation.Language.Parser]::ParseInput(\$text, [ref]\$t, [ref]\$e) | Out-Null
        if (\$e.Count -gt 0) {
            foreach (\$err in \$e) {
                Write-Output (\"PARSE_ERROR: ${win_file}:\" + \$err.Extent.StartLineNumber + \":\" + \$err.Extent.StartColumnNumber + \": \" + \$err.Message)
            }
        }
    " 2>&1 || true)

    if echo "$OUT" | grep -q "PARSE_ERROR:"; then
        echo "$OUT" | grep "PARSE_ERROR:" >&2
        ERRORS_FOUND=$((ERRORS_FOUND + 1))
    fi
done

if [ "$ERRORS_FOUND" -gt 0 ]; then
    echo "[lint-powershell] FAIL: Found $ERRORS_FOUND PowerShell file(s) with AST parse errors" >&2
    exit 1
fi

echo "[lint-powershell] PASS: All ${#files[@]} PowerShell files parsed cleanly with zero AST errors"
exit 0
