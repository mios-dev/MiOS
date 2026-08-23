#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Fixes boot-time failures by restoring execution bits on MiOS binaries, correcting USBGuard permissions, resolvi...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "Restore +x on mios binaries, usbguard 0600, systemd-sysusers systemd-resolve"

if [ -f /etc/usbguard/usbguard-daemon.conf ]; then
    chmod 0600 /etc/usbguard/usbguard-daemon.conf
fi
if [ -f /etc/usbguard/rules.conf ]; then
    chmod 0600 /etc/usbguard/rules.conf
fi


find ${MIOS_LIBEXEC_DIR} -type f -exec chmod +x {} \; || true
find /usr/libexec -type f \( -name 'mios-*' -o -name 'role-apply' -o -name 'selinux-init' -o -name 'gpu-detect' -o -name 'cpu-isolate' -o -name 'motd' -o -name 'dash' -o -name 'sb-audit' -o -name 'wsl-init' -o -name 'wsl-firstboot' -o -name 'sb-keygen' -o -name 'tpm-enroll' \) -exec chmod +x {} \; || true
find /usr/bin -name 'mios-*' -type f -exec chmod +x {} \; || true

for hook in /etc/libvirt/hooks/qemu /usr/lib/libvirt/hooks/qemu; do
    if [ -f "$hook" ]; then
        chmod +x "$hook"
    fi
done

if [ -f /usr/lib/sysusers.d/systemd-resolve.conf ]; then
    systemd-sysusers /usr/lib/sysusers.d/systemd-resolve.conf || true
fi


mios_skip "OCI/WSL2 service gating: ConditionVirtualization drop-ins ship in system_files overlay"


