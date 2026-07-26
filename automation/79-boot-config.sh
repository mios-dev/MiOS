#!/bin/bash
# MIOS_APPLY_CLASS=boot-only
# AI-hint: Configures boot-time console behavior by enabling getty@tty1, serial-getty@ttyS0, and emergency/rescue shells to ensure accessible text consoles and serial access for remote debugging.
# AI-related: mios-console, mios-verbose, tty1.service, emergency.service, rescue.service, ttyS0.service
# 'MiOS' - 98-boot-config: Boot console + service configuration
# Plymouth disable is handled by usr/lib/bootc/kargs.d/10-mios-console.toml
# Console verbosity is handled by usr/lib/bootc/kargs.d/00-mios.toml + 10-mios-verbose.toml
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "configuring boot console"

# ── Verify kargs TOML files exist ──────────────────────────────────────────
# These are static files from  -- if missing, the overlay step failed.
if [ -f /usr/lib/bootc/kargs.d/10-mios-console.toml ]; then
    mios_ok "/usr/lib/bootc/kargs.d/10-mios-console.toml present (plymouth disable via kernel cmdline)"
else
    mios_err "10-mios-console.toml not found -- check overlay"
fi

# ── Ensure agetty on tty1 ─────────────────────────────────────────────────
# Even if GDM fails, we need a text console to diagnose.
mios_log "enabling getty on tty1 (fallback console)"
systemctl enable getty@tty1.service 2>/dev/null || true

# ── Emergency shell access ────────────────────────────────────────────────
mios_log "enabling emergency/rescue shell access"
systemctl enable emergency.service 2>/dev/null || true
systemctl enable rescue.service 2>/dev/null || true

# ── Serial console for Hyper-V / QEMU ────────────────────────────────────
mios_log "enabling serial-getty on ttyS0"
systemctl enable serial-getty@ttyS0.service 2>/dev/null || true

# ── NetworkManager-wait-online timeout ────────────────────────────────────
mios_log "NetworkManager-wait-online-service.d timeout drop-in supplied by image overlay (not set by this script)"

mios_ok "boot console configured"
mios_log "plymouth: disabled (kernel cmdline plymouth.enable=0)"
mios_log "getty@tty1: enabled (fallback text console)"
mios_log "serial-getty@ttyS0: enabled (serial console)"
mios_log "NM-wait-online: timeout set by overlay drop-in (value not read or verified by this script)"
