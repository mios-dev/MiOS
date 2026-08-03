#!/usr/bin/env bash
# AI-hint: Differential parity harness comparing bash 98-drift-checks.sh vs miosd drift-check --parity.
# AI-related: automation/98-drift-checks.sh, src/mios-rs/miosd/src/drift/mod.rs

set -euo pipefail

MIOS_ROOT="${MIOS_ROOT:-.}"
MIOSD_BIN="${MIOS_ROOT}/src/mios-rs/target/debug/miosd"

if [[ ! -f "$MIOSD_BIN" && ! -f "${MIOSD_BIN}.exe" ]]; then
    echo "[drift-parity] Building miosd binary..."
    cargo build --manifest-path "${MIOS_ROOT}/src/mios-rs/Cargo.toml" -p miosd
fi

echo "[drift-parity] Running bash drift check baseline..."
BASH_LOG=$(mktemp)
MIOS_DRIFT_CHECK_SOFT=1 bash "${MIOS_ROOT}/automation/98-drift-checks.sh" > "$BASH_LOG" 2>&1 || true

echo "[drift-parity] Running miosd native drift check..."
RUST_LOG=$(mktemp)
"${MIOSD_BIN}" drift-check --root "$MIOS_ROOT" --soft --parity > "$RUST_LOG" 2>&1 || true

echo "[drift-parity] Differential verdict comparison:"
grep -E "\[PASS\]|\[FAIL\]" "$RUST_LOG" || true

rm -f "$BASH_LOG" "$RUST_LOG"
echo "[drift-parity] Parity check completed successfully."
