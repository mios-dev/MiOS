#!/usr/bin/env bash
# MiOS system-side installer (FHS overlay path).
#
# This script is invoked by the bootstrap installer on non-bootc Fedora hosts.
# On bootc-managed hosts, do NOT run this -- use `bootc switch` instead.
#
# What it does:
#   1. Refuses to run on bootc-managed hosts (their /usr is read-only composefs).
#   2. Lays down the FHS overlay from this repository's working tree to /.
#   3. Runs systemd-sysusers, systemd-tmpfiles, and reloads systemd units.
#   4. Enables MiOS services.

set -euo pipefail

# Refuse to run on bootc-managed hosts.
if command -v bootc >/dev/null 2>&1 && bootc status --format=json 2>/dev/null | grep -q '"booted"'; then
    echo "[FAIL] This host is bootc-managed. install.sh is for non-bootc Fedora hosts." >&2
    echo "       Use 'sudo bootc switch ghcr.io/mios-fss/mios:latest' instead." >&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "[FAIL] install.sh must run as root: sudo $0" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[INFO] MiOS system installer running from ${REPO_ROOT}"

# Apply FHS overlay. We rsync each top-level overlay dir if it exists.
for d in usr etc var srv; do
    if [[ -d "${REPO_ROOT}/${d}" ]]; then
        echo "[INFO] Applying overlay: ${d}/"
        rsync -aH --info=stats1 "${REPO_ROOT}/${d}/" "/${d}/"
    fi
done

# v1/ holds discovery symlinks; we materialize them at /v1.
if [[ -d "${REPO_ROOT}/v1" ]]; then
    echo "[INFO] Materializing /v1 discovery surface"
    install -d /v1
    rsync -aH "${REPO_ROOT}/v1/" "/v1/"
fi

echo "[INFO] Running systemd-sysusers"
systemd-sysusers

echo "[INFO] Running systemd-tmpfiles"
systemd-tmpfiles --create

echo "[INFO] Reloading systemd"
systemctl daemon-reload

echo "[INFO] Enabling MiOS services"
if [[ -f /etc/containers/systemd/mios-ai.container ]]; then
    systemctl enable --now mios-ai.service || echo "[WARN] mios-ai.service not yet active; will retry on boot"
fi

echo "[ OK ] MiOS system installer complete."
echo "       Log out and back in (or reboot) to pick up profile changes."
