// AI-hint: MiOS desktop notification toasts (Quickshell layer-shell surface,
// top-right anchored). Hyprland-native: receives dunst/mako-forwarded events
// or direct QML signal calls. Colors from Theme.qml (SSOT, mios.toml [colors]).
// AI-related: usr/share/mios/quickshell/Theme.qml, usr/share/mios/quickshell/Config.qml,
// usr/share/mios/hyprland/hyprland.conf

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland

// Notification toast model (max 4 visible, oldest auto-dismissed at 5s)
QtObject {
    id: notifRoot

    property var toasts: []

    function show(title, body, kind) {
        // kind: "info" | "success" | "warning" | "error"
        var t = { title: title, body: body, kind: kind || "info", ts: Date.now() }
        toasts = toasts.concat([t])
        if (toasts.length > 4) toasts = toasts.slice(toasts.length - 4)
        toastsChanged()
    }

    // Expose for Config.qml
    signal toastsChanged()
}
