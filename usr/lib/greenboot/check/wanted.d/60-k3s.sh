#!/bin/bash
# AI-hint: Advisory greenboot check that verifies K3s service activity and kubeconfig accessibility; used by agents to detect K3s health issues without triggering rollbacks on non-k3s roles.
# AI-related: mios-greenboot
set -euo pipefail

TIMEOUT=60

if ! systemctl is-enabled --quiet k3s 2>/dev/null; then
    echo "[mios-greenboot] K3s not enabled on this role"
    exit 0
fi

echo "[mios-greenboot] K3s enabled"

deadline=$(( $(date +%s) + TIMEOUT ))
while true; do
    if systemctl is-active --quiet k3s 2>/dev/null; then
        echo "[mios-greenboot] K3s is active"
        break
    fi
    if [[ $(date +%s) -ge $deadline ]]; then
        echo "[mios-greenboot] WARNING: K3s did not become active within ${TIMEOUT}s" >&2
        exit 1
    fi
    sleep 3
done

if [[ ! -r /etc/rancher/k3s/k3s.yaml ]]; then
    echo "[mios-greenboot] WARNING: K3s kubeconfig not readable" >&2
    exit 1
fi

if kubectl --kubeconfig /etc/rancher/k3s/k3s.yaml get nodes --no-headers 2>/dev/null \
        | grep -q "Ready"; then
    echo "[mios-greenboot] K3s node is Ready"
    exit 0
else
    echo "[mios-greenboot] WARNING: K3s node not yet in Ready state" >&2
    exit 1
fi
