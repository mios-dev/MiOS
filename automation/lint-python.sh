#!/usr/bin/env bash
# AI-hint: Python py_compile + static analysis gate for usr/lib/mios, tools, and usr/libexec/mios.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[lint-python] WARNING: python3 is missing -- python linting SKIPPED (not a pass)" >&2
    exit 2
fi

files=()

# 1. usr/lib/mios/**/*.py
if [ -d "${ROOT}/usr/lib/mios" ]; then
    while IFS= read -r f; do
        [ -f "$f" ] && files+=("$f")
    done < <(find "${ROOT}/usr/lib/mios" -name "*.py")
fi

# 2. tools/*.py
for f in "${ROOT}"/tools/*.py; do
    [ -f "$f" ] && files+=("$f")
done

# 3. usr/libexec/mios/* with python shebangs
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
    echo "[lint-python] PASS: no Python files found to lint."
    exit 0
fi

echo "[lint-python] Compiling ${#files[@]} Python files with py_compile..."
failed=0

for f in "${files[@]}"; do
    if ! python3 -c "import sys, ast; ast.parse(open(sys.argv[1], 'rb').read(), sys.argv[1])" "$f" >/dev/null 2>&1; then
        echo "[lint-python] ERROR: Python compilation failed for $f" >&2
        failed=$((failed + 1))
    fi
done

if [ "$failed" -gt 0 ]; then
    echo "[lint-python] FAIL: $failed Python file(s) failed py_compile." >&2
    exit 1
fi

echo "[lint-python] PASS: all ${#files[@]} Python files compiled clean."
exit 0
