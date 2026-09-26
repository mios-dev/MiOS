#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs Hyprland tiling compositor, XWayland, window routing helpers, and constructs the base layout configuration inside...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
# shellcheck source=/dev/null
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

mios_log "Installing Hyprland compositor & tools"
install_packages_strict "hyprland"

# Render each imperative generator's installed surface from the merged build SSOT (MIOS_VENDOR_TOML), so operator edits ship.
for _gen in ux/wm_config_gen.py desktop/gpu_terminal.py win/wt_profile_inject.py ux/tmux_theme.py; do
    python3 "/usr/libexec/mios/${_gen}" --write-fixture /
done
mios_ok "Rendered Hyprland, Sway, Alacritty, WSL terminal profile and tmux theme from mios.toml"

mkdir -p /usr/share/wayland-sessions
cat << 'EOF' > /usr/share/wayland-sessions/hyprland.desktop
[Desktop Entry]
Name=Hyprland
Comment=An intelligent dynamic tiling Wayland compositor
Exec=Hyprland
Type=Application
DesktopNames=Hyprland
EOF
chmod 0644 /usr/share/wayland-sessions/hyprland.desktop
mios_ok "Registered /usr/share/wayland-sessions/hyprland.desktop"

mkdir -p /etc/hypr
if [[ ! -e /etc/hypr/hyprland.conf ]]; then
    ln -sf /usr/share/mios/hyprland/hyprland.conf /etc/hypr/hyprland.conf
fi
