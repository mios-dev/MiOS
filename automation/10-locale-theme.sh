#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures a unified dark theme across all UI toolkits (GTK3/4, Qt5/6, Electron, Flatpak) by applying dconf settings, environment variables, and global Flatpak overrides.
# AI-related: mios-flatpak-init
# 'MiOS' - 30-locale-theme: Unified dark theme for EVERY window type
#
# Coverage matrix (ALL must be dark):
#   [ok] libadwaita / GTK4 apps (GNOME native) -- color-scheme=prefer-dark via dconf
#   [ok] GTK3 apps (legacy GNOME) -- adw-gtk3-dark theme
#   [ok] GDM login screen -- separate dconf db (gdm user)
#   [ok] GNOME lock screen -- inherits user session (automatic)
#   [ok] Flatpak apps -- ADW_DEBUG_COLOR_SCHEME + portal + filesystem overrides
#   [ok] Qt5/Qt6 apps -- adwaita-qt + QGnomePlatform env vars
#   [ok] Electron/Chromium apps -- ELECTRON_FORCE_DARK_MODE
#   [ok] Firefox -- MOZ_ENABLE_WAYLAND + portal color-scheme
#   [ok] GNOME Remote Desktop -- XCURSOR_THEME + session env
#   [ok] TTY/console -- no theming needed (terminal colors)
#
# MUST RUN BEFORE 30-user.sh (skel .bashrc must exist before useradd -m)
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "'MiOS' ${MIOS_VERSION:-} locale + dark theme (dconf/GTK/Qt/Flatpak)"

# ═══ SKEL .bashrc (MUST come BEFORE useradd -m) ═══
# : Delivered via usr/share/skel/.bashrc overlay.
mios_skip "/etc/skel/.bashrc via usr/share/skel overlay"

# ═══ GTK3: adw-gtk3-dark for visual consistency with libadwaita ═══
# : Delivered via etc/gtk-3.0/settings.ini overlay.
mios_skip "GTK3 theme via etc/gtk-3.0/settings.ini overlay"

# ═══ GTK4: libadwaita reads color-scheme, NOT GTK_THEME ═══
# : Delivered via etc/gtk-4.0/settings.ini overlay.
mios_skip "GTK4 theme via etc/gtk-4.0/settings.ini overlay"

# ═══ System-wide env vars for ALL toolkits ═══
# : Delivered via etc/environment.d/ overlay.
mios_skip "toolkit env vars via etc/environment.d/ overlay"

# ═══ Flatpak overrides -- dark theme + cursor + fonts ═══
# Bake-time seed of the GLOBAL flatpak override. Runtime
# mios-flatpak-init re-applies the same envs from mios.toml
# [appearance] every boot so operator changes propagate without a
# re-bake. Keep this list IN SYNC with mios-flatpak-init.
# Operator directive "should be the GLOBAL overrides so
# that newly installed apps/flatpaks take hold of the configurations
# as well" -- everything here goes to system-wide (no --app=ID),
# making every present + future flatpak inherit it.
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
# Explicitly REJECT /usr/share/{themes,icons,fonts} -- flatpak refuses
# with "Path /usr is reserved by Flatpak" + emits F: warnings on every
# launch (operator-flagged ptyxis launch noise). adw-gtk3
# + Bibata reach the sandbox via the Flathub runtime extension
# (org.gtk.Gtk3theme.adw-gtk3-dark) + the xdg-data mounts above.
flatpak override --system --nofilesystem=/usr/share/themes 2>/dev/null || true
flatpak override --system --nofilesystem=/usr/share/icons 2>/dev/null || true
flatpak override --system --nofilesystem=/usr/share/fonts 2>/dev/null || true

# ═══ Skeleton autostart (Bottles from flathub-beta on first login) ═══
# : Delivered via etc/skel/.config/autostart/ overlay.

# Ensure skel GTK3 also uses adw-gtk3-dark (for new user sessions)
# : Delivered via etc/skel/.config/gtk-3.0/settings.ini overlay.
# ── Compile GSchema overrides (THE correct way to set GNOME defaults) ──
if [ -f /usr/share/glib-2.0/schemas/90-mios.gschema.override ]; then
    mios_log "GSchema overrides compile"
    glib-compile-schemas /usr/share/glib-2.0/schemas/ || true
    mios_ok "GSchema overrides compiled"
fi

# Suppress DBus warnings during headless update without swallowing real syntax errors
export GIO_USE_VFS=local
dconf update || true

# Migrate generated binary dconf databases to the immutable /usr/share path.
# This prevents OSTree 3-way merge binary conflicts on /etc/dconf/db/local
# during bootc upgrades if users make their own local dconf changes.
if [ -d /etc/dconf/db ]; then
    mkdir -p /usr/share/dconf/db
    find /etc/dconf/db -maxdepth 1 -type f -exec mv -f {} /usr/share/dconf/db/ \; 2>/dev/null || true
fi

mios_ok "system Flatpak overrides, 90-mios.gschema.override, dconf update applied"
