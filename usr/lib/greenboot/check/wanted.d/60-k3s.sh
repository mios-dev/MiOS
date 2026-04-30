#!/bin/bash
# MiOS greenboot — advisory K3s readiness check (wanted.d = no rollback on fail)
# Logs a warning if K3s is enabled but not healthy after boot.
# Lives in wanted.d so desktop/hybrid roles (where K3s is disabled) never fail.
set -euo pipefail

TIMEOUT=60

# Skip entirely if K3s is not enabled for this role
if ! systemctl is-enabled --quiet k3s 2>/dev/null; then
    echo "[mios-greenboot] K3s not enabled on this role — skipping check."
    exit 0
fi

echo "[mios-greenboot] K3s enabled — waiting up to ${TIMEOUT}s for active state..."

# Wait for K3s to reach active state
deadline=$(( $(date +%s) + TIMEOUT ))
while true; do
    if systemctl is-active --quiet k3s 2>/dev/null; then
        echo "[mios-greenboot] K3s is active."
        break
    fi
    if [[ $(date +%s) -ge $deadline ]]; then
        echo "[mios-greenboot] WARNING: K3s did not become active within ${TIMEOUT}s." >&2
        exit 1
    fi
    sleep 3
done

# Verify kubeconfig is accessible (k3s writes it to /etc/rancher/k3s/k3s.yaml)
if [[ ! -r /etc/rancher/k3s/k3s.yaml ]]; then
    echo "[mios-greenboot] WARNING: K3s kubeconfig not readable." >&2
    exit 1
fi

# Quick node Ready check (non-fatal on transient NotReady during first boot)
if kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml get nodes --no-headers 2>/dev/null \
        | grep -q "Ready"; then
    echo "[mios-greenboot] K3s node is Ready."
    exit 0
else
    echo "[mios-greenboot] WARNING: K3s node not yet in Ready state." >&2
    exit 1
fi
