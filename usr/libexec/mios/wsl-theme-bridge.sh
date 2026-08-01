#!/bin/bash
# AI-hint: Bridges the Windows AppsUseLightTheme registry value to GNOME's
# AI-related: /usr/libexec/mios/wsl-theme-bridge.sh, mios-wsl-theme-bridge, mios-wsl-theme-bridge.service
# AI-functions: query_apps_use_light_theme, apply
set -euo pipefail

set -u

INTERVAL="${MIOS_THEME_POLL_INTERVAL:-15}"
last_scheme=""

[ -d /mnt/wslg ] || exit 0

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

command -v gsettings >/dev/null 2>&1 || exit 0

apply() {
    local scheme="$1" gtk_theme
    case "$scheme" in
        prefer-dark) gtk_theme="adw-gtk3-dark" ;;
        default)     gtk_theme="adw-gtk3" ;;
        *) return 0 ;;
    esac
    gsettings set org.gnome.desktop.interface color-scheme "$scheme" 2>/dev/null || true
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
