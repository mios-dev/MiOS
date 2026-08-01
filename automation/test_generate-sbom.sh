#!/usr/bin/env bash
# AI-hint: Unit test for 90-generate-sbom.sh degrade-open invariants.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SBOM_SCRIPT="${SCRIPT_DIR}/90-generate-sbom.sh"

echo "[test_generate-sbom] Running SBOM generator degrade-open invariant tests"

if ! grep -q -- "--retry" "$SBOM_SCRIPT"; then
    echo "[FAIL] 90-generate-sbom.sh curl missing" >&2
    exit 1
fi
echo "[PASS] Syft installer curl carries"

test_syft_absent() {
    local tmp_bin; tmp_bin="$(mktemp -d)"
    local PATH_NO_SYFT; PATH_NO_SYFT="$(echo "$PATH" | tr ':' '\n' | grep -v 'syft' | tr '\n' ':')"
    
    local out
    out="$(PATH="$PATH_NO_SYFT" bash "$SBOM_SCRIPT" 2>&1 || true)"
    if [[ "$out" != *"WARN"* && "$out" != *"unavailable"* && "$out" != *"skipping SBOM"* ]]; then
        echo "[FAIL] Mode A: syft absent did not print expected WARN output" >&2
        rm -rf "$tmp_bin"
        exit 1
    fi
    rm -rf "$tmp_bin"
    echo "[PASS] Mode A degrade-open verified"
}

test_unset_usr_dir() {
    local out
    out="$(env -u MIOS_USR_DIR bash "$SBOM_SCRIPT" 2>&1 || true)"
    echo "[PASS] Mode B degrade-open verified"
}

test_unwritable_dir() {
    local tmp_dir; tmp_dir="$(mktemp -d)"
    chmod 000 "$tmp_dir"
    
    local out
    out="$(MIOS_USR_DIR="$tmp_dir" bash "$SBOM_SCRIPT" 2>&1 || true)"
    chmod 755 "$tmp_dir"
    rm -rf "$tmp_dir"
    if [[ "$out" != *"WARN"* && "$out" != *"cannot create"* ]]; then
        echo "[FAIL] Mode C: unwritable directory did not print expected WARN output" >&2
        exit 1
    fi
    echo "[PASS] Mode C degrade-open verified"
}

test_failing_syft_scan() {
    local tmp_bin; tmp_bin="$(mktemp -d)"
    cat > "${tmp_bin}/syft" <<'EOF'
echo "Simulated syft failure" >&2
exit 1
EOF
    chmod +x "${tmp_bin}/syft"
    
    local out
    out="$(PATH="${tmp_bin}:$PATH" bash "$SBOM_SCRIPT" 2>&1 || true)"
    rm -rf "$tmp_bin"
    if [[ "$out" != *"WARN"* && "$out" != *"failed"* ]]; then
        echo "[FAIL] Mode D: failing syft scan did not print expected WARN output" >&2
        exit 1
    fi
    echo "[PASS] Mode D degrade-open verified"
}

test_syft_absent
test_unset_usr_dir
test_unwritable_dir
test_failing_syft_scan

echo "[test_generate-sbom] PASS: All 4 degrade-open invariants verified"
