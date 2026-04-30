#!/usr/bin/bash
# Wanted check: High Availability (Pacemaker) Cluster Health
# Fails emit warnings in greenboot-status but do NOT trigger OS rollback.
set -euo pipefail

# If pacemaker isn't active (e.g., gated out because this is a VM or WSL2),
# skip the check completely. This prevents false positive failures.
if ! systemctl is-active --quiet pacemaker.service; then
    exit 0
fi

# If the cluster hasn't been bootstrapped yet (first boot sequence), skip.
if [[ ! -f /etc/corosync/corosync.conf ]]; then
    echo "HA cluster not yet bootstrapped."
    exit 0
fi

# Run the native cluster status check
if command -v pcs >/dev/null 2>&1; then
    if ! pcs cluster status >/dev/null 2>&1; then
        echo "HA cluster daemon is active, but 'pcs cluster status' reports errors!"
        exit 1
    fi
fi

echo "HA cluster is responding and healthy."
exit 0
