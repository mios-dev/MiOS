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

# Frosted glass aesthetics / transparency (multi-layer "liquid glass")
decoration {
    rounding = 12
    active_opacity = 1.0
    inactive_opacity = 0.94
    fullscreen_opacity = 1.0
    blur {
        enabled = true
        size = 8
        passes = 4
        new_optimizations = true
        xray = true
        ignore_opacity = true
        noise = 0.012
        contrast = 1.05
        brightness = 0.85
        vibrancy = 0.20
        vibrancy_darkness = 0.10
        popups = true           # frost drop-down menus / context popups too
        popups_ignorealpha = 0.2
    }
    drop_shadow = true
    shadow_range = 18
    shadow_render_power = 3
    shadow_offset = 0 4
    col.shadow = rgba(10101088)
    col.shadow_inactive = rgba(10101044)
    dim_inactive = true
    dim_strength = 0.06
}

# Dynamic micro-animations -- overshoot beziers approximate a spring/"liquid"
# feel and are safe on Hyprland 0.46+ (native spring curves are 0.55+, adopt
# once the baked Hyprland reaches it). Layer animations glide the Quickshell
# shell surfaces in. NOTE: borderangle is intentionally NOT looped -- looping it
# defeats VFR and drains battery even when the window is obscured (Hyprland wiki).
animations {
    enabled = true
    bezier = liquid,    0.25, 1.30, 0.35, 1.00
    bezier = smoothOut, 0.36, 0.00, 0.66, -0.56
    bezier = smoothIn,  0.25, 1.00, 0.50, 1.00
    bezier = myBezier,  0.05, 0.90, 0.10, 1.05
    animation = windows,     1, 5, myBezier, popin 60%
    animation = windowsIn,   1, 5, myBezier, popin 60%
    animation = windowsOut,  1, 4, smoothOut, popin 80%
    animation = windowsMove,  1, 4, liquid
    animation = border,      1, 10, default
    animation = borderangle, 1, 8, default
    animation = fade,        1, 5, smoothIn
    animation = fadeIn,      1, 5, smoothIn
    animation = fadeOut,     1, 5, smoothOut
    animation = workspaces,  1, 5, liquid, slide
    animation = layers,      1, 4, myBezier, slide
    animation = layersIn,    1, 4, myBezier, slide
    animation = layersOut,   1, 4, smoothOut, slide
}

# Liquid-glass on the shell's OWN layer surfaces (Quickshell bar + rail, rofi,
# notifications, drop-downs). Compositor blur is what actually frosts them --
# the QML only sets a translucent fill. Closes the gap documented in the header
# of usr/share/mios/quickshell/Sidebar.qml (`layerrule = blur, quickshell`).
layerrule = blur, quickshell
layerrule = ignorealpha 0.2, quickshell
layerrule = blur, rofi
layerrule = ignorealpha 0.5, rofi
layerrule = blur, notifications
layerrule = ignorealpha 0.3, notifications

# Window Rules (promoting native GUI wrappers)
windowrulev2 = suppressevent maximize, class:.*
windowrulev2 = float, class:^(mios-webshell)$
windowrulev2 = size 1200 800, class:^(mios-webshell)$

# Cockpit (real, already wired -- usr/lib/systemd/system/cockpit.socket.d/
# listen.conf + usr/share/containers/systemd/mios-cockpit-link.container),
# opened via the $mainMod, C keybind below or the Quickshell Sidebar.qml tile.
windowrulev2 = float, class:^(cockpit)$
windowrulev2 = size 1400 900, class:^(cockpit)$

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
# usr/share/doc/mios/concepts/mios-app-browser-portal-dashboard-design-*.md §7/§12.
: "${MIOS_COLOR_ACCENT:=#1A407F}"
: "${MIOS_COLOR_INFO:=#1A407F}"
: "${MIOS_COLOR_MUTED:=#948E8E}"
sed -i \
    -e "s/@@MIOS_COLOR_ACCENT@@/${MIOS_COLOR_ACCENT#\#}/g" \
    -e "s/@@MIOS_COLOR_INFO@@/${MIOS_COLOR_INFO#\#}/g" \
    -e "s/@@MIOS_COLOR_MUTED@@/${MIOS_COLOR_MUTED#\#}/g" \
    /usr/share/mios/hyprland/hyprland.conf

chmod 0644 /usr/share/mios/hyprland/hyprland.conf
echo "[54-bake-hyprland] Wrote /usr/share/mios/hyprland/hyprland.conf (MIOS_COLOR_ACCENT/INFO/MUTED tokens substituted from mios.toml [colors])."
