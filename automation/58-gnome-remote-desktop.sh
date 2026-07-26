#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures GNOME Remote Desktop for Wayland-native RDP support and masks legacy xrdp services to ensure a clean remote desktop environment in MiOS.
# AI-related: xrdp.service, xrdp-sesman.service
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "mask xrdp.service, xrdp-sesman.service; GNOME Remote Desktop via 90-mios.preset"

# Pre-emptively disable/mask legacy xrdp services just in case they bleed in from a base image
systemctl mask xrdp.service xrdp-sesman.service 2>/dev/null || true

# GNOME Remote Desktop handles Wayland headless RDP natively.
# Enablement is handled via usr/lib/systemd/system-preset/90-mios.preset
# Drop-in to wait for network is delivered via system_files overlay.

mios_ok "xrdp.service, xrdp-sesman.service masked"
