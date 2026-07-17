#!/usr/bin/env bash
# AI-hint: Runner for shellcheck across automation, tools, and libexec shell scripts. Degrades open if shellcheck is absent.
# AI-related: /usr/libexec/mios/mios-
set -euo pipefail

# SCRIPT_DIR is the location of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v shellcheck >/dev/null 2>&1; then
    # exit 2 == "skipped, NOT linted" so the drift-gate WARNs rather than printing a
    # false-green conformance summary over nothing linted.
    echo "[lint-shell] WARNING: shellcheck is missing -- shell linting SKIPPED (not a pass)" >&2
    exit 2
fi

# Find all shell files
files=()

# 1. automation/*.sh
for f in "${ROOT}"/automation/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

# 2. tools/*.sh
for f in "${ROOT}"/tools/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

# 3. usr/libexec/mios/mios-* (filter by shebang)
for f in "${ROOT}"/usr/libexec/mios/mios-*; do
    if [ -f "$f" ]; then
        # read the first line
        read -r first_line < "$f" || true
        if [[ "$first_line" =~ ^#\!.*(bash|sh) ]]; then
            files+=("$f")
        fi
    fi
done

if [ ${#files[@]} -eq 0 ]; then
    echo "[lint-shell] No shell scripts found to lint."
    exit 0
fi

echo "[lint-shell] Linting ${#files[@]} shell scripts at error level..."
if ! shellcheck --severity=error "${files[@]}"; then
    echo "[lint-shell] FAIL: shellcheck found error-level issues in the repository." >&2
    exit 1
fi

# Find modified shell files in this change/branch to enforce warning-level linting
modified_files=()
git_ref="origin/main"
if ! git rev-parse --verify "$git_ref" >/dev/null 2>&1; then
    git_ref="HEAD~1"
fi

if git rev-parse --verify "$git_ref" >/dev/null 2>&1; then
    # Find all added/modified shell files or usr/libexec/mios/mios-* scripts
    while IFS= read -r f; do
        if [ -f "$f" ]; then
            # Verify if this file is in our list of files to check (i.e. matches our shebang check or is a .sh file)
            if [[ "$f" =~ \.sh$ ]]; then
                modified_files+=("$f")
            elif [[ "$f" =~ ^usr/libexec/mios/mios- ]]; then
                read -r first_line < "$f" || true
                if [[ "$first_line" =~ ^#\!.*(bash|sh) ]]; then
                    modified_files+=("$f")
                fi
            fi
        fi
    done < <(git diff --name-only --diff-filter=ACMRT "$git_ref" 2>/dev/null || true)
fi

if [ ${#modified_files[@]} -gt 0 ]; then
    echo "[lint-shell] Linting ${#modified_files[@]} modified/new shell scripts at warning level..."
    if ! shellcheck --severity=warning "${modified_files[@]}"; then
        echo "[lint-shell] FAIL: shellcheck found warning-level or higher issues in modified files." >&2
        exit 1
    fi
else
    echo "[lint-shell] No modified shell scripts to lint at warning level."
fi

echo "[lint-shell] PASS: all shell scripts conform to safety rules."
exit 0
