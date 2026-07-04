#!/bin/bash
# AI-hint: Installs Hyprland tiling compositor, XWayland, window routing helpers, and constructs the base layout configuration inside /usr/share/mios/hyprland/hyprland.conf.
# AI-related: /usr/share/mios/hyprland/hyprland.conf, /usr/bin/hyprland
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

echo "[54-bake-hyprland] Installing Hyprland compositor & tools..."
install_packages_strict "hyprland"

echo "[54-bake-hyprland] Generating baseline Hyprland configuration..."
mkdir -p /usr/share/mios/hyprland
cat << 'EOF' > /usr/share/mios/hyprland/hyprland.conf
# =============================================================================
# MiOS Tiling Display Compositor Settings (Hyprland 0.46+)
# =============================================================================

# Monitors (automatic resolution and HiDPI scaling resolution translation)
monitor=,preferred,auto,1

# Input devices
input {
    kb_layout = us
    follow_mouse = 1
    sensitivity = 0 # -1.0 - 1.0, 0 means no modification
    touchpad {
        natural_scroll = true
    }
}

# General layout behavior
general {
    gaps_in = 5
    gaps_out = 10
    border_size = 2
    col.active_border = rgba(@@MIOS_COLOR_ACCENT@@ee) rgba(@@MIOS_COLOR_INFO@@ee) 45deg
    col.inactive_border = rgba(@@MIOS_COLOR_MUTED@@aa)
    layout = dwindle
    allow_tearing = false
}

# Frosted glass aesthetics / transparency
decoration {
    rounding = 10
    blur {
        enabled = true
        size = 8
        passes = 3
        new_optimizations = true
        xray = true
        noise = 0.01
        contrast = 0.9
        brightness = 0.8
    }
    drop_shadow = true
    shadow_range = 4
    shadow_render_power = 3
    col.shadow = rgba(1a1a1aee)
}

# Dynamic micro-animations
animations {
    enabled = true
    bezier = myBezier, 0.05, 0.9, 0.1, 1.05
    animation = windows, 1, 7, myBezier
    animation = windowsOut, 1, 7, default, popin 80%
    animation = border, 1, 10, default
    animation = borderangle, 1, 8, default
    animation = fade, 1, 7, default
    animation = workspaces, 1, 6, default
}

# Window Rules (promoting native GUI wrappers)
windowrulev2 = suppressevent maximize, class:.*
windowrulev2 = float, class:^(mios-webshell)$
windowrulev2 = size 1200 800, class:^(mios-webshell)$

# Cockpit (real, already wired -- usr/lib/systemd/system/cockpit.socket.d/
# listen.conf + usr/share/containers/systemd/mios-cockpit-link.container),
# opened via the $mainMod, C keybind below or the Quickshell Sidebar.qml tile.
windowrulev2 = float, class:^(cockpit)$
windowrulev2 = size 1400 900, class:^(cockpit)$

# Layer-shell blur for the Quickshell top bar + vertical rail (Config.qml /
# PanelWindow.qml / Sidebar.qml already render themselves semi-transparent
# via Theme.qml's panelOpacity; this makes that translucency read as real
# frosted glass instead of a flat tint, matching decoration.blur above and
# the operator's standing acrylic/frameless directive in mios.toml [theme]).
layerrule = blur, quickshell
layerrule = ignorezero, quickshell

# Startup applications (Quickshell Status Bar)
exec-once = quickshell --config /usr/share/mios/quickshell/Config.qml

# Environment setup for systemd user session
exec-once = systemctl --user import-environment WAYLAND_DISPLAY XDG_CURRENT_DESKTOP
exec-once = dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP
exec-once = systemctl --user start graphical-session.target

# Window management keybindings (Mod key = Super/Windows key)
$mainMod = SUPER

bind = $mainMod, Q, killactive,
bind = $mainMod, M, exit,
bind = $mainMod, E, exec, mios-webshell
bind = $mainMod, V, togglefloating,
bind = $mainMod, R, exec, rofi -show drun
bind = $mainMod, P, pseudo, # dwindle
bind = $mainMod, J, togglesplit, # dwindle
bind = $mainMod, C, exec, xdg-open http://localhost:9090 # Cockpit -- real, see mios-cockpit-link.container

# Focus movements
bind = $mainMod, left, movefocus, l
bind = $mainMod, right, movefocus, r
bind = $mainMod, up, movefocus, u
bind = $mainMod, down, movefocus, d

# Workspace switching
bind = $mainMod, 1, workspace, 1
bind = $mainMod, 2, workspace, 2
bind = $mainMod, 3, workspace, 3
bind = $mainMod, 4, workspace, 4
bind = $mainMod, 5, workspace, 5

# Move active window to workspace
bind = $mainMod SHIFT, 1, movetoworkspace, 1
bind = $mainMod SHIFT, 2, movetoworkspace, 2
bind = $mainMod SHIFT, 3, movetoworkspace, 3
bind = $mainMod SHIFT, 4, movetoworkspace, 4
bind = $mainMod SHIFT, 5, movetoworkspace, 5
EOF

# SSOT color substitution (Law 7): tools/lib/userenv.sh (sourced above via
# lib/packages.sh -> lib/common.sh, the same convention every other
# automation/*.sh script uses) already exports MIOS_COLOR_* from mios.toml
# [colors]. The heredoc above stays single-quoted on purpose -- it also
# contains literal Hyprland variable references ($mainMod) that must NOT be
# shell-expanded -- so the brand palette is substituted here via placeholder
# tokens instead of inline interpolation. Previously this file hardcoded a
# neon cyan/green gradient (rgba(33ccffee)/rgba(00ff99ee)) with no
# relationship to the rest of the OS; see design spec
# usr/share/doc/mios/concepts/mios-app-browser-portal-dashboard-design-2026-07-03.md §7/§12.
: "${MIOS_COLOR_ACCENT:=#1A407F}"
: "${MIOS_COLOR_INFO:=#1A407F}"
: "${MIOS_COLOR_MUTED:=#948E8E}"
sed -i \
    -e "s/@@MIOS_COLOR_ACCENT@@/${MIOS_COLOR_ACCENT#\#}/g" \
    -e "s/@@MIOS_COLOR_INFO@@/${MIOS_COLOR_INFO#\#}/g" \
    -e "s/@@MIOS_COLOR_MUTED@@/${MIOS_COLOR_MUTED#\#}/g" \
    /usr/share/mios/hyprland/hyprland.conf

chmod 0644 /usr/share/mios/hyprland/hyprland.conf
echo "[54-bake-hyprland] Baseline configuration written successfully."
