#!/usr/bin/env bash
# MIOS_INSTALLER_ROLE=fhs-overlay-installer
# AI-hint: Installs the MiOS FHS overlay onto non-bootc Fedora hosts by syncing usr/etc/var/srv directories, materi...
# AI-doc: usr/share/doc/mios/manual/automation.md

set -euo pipefail

if command -v bootc >/dev/null 2>&1 && bootc status --format=json 2>/dev/null | grep -q '"booted"'; then
    echo "[FAIL] This host is bootc-managed. install.sh is for non-bootc Fedora hosts" >&2
    echo "       Use 'sudo bootc switch ghcr.io/MiOS-DEV/mios:latest' instead" >&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "[FAIL] install.sh must run as root: sudo $0" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[INFO] 'MiOS' system installer running from ${REPO_ROOT}"

if [[ "${REPO_ROOT}" != "/" ]]; then
    for d in usr etc var srv; do
        if [[ -d "${REPO_ROOT}/${d}" ]]; then
            echo "[INFO] Applying overlay: ${d}/"
            rsync -aH --info=stats1 "${REPO_ROOT}/${d}/" "/${d}/"
        fi
    done

    if [[ -d "${REPO_ROOT}/v1" ]]; then
        echo "[INFO] Materializing /v1 discovery surface"
        install -d /v1
        rsync -aH "${REPO_ROOT}/v1/" "/v1/"
    fi
else
    echo "[INFO] Running directly from root, skipping overlay sync"
fi
echo "[INFO] Running systemd-sysusers"
systemd-sysusers

echo "[INFO] Running systemd-tmpfiles"
systemd-tmpfiles --create

echo "[INFO] Reloading systemd"
systemctl daemon-reload

echo "[INFO] Quadlet .container units laid down under /etc/containers/systemd; systemd generator instantiates them on next daemon-reload/boot"

echo "[ OK ] 'MiOS' system installer complete"
echo "       Log out and back in to pick up profile changes"
