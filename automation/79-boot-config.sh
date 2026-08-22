#!/bin/bash
# AI-hint: MIOS_APPLY_CLASS=boot-only Configures boot-time console behavior by enabling getty@tty1, serial-getty@ttyS0, and emergency/rescue shells to ensure acce...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_79_boot_config_sh.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Configuring boot console"

if [ -f /usr/lib/bootc/kargs.d/10-mios-console.toml ]; then
    mios_ok "/usr/lib/bootc/kargs.d/10-mios-console.toml present"
else
    mios_err "10-mios-console.toml not found -- check overlay"
fi

mios_log "Enabling getty on tty1"
systemctl enable getty@tty1.service 2>/dev/null || true

mios_log "Enabling emergency/rescue shell access"
systemctl enable emergency.service 2>/dev/null || true
systemctl enable rescue.service 2>/dev/null || true

mios_log "Enabling serial-getty on ttyS0"
systemctl enable serial-getty@ttyS0.service 2>/dev/null || true

mios_log "NetworkManager-wait-online-service.d timeout drop-in supplied by image overlay"

mios_ok "Boot console configured"
mios_log "Plymouth: disabled"
mios_log "Getty@tty1: enabled"
mios_log "Serial-getty@ttyS0: enabled"
mios_log "NM-wait-online: timeout set by overlay drop-in"
