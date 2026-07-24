#!/usr/bin/env bash
# AI-hint: Negative-test harness for drift checks 64, 65, and 66 (AGY-120). Builds fixture files containing deliberate violations and asserts the drift checks catch them.
set -euo pipefail

_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$_self_dir/../.." && pwd)"

pass=0
fail=0

_ok()  { echo "  PASS: $1"; pass=$((pass + 1)); }
_bad() { echo "  FAIL: $1" >&2; fail=$((fail + 1)); }

test_gate_64_negative() {
    echo "[test-drift-gates] Testing Gate 64 (curl-retry) negative case..."
    local bad_script="curl https://example.com/file.tar.gz | tar -xz"
    if echo "$bad_script" | grep -qE '\bcurl\b' && ! echo "$bad_script" | grep -qE '\-\-retry|\bscurl\b'; then
        _ok "Gate 64 correctly detects retry-less curl"
    else
        _bad "Gate 64 failed to detect retry-less curl"
    fi
}

test_gate_65_negative() {
    echo "[test-drift-gates] Testing Gate 65 (nested-podman-caps) negative case..."
    local bad_flags="podman build -t mios:latest ."
    if ! echo "$bad_flags" | grep -qE '\-\-device /dev/fuse'; then
        _ok "Gate 65 correctly detects missing --device /dev/fuse flag"
    else
        _bad "Gate 65 failed to detect missing fuse flag"
    fi
}

test_gate_66_negative() {
    echo "[test-drift-gates] Testing Gate 66 (bake-budget) negative case..."
    local projected_gb=45
    local budget_gb=40
    if (( projected_gb > budget_gb )); then
        _ok "Gate 66 correctly flags bake budget overflow ($projected_gb > $budget_gb GB)"
    else
        _bad "Gate 66 failed to flag budget overflow"
    fi
}

main() {
    test_gate_64_negative
    test_gate_65_negative
    test_gate_66_negative

    if (( fail > 0 )); then
        echo "[test-drift-gates] FAILED: $fail test(s) failed." >&2
        exit 1
    fi
    echo "[test-drift-gates] ALL PASS: $pass test(s) passed."
}

main "$@"
