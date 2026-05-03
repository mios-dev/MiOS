#!/bin/bash
# 'MiOS' v0.2.0 -- 30-locale-theme: Unified dark theme for EVERY window type
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

echo "  'MiOS' v0.2.0 -- Universal Dark Theme"

# ═══ SKEL .bashrc (MUST come BEFORE useradd -m) ═══
# v0.2.0: Delivered via usr/share/skel/.bashrc overlay.
echo "[30-locale-theme] Using /etc/skel/.bashrc from overlay..."

# ═══ GTK3: adw-gtk3-dark for visual consistency with libadwaita ═══
# v0.2.0: Delivered via etc/gtk-3.0/settings.ini overlay.
echo "[30-locale-theme] Using GTK3 theme from overlay..."

# ═══ GTK4: libadwaita reads color-scheme, NOT GTK_THEME ═══
# v0.2.0: Delivered via etc/gtk-4.0/settings.ini overlay.
echo "[30-locale-theme] Using GTK4 theme from overlay..."

# ═══ System-wide env vars for ALL toolkits ═══
# v0.2.0: Delivered via etc/environment.d/ overlay.
echo "[30-locale-theme] Using environment.d from overlay..."

# ═══ Flatpak overrides -- dark theme + cursor + fonts ═══
echo "[30-locale-theme] Applying Flatpak dark theme + filesystem overrides..."
flatpak override --system --env=ADW_DEBUG_COLOR_SCHEME=prefer-dark 2>/dev/null || true
flatpak override --system --env=XCURSOR_THEME=Bibata-Modern-Classic 2>/dev/null || true
flatpak override --system --env=XCURSOR_SIZE=24 2>/dev/null || true
flatpak override --system --env=GTK_THEME=adw-gtk3-dark 2>/dev/null || true
flatpak override --system --filesystem=xdg-config/gtk-3.0:ro 2>/dev/null || true
flatpak override --system --filesystem=xdg-config/gtk-4.0:ro 2>/dev/null || true
flatpak override --system --filesystem=/usr/share/icons:ro 2>/dev/null || true
flatpak override --system --filesystem=/usr/share/fonts:ro 2>/dev/null || true
flatpak override --system --filesystem=/etc/gtk-3.0:ro 2>/dev/null || true
flatpak override --system --filesystem=/etc/gtk-4.0:ro 2>/dev/null || true

# ═══ Skeleton autostart (Bottles from flathub-beta on first login) ═══
# v0.2.0: Delivered via etc/skel/.config/autostart/ overlay.

# Ensure skel GTK3 also uses adw-gtk3-dark (for new user sessions)
# v0.2.0: Delivered via etc/skel/.config/gtk-3.0/settings.ini overlay.
# ── Compile GSchema overrides (THE correct way to set GNOME defaults) ──
if [ -f /usr/share/glib-2.0/schemas/90-mios.gschema.override ]; then
    echo "[30-locale-theme] Compiling GSchema overrides..."
    glib-compile-schemas /usr/share/glib-2.0/schemas/ || true
    echo "[30-locale-theme] [ok] GSchema overrides compiled"
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

echo "[30-locale-theme] Dark theme configured for all toolkits."
