#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures a unified dark theme across all UI toolkits (GTK3/4, Qt5/6, Electron, Flatpak) by applying dconf settings, environment variables, and global Flatpak overrides.
# AI-related: mios-flatpak-init
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "'MiOS' ${MIOS_VERSION:-} locale + dark theme"

mios_skip "/etc/skel/.bashrc via usr/share/skel overlay"

mios_skip "GTK3 theme via etc/gtk-3.0/settings.ini overlay"

mios_skip "GTK4 theme via etc/gtk-4.0/settings.ini overlay"

mios_skip "toolkit env vars via etc/environment.d/ overlay"

mios_log "Flatpak global dark theme + cursor overrides"
flatpak override --system --env=ADW_DEBUG_COLOR_SCHEME=prefer-dark 2>/dev/null || true
flatpak override --system --env=XCURSOR_THEME=Bibata-Modern-Classic 2>/dev/null || true
flatpak override --system --env=XCURSOR_SIZE=24 2>/dev/null || true
flatpak override --system --env=GTK_THEME=adw-gtk3-dark 2>/dev/null || true
flatpak override --system --filesystem=xdg-config/gtk-3.0:ro 2>/dev/null || true
flatpak override --system --filesystem=xdg-config/gtk-4.0:ro 2>/dev/null || true
flatpak override --system --filesystem=xdg-data/icons:ro 2>/dev/null || true
flatpak override --system --filesystem=xdg-data/themes:ro 2>/dev/null || true
flatpak override --system --filesystem=/etc/gtk-3.0:ro 2>/dev/null || true
flatpak override --system --filesystem=/etc/gtk-4.0:ro 2>/dev/null || true
flatpak override --system --nofilesystem=/usr/share/themes 2>/dev/null || true
flatpak override --system --nofilesystem=/usr/share/icons 2>/dev/null || true
flatpak override --system --nofilesystem=/usr/share/fonts 2>/dev/null || true

if [ -f /usr/share/glib-2.0/schemas/90-mios.gschema.override ]; then
    mios_log "GSchema overrides compile"
    glib-compile-schemas /usr/share/glib-2.0/schemas/ || true
    mios_ok "GSchema overrides compiled"
fi

export GIO_USE_VFS=local
dconf update || true

if [ -d /etc/dconf/db ]; then
    mkdir -p /usr/share/dconf/db
    find /etc/dconf/db -maxdepth 1 -type f -exec mv -f {} /usr/share/dconf/db/ \; 2>/dev/null || true
fi

mios_ok "System Flatpak overrides, 90-mios.gschema.override, dconf update applied"
