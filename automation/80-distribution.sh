#!/bin/bash
# AI-hint: Enable mios-oci-delta-apply.service (GAP-5)

set -euo pipefail

if [[ -f /usr/lib/systemd/system/mios-oci-delta-apply.service ]]; then
    echo "Enabling mios-oci-delta-apply.service..."
    systemctl enable mios-oci-delta-apply.service || true
fi
