#!/usr/bin/bash
# Required: mios-role.service must have succeeded
set -euo pipefail
systemctl is-active --quiet mios-role.service || {
    echo "mios-role.service is not active"
    exit 1
}
test -f /var/lib/mios/role.active