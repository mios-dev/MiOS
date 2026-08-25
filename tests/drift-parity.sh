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
bash_rc=0
MIOS_DRIFT_CHECK_SOFT=1 bash "${MIOS_ROOT}/automation/98-drift-checks.sh" > "$BASH_LOG" 2>&1 || bash_rc=$?

echo "[drift-parity] Running miosd native drift check..."
RUST_LOG=$(mktemp)
rust_rc=0
"${MIOSD_BIN}" drift-check --root "$MIOS_ROOT" --soft --parity > "$RUST_LOG" 2>&1 || rust_rc=$?

echo "[drift-parity] Differential verdict comparison:"
python3 - "$BASH_LOG" "$RUST_LOG" "$bash_rc" "$rust_rc" <<'PY'
import sys

bash_log, rust_log = sys.argv[1], sys.argv[2]
bash_rc, rust_rc = int(sys.argv[3]), int(sys.argv[4])

with open(bash_log, "r", encoding="utf-8", errors="ignore") as f:
    b_lines = f.readlines()

with open(rust_log, "r", encoding="utf-8", errors="ignore") as f:
    r_lines = f.readlines()

b_has_violation = any("[VIOLATION]" in l or "violated" in l.lower() or "failed" in l.lower() for l in b_lines)
r_has_fail = any("[FAIL]" in l for l in r_lines)

disagreements = []
if bash_rc != rust_rc:
    disagreements.append(f"Exit code mismatch: bash={bash_rc}, rust={rust_rc}")

if b_has_violation != r_has_fail:
    disagreements.append(f"Verdict mismatch: bash_has_violation={b_has_violation}, rust_has_fail={r_has_fail}")

if disagreements:
    print("[drift-parity] FAIL: Disagreements detected between Bash and Rust runner:")
    for d in disagreements:
        print(f"  - {d}")
    sys.exit(1)

print("[drift-parity] PASS: Bash and Rust runner verdicts agree cleanly.")
sys.exit(0)
PY
cmp_rc=$?

rm -f "$BASH_LOG" "$RUST_LOG"

if [[ $cmp_rc -ne 0 ]]; then
    echo "[drift-parity] Differential parity check FAILED." >&2
    exit 1
fi

echo "[drift-parity] Parity check completed successfully."
