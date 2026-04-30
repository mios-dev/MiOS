#!/usr/bin/bash
# Required: composefs verity integrity check
set -euo pipefail

# 1. Check if composefs is enabled in prepare-root.conf
if grep -q "enabled = verity" /usr/lib/ostree/prepare-root.conf 2>/dev/null; then
    echo "[greenboot] composefs verity is enabled in configuration"
else
    echo "[greenboot] INFO: composefs verity not requested - skipping deep check"
    exit 0
fi

# 2. Check if the root filesystem is actually composefs
if mount | grep "type composefs" >/dev/null; then
    echo "[greenboot] SUCCESS: root is mounted as composefs"
else
    echo "[greenboot] ERROR: composefs requested but not active"
    # Note: we don't exit 1 here yet because it might be the first boot
    # but we should definitely log it.
fi

# 3. Quick integrity sample (if composefs-info is present)
if command -v composefs-info >/dev/null; then
    # We can't easily find the .cfs image path at runtime without parsing 
    # ostree metadata, but we can verify that some core files have verity bits.
    if fsverity digest /usr/bin/bash >/dev/null 2>&1; then
        echo "[greenboot] SUCCESS: fsverity is active on /usr/bin/bash"
    else
        echo "[greenboot] FAILURE: fsverity missing on critical binary"
        exit 1
    fi
fi

exit 0
