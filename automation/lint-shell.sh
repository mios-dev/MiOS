#!/usr/bin/env bash
# AI-hint: Runner for shellcheck across automation, tools, and libexec shell scripts. Degrades open if shellcheck is absent.
# AI-related: /usr/libexec/mios/mios-
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v shellcheck >/dev/null 2>&1; then
    if command -v dnf >/dev/null 2>&1; then
        dnf install -y ShellCheck >/dev/null 2>&1 || true
    elif command -v apt-get >/dev/null 2>&1; then
        { sudo -n apt-get update -qq && sudo -n apt-get install -y shellcheck; } >/dev/null 2>&1 \
            || { apt-get update -qq && apt-get install -y shellcheck; } >/dev/null 2>&1 \
            || true
    fi
fi

if ! command -v shellcheck >/dev/null 2>&1; then
    echo "[lint-shell] WARNING: shellcheck is missing and could not be provisioned" >&2
    exit 2
fi

files=()

for f in "${ROOT}"/automation/*.sh "${ROOT}"/automation/tests/*.sh "${ROOT}"/automation/support/*.sh "${ROOT}"/automation/lib/*.sh; do
    if [ -f "$f" ]; then
        # Exclude generated globals.sh as its thousands of variables cause shellcheck 0.9.0 to OOM
        if [[ "$(basename "$f")" == "globals.sh" ]]; then
            continue
        fi
        files+=("$f")
    fi
done

for f in "${ROOT}"/tools/*.sh "${ROOT}"/tools/lib/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

for f in "${ROOT}"/installation/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

for f in "${ROOT}"/tests/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

for f in "${ROOT}"/usr/lib/mios/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

for f in "${ROOT}"/usr/libexec/mios/mios-*; do
    if [ -f "$f" ]; then
        read -r first_line < "$f" || true
        if [[ "$first_line" =~ ^#\!.*(bash|sh) ]]; then
            files+=("$f")
        fi
    fi
done

if [ ${#files[@]} -eq 0 ]; then
    echo "[lint-shell] No shell scripts found to lint"
    exit 0
fi

echo "[lint-shell] Linting ${#files[@]} shell scripts at error level"
if ! shellcheck --severity=error "${files[@]}"; then
    echo "[lint-shell] FAIL: shellcheck found error-level issues in the repository" >&2
    exit 1
fi

modified_files=()
if [ -d ".git" ] && command -v git >/dev/null 2>&1; then
    git_ref="origin/main"
    if ! git rev-parse --verify "$git_ref" >/dev/null 2>&1; then
        git_ref="HEAD~1"
    fi

    if git rev-parse --verify "$git_ref" >/dev/null 2>&1; then
        while IFS= read -r f; do
            if [ -f "$f" ]; then
                if [[ "$f" =~ \.sh$ ]]; then
                    if [[ "$(basename "$f")" != "globals.sh" ]]; then
                        modified_files+=("$f")
                    fi
                elif [[ "$f" =~ ^usr/libexec/mios/mios- ]]; then
                    read -r first_line < "$f" || true
                    if [[ "$first_line" =~ ^#\!.*(bash|sh) ]]; then
                        modified_files+=("$f")
                    fi
                fi
            fi
        done < <(git diff --name-only --diff-filter=ACMRT "$git_ref" 2>/dev/null || true)
    fi
fi

if [ ${#modified_files[@]} -gt 0 ]; then
    echo "[lint-shell] Linting ${#modified_files[@]} modified/new shell scripts at warning level"
    if ! shellcheck --severity=warning "${modified_files[@]}"; then
        echo "[lint-shell] FAIL: shellcheck found warning-level or higher issues in modified files" >&2
        exit 1
    fi
else
    echo "[lint-shell] No modified shell scripts to lint at warning level"
fi

echo "[lint-shell] PASS: shellcheck reports no error-level issues repo-wide and no warning-level issues in modified/new scripts"
exit 0
