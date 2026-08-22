# AI-hint: !/usr/bin/bash Verifies the booted kernel enforces the lockdown mode the image kargs declare (`lockdown=integrity` in usr/lib/bootc/karg...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_greenboot_check_wanted_d_31_kernel_lockdown_sh.md
set -euo pipefail
LOCKDOWN_FILE=/sys/kernel/security/lockdown
if [[ -r "${LOCKDOWN_FILE}" ]]; then
    if ! grep -q '\[integrity\]' "${LOCKDOWN_FILE}"; then
        echo "kernel lockdown mode is '$(cat "${LOCKDOWN_FILE}")' -- image kargs declare lockdown=integrity"
        exit 1
    fi
fi
