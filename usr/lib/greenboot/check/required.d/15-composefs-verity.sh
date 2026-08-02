#!/usr/bin/bash
# AI-hint: Validates the integrity of the root filesystem by checking if composefs is enabled in prepare-root.conf, verifying the mount type, and performing a fsverity check on critical binaries.
set -euo pipefail

if grep -q "enabled = verity" /usr/lib/ostree/prepare-root.conf 2>/dev/null; then
    echo "[greenboot] composefs verity is enabled in configuration"
else
    echo "[greenboot] INFO: composefs verity not requested - skipping deep check"
    exit 0
fi

if mount | grep "type composefs" >/dev/null; then
    echo "[greenboot] SUCCESS: root is mounted as composefs"
else
    echo "[greenboot] ERROR: composefs requested but not active"
fi

if command -v composefs-info >/dev/null; then
    if fsverity digest /usr/bin/bash >/dev/null 2>&1; then
        echo "[greenboot] SUCCESS: fsverity is active on /usr/bin/bash"
    else
        echo "[greenboot] FAILURE: fsverity missing on critical binary"
        exit 1
    fi
fi

exit 0
