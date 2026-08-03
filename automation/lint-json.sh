#!/usr/bin/env bash
# AI-hint: JSON syntax verification gate across tracked/repo .json files.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[lint-json] WARNING: python3 is missing, skipping JSON syntax check" >&2
    exit 0
fi

files=()
if [ -d "$ROOT/.git" ] && command -v git >/dev/null 2>&1; then
    while IFS= read -r f; do
        if [ -f "$ROOT/$f" ] && [[ "$f" =~ \.json$ ]] && [[ "$f" != *"theme/fixtures/"* ]]; then
            files+=("$ROOT/$f")
        fi
    done < <(git -C "$ROOT" ls-files "*.json" 2>/dev/null || true)
fi

if [ ${#files[@]} -eq 0 ]; then
    while IFS= read -r f; do
        if [[ "$f" != *"theme/fixtures/"* ]]; then
            files+=("$f")
        fi
    done < <(find "$ROOT" -name "*.json" -type f -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/.devcontainer/*" -not -path "*/theme/fixtures/*" 2>/dev/null || true)
fi

if [ ${#files[@]} -eq 0 ]; then
    echo "[lint-json] PASS: no JSON files found to lint"
    exit 0
fi

echo "[lint-json] Checking ${#files[@]} JSON files..."
failed=0

for f in "${files[@]}"; do
    if ! python3 -c "import sys, json; json.load(open(sys.argv[1], 'r', encoding='utf-8-sig'))" "$f" >/dev/null 2>&1; then
        echo "[lint-json] ERROR: Invalid JSON syntax in $f" >&2
        failed=$((failed + 1))
    fi
done

if [ "$failed" -gt 0 ]; then
    echo "[lint-json] FAIL: $failed JSON file(s) failed validation" >&2
    exit 1
fi

echo "[lint-json] PASS: all ${#files[@]} JSON files parsed cleanly"
exit 0
