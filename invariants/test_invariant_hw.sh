#!/bin/bash
# AI-hint: Hardware invariant: on a bootc VFIO host the CXL IOMMU bypass karg must be present; skips (exit 2) where no VFIO kargs exist.
set -euo pipefail
echo "[TEST-INVARIANT-HW] Verifying Kernel CXL IOMMU bypass parameter..."

kargs_file="/usr/lib/bootc/kargs.d/50-vfio-security.kargs"

# This invariant only applies to a booted bootc/MiOS host with VFIO kargs
# baked into the UKI. On a generic devcontainer, Codespace, or CI runner the
# file legitimately does not exist: that is a capability absence, not a
# defect, so it must SKIP (exit 2) rather than FAIL (exit 1) or silently PASS.
if [[ ! -f "$kargs_file" ]]; then
    echo "[SKIP] [INVARIANT-HW] $kargs_file not present; not a bootc VFIO host."
    exit 2
fi

grep -q "cxl_iommu_bypass=force" "$kargs_file" || {
    echo "[FAIL] Missing cxl_iommu_bypass=force in $kargs_file" >&2
    exit 1
}
echo "[PASS] [INVARIANT-HW] verified."
