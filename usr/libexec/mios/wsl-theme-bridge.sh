#!/bin/bash
# /usr/libexec/mios/wsl-theme-bridge.sh
#
# Bridges the Windows AppsUseLightTheme registry value to GNOME's
# org.gnome.desktop.interface color-scheme + gtk-theme keys, so GTK /
# Adwaita / libadwaita apps inside MiOS-DEV (WSLg) follow the host's
# light/dark setting automatically.
#
# Why a poll loop:
#   Windows does not expose a registry-change notification across the
#   WSL2 boundary. WSLg's compositor reads the host theme for its own
#   chrome but does not propagate it to guest dbus/gsettings -- guest
#   apps query org.freedesktop.appearance via xdg-desktop-portal-gtk,
#   which reads gsettings, which reads dconf, which has no signal source
#   for the Windows side. A 15s poll is cheap (one cmd.exe registry read
#   per tick) and gsettings only writes when the value actually changes,
#   so dconf doesn't churn.
#
# Why a user service rather than system:
#   gsettings writes per-user; the bus is /run/user/$UID/bus. Running as
#   the user via mios-wsl-theme-bridge.service (user instance) avoids any
#   need to su or fiddle with DBUS_SESSION_BUS_ADDRESS plumbing.
#
# WSL-only by ConditionVirtualization in the unit; this script also
# bails if /mnt/wslg is absent (defense in depth for unusual WSL flavors
# without WSLg).

set -u

INTERVAL="${MIOS_THEME_POLL_INTERVAL:-15}"
last_scheme=""

[ -d /mnt/wslg ] || exit 0

# We need cmd.exe (preferred -- no PATH lookup quirks) or reg.exe to
# query the registry. Both come from the WSL interop layer.
if command -v cmd.exe >/dev/null 2>&1; then
    query_apps_use_light_theme() {
        cmd.exe /c reg query \
            'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' \
            /v AppsUseLightTheme 2>/dev/null \
        | tr -d '\r' \
        | awk '/AppsUseLightTheme/ {print $NF}'
    }
elif command -v reg.exe >/dev/null 2>&1; then
    query_apps_use_light_theme() {
        reg.exe query \
            'HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' \
            /v AppsUseLightTheme 2>/dev/null \
        | tr -d '\r' \
        | awk '/AppsUseLightTheme/ {print $NF}'
    }
else
    exit 0
fi

# gsettings is the write surface. If absent (gsettings-desktop-schemas
# missing), exit cleanly -- the schema gap is what really needs fixing.
command -v gsettings >/dev/null 2>&1 || exit 0

apply() {
    local scheme="$1" gtk_theme
    case "$scheme" in
        prefer-dark) gtk_theme="adw-gtk3-dark" ;;
        default)     gtk_theme="adw-gtk3" ;;
        *) return 0 ;;
    esac
    gsettings set org.gnome.desktop.interface color-scheme "$scheme" 2>/dev/null || true
    # gtk-theme is a legacy fallback for apps that don't honor
    # color-scheme yet (older GTK3, some Electron). adw-gtk3-theme ships
    # both variants; if not installed, the set is a no-op-with-warning.
    gsettings set org.gnome.desktop.interface gtk-theme "$gtk_theme" 2>/dev/null || true
}

while :; do
    case "$(query_apps_use_light_theme)" in
        0x0) scheme="prefer-dark" ;;
        0x1) scheme="default" ;;
        *)   scheme="" ;;
    esac
    if [ -n "$scheme" ] && [ "$scheme" != "$last_scheme" ]; then
        apply "$scheme"
        last_scheme="$scheme"
    fi
    sleep "$INTERVAL"
done
