#!/usr/bin/env bash
# 40-composefs-verity.sh - promote composefs from default (yes) to verity mode
# Tamper-evident root. Requires ext4 or btrfs target FS (NOT xfs).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

conf=/usr/lib/ostree/prepare-root.conf
if [[ -f "$conf" ]]; then
    log "backing up existing $conf -> ${conf}.orig"
    cp -a "$conf" "${conf}.orig"
fi

cat > "$conf" <<'EOF'
# MiOS: composefs in verity mode. Tamper-evident root.
# Target filesystems must support fsverity (ext4, btrfs). XFS is NOT supported.
[composefs]
enabled = verity

[root]
transient = false

[etc]
transient = false
EOF

# Mask systemd-remount-fs (known-broken with composefs on F42+)
log "masking systemd-remount-fs.service (composefs interop bug)"
ln -sf /dev/null /etc/systemd/system/systemd-remount-fs.service

log "composefs verity mode configured"