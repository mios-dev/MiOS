#!/usr/bin/bash
# AI-hint: Verifies the booted kernel enforces the lockdown mode the image kargs declare (`lockdown=integrity` in usr/lib/bootc/karg...
# AI-doc: usr/share/doc/mios/manual/system.md
set -euo pipefail
LOCKDOWN_FILE=/sys/kernel/security/lockdown
if [[ -r "${LOCKDOWN_FILE}" ]]; then
    if ! grep -q '\[integrity\]' "${LOCKDOWN_FILE}"; then
        echo "kernel lockdown mode is '$(cat "${LOCKDOWN_FILE}")' -- image kargs declare lockdown=integrity"
        exit 1
    fi
fi
