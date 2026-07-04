// AI-hint: MiOS Quickshell entry point (launched by Hyprland via
// `exec-once = quickshell --config /usr/share/mios/quickshell/Config.qml`,
// see automation/54-bake-hyprland.sh). Wires together the two shell
// surfaces: PanelWindow.qml (top status bar) and Sidebar.qml (left vertical
// launcher rail). Both read their palette from Theme.qml (SSOT: mios.toml
// [colors], bridged via /etc/mios/theme/theme.json -- see that file's
// header) instead of the hardcoded Catppuccin Mocha hex this file used to
// contain directly.
// AI-related: usr/share/mios/quickshell/PanelWindow.qml, usr/share/mios/quickshell/Sidebar.qml,
// usr/share/mios/quickshell/Theme.qml, usr/share/mios/hyprland/hyprland.conf

import QtQuick
import Quickshell

ShellRoot {
    // Top status bar: brand mark, agent status, clock.
    PanelWindow {}

    // Left vertical launcher rail: workspaces, agent pill, Cockpit tile, clock.
    Sidebar {}
}
