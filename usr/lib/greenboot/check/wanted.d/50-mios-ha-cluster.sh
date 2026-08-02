#!/usr/bin/bash
# AI-hint: Validates Pacemaker/Corosync cluster health via `pcs cluster status`; used by greenboot to monitor HA cluster stability without triggering rollbacks if the service is inactive or unbootstrapped.
# AI-related: pacemaker.service
set -euo pipefail

if ! systemctl is-active --quiet pacemaker.service; then
    exit 0
fi

if [[ ! -f /etc/corosync/corosync.conf ]]; then
    echo "HA cluster not yet bootstrapped"
    exit 0
fi

if command -v pcs >/dev/null 2>&1; then
    if ! pcs cluster status >/dev/null 2>&1; then
        echo "HA cluster daemon is active, but 'pcs cluster status' reports errors"
        exit 1
    fi
fi

echo "HA cluster is responding and healthy"
exit 0
