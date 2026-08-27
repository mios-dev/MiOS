#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures Hyper-V Enhanced Session support by enabling hv_sock, configuring gnome-remote-desktop for Wayland-native RDP via v...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Chmod cockpit.socket.d/listen.conf, append hv_sock to modules-load.d/mios.conf, enable mios-hyperv-enhanced.service"

if [ -f /usr/lib/systemd/system/cockpit.socket.d/listen.conf ]; then
    chmod 644 /usr/lib/systemd/system/cockpit.socket.d/listen.conf
fi

mios_log "Hyper-V Enhanced Session"

if ! grep -q 'hv_sock' /usr/lib/modules-load.d/mios.conf 2>/dev/null; then
    echo "Hv_sock" >> /usr/lib/modules-load.d/mios.conf
fi

systemctl enable mios-hyperv-enhanced.service 2>/dev/null || true

chmod +x /usr/libexec/mios-grd-setup 2>/dev/null || true

mios_ok "VM gating + Hyper-V Enhanced Session configured"
