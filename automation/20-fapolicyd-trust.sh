#!/usr/bin/env bash
set -euo pipefail

echo "==> Configuring fapolicyd for fs-verity/ComposeFS..."

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# Configure fapolicyd to use the file trust backend (fs-verity)
# This allows 0-second boot delays while maintaining rigid application whitelisting
# in immutable ComposeFS environments.
#
# v0.1.4: USR-OVER-ETC alignment. Update both /usr/lib and /etc.
for config in /usr/lib/fapolicyd/fapolicyd.conf /etc/fapolicyd/fapolicyd.conf; do
    if [[ -f "$config" ]]; then
        sed -i 's/^trust =.*/trust = file,rpmdb/' "$config" || true
    fi
done

# Enable the service
systemctl enable fapolicyd.service
echo "==> fapolicyd configured successfully."
