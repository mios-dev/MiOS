// AI-hint: MiOS Quickshell entry point (launched by Hyprland via
// `exec-once = quickshell --config /usr/share/mios/quickshell/Config.qml`,
// see automation/54-bake-hyprland.sh). Wires together all three shell
// surfaces: PanelWindow.qml (top status bar), Sidebar.qml (left vertical
// launcher rail), and Notifications.qml (top-right toast toaster).
// All surfaces read their palette from Theme.qml (SSOT: mios.toml [colors],
// bridged via /etc/mios/theme/theme.json).
// AI-related: usr/share/mios/quickshell/PanelWindow.qml, usr/share/mios/quickshell/Sidebar.qml,
// usr/share/mios/quickshell/Notifications.qml, usr/share/mios/quickshell/Theme.qml,
// usr/share/mios/hyprland/hyprland.conf

import QtQuick
import Quickshell

ShellRoot {
    // Top status bar: brand mark, agent status, live clock.
    PanelWindow {}

    // Left vertical launcher rail: workspace pips, agent pill, Cockpit/Terminal tiles.
    Sidebar {}

    // Top-right toast notification surface (GnomeOS-style slide-in toasts).
    // Call notifs.notify("Title", "Body", "success"|"warning"|"error"|"info")
    // from any shell surface to display a toast.
    Notifications { id: notifs }
}
