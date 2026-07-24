#!/usr/bin/env bash
# AI-hint: Runner for shellcheck across automation, tools, and libexec shell scripts. Degrades open if shellcheck is absent.
# AI-related: /usr/libexec/mios/mios-
set -euo pipefail

# SCRIPT_DIR is the location of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Ensure shellcheck is PRESENT so the lint actually GATES (a skipped lint is a
# false-green). If absent, provision it via the distro package manager -- dnf
# (`ShellCheck` on the Fedora build host) or apt (`shellcheck` on the CI/Ubuntu
# runner). build.sh runs this same lint in its POST-build drift phase on the build
# host, where nothing had installed shellcheck -> it silently SKIPPED; auto-provision
# closes that gap in every context (CI build job, Forgejo, local build) without
# depending on the environment pre-installing it. Best-effort + `set -e`-safe.
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
    # exit 2 == "skipped, NOT linted" so the drift-gate WARNs rather than printing a
    # false-green conformance summary over nothing linted. Reached only when no
    # package manager / no egress could provision shellcheck (genuine degrade-open).
    echo "[lint-shell] WARNING: shellcheck is missing and could not be provisioned -- shell linting SKIPPED (not a pass)" >&2
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
if [ -d ".git" ] && command -v git >/dev/null 2>&1; then
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

echo "[lint-shell] PASS: shellcheck reports no error-level issues repo-wide and no warning-level issues in modified/new scripts."
exit 0
