#!/usr/bin/bash
# AI-hint: Validates that the mios-role.service is active and the local role file exists before proceeding with greenboot checks.
# AI-related: mios-role, mios-role.service
# Required: mios-role.service must have succeeded
set -euo pipefail
systemctl is-active --quiet mios-role.service || {
    echo "mios-role.service is not active"
    exit 1
}
test -f /var/lib/mios/role.active