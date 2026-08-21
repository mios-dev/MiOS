#!/usr/bin/env bash
# AI-hint: Python py_compile + undefined-name gate for usr/lib/mios, usr/share/mios, tools, and usr/libexec/mios.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[lint-python] WARNING: python3 is missing" >&2
    exit 2
fi

files=()

# usr/share/mios ships runtime Python payloads too -- the OWUI pipe, the
# configurator's helpers. Leaving them out is how `Any` went unimported in the
# canonical OWUI entry point, which made the module unloadable.
if [ -d "${ROOT}/usr/share/mios" ]; then
    while IFS= read -r f; do
        [ -f "$f" ] && files+=("$f")
    done < <(find "${ROOT}/usr/share/mios" -name "*.py")
fi

if [ -d "${ROOT}/usr/lib/mios" ]; then
    while IFS= read -r f; do
        [ -f "$f" ] && files+=("$f")
    done < <(find "${ROOT}/usr/lib/mios" -name "*.py")
fi

for f in "${ROOT}"/tools/*.py; do
    [ -f "$f" ] && files+=("$f")
done

if [ -d "${ROOT}/usr/libexec/mios" ]; then
    for f in "${ROOT}"/usr/libexec/mios/*; do
        if [ -f "$f" ] && [[ "$f" != *.py ]]; then
            if file "$f" 2>/dev/null | grep -qE "text|script"; then
                head_line="$(head -n 1 "$f" 2>/dev/null || true)"
                if [[ "$head_line" == *"python"* ]]; then
                    files+=("$f")
                fi
            fi
        fi
    done
fi

if [ "${#files[@]}" -eq 0 ]; then
    echo "[lint-python] PASS: no Python files found to lint"
    exit 0
fi

echo "[lint-python] Compiling ${#files[@]} Python files with py_compile"
failed=0

for f in "${files[@]}"; do
    if ! python3 -c "import sys, ast; ast.parse(open(sys.argv[1], 'rb').read(), sys.argv[1])" "$f" >/dev/null 2>&1; then
        echo "[lint-python] ERROR: Python compilation failed for $f" >&2
        failed=$((failed + 1))
    fi
done

if [ "$failed" -gt 0 ]; then
    echo "[lint-python] FAIL: $failed Python file failed py_compile" >&2
    exit 1
fi

# Undefined-name pass. ast.parse above proves a file PARSES; it says nothing
# about whether the names it uses exist. Three undefined module-scope names sat
# in agent-pipe's server.py behind a clean parse, so the service could not
# import at all. pyflakes is the smallest tool that answers that question.
if command -v pyflakes >/dev/null 2>&1; then
    PYFLAKES=(pyflakes)
elif python3 -c 'import pyflakes' >/dev/null 2>&1; then
    PYFLAKES=(python3 -m pyflakes)
else
    PYFLAKES=()
fi

if [ "${#PYFLAKES[@]}" -eq 0 ]; then
    if [ "${MIOS_DRIFT_REQUIRE_TOOLS:-0}" = "1" ]; then
        echo "[lint-python] FAIL: pyflakes absent but MIOS_DRIFT_REQUIRE_TOOLS=1" >&2
        exit 1
    fi
    echo "[lint-python] SKIP: pyflakes absent -- undefined-name pass not run"
else
    echo "[lint-python] Undefined-name pass over ${#files[@]} Python files"
    undef=0
    for f in "${files[@]}"; do
        hits="$("${PYFLAKES[@]}" "$f" 2>/dev/null | grep -E 'undefined name' || true)"
        if [ -n "$hits" ]; then
            echo "$hits" >&2
            undef=$((undef + 1))
        fi
    done
    if [ "$undef" -gt 0 ]; then
        echo "[lint-python] FAIL: $undef Python file(s) reference undefined names" >&2
        exit 1
    fi
    echo "[lint-python] PASS: no undefined names"
fi

echo "[lint-python] PASS: all ${#files[@]} Python files compiled clean"
exit 0
