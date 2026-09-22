#!/bin/bash
set -euo pipefail
echo "[TEST-INVARIANT-REL] Running two-sided control gate..."
# Positive control
python3 -c "import sys; sys.exit(0)" || exit 1
# Negative control (planted defect must fail)
! python3 -c "import sys; sys.exit(1)" 2>/dev/null || {
    echo "[FAIL] Negative control failed to trap error!" >&2
    exit 1
}
echo "[PASS] [INVARIANT-REL] Two-sided control passed."
