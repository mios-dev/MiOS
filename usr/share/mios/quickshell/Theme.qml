// AI-hint: MiOS brand-theme bridge for Quickshell (Law 7 / SSOT). Values are
// NOT hand-typed here as the source of truth -- FileView loads
// /etc/mios/theme/theme.json, regenerated from usr/share/mios/mios.toml
// [colors]/[theme]/[theme.font] by usr/libexec/mios/mios-sync-theme. The
// literals below are ONLY the degrade-open fallback used before the first
// sync runs (or if the bridge file is unreadable) -- they mirror the current
// mios.toml vendor defaults, they are not a second palette. Run
// `mios-sync-theme` (or `systemctl start mios-sync-theme.service`) after
// editing mios.toml [colors] to refresh the bridge this file reads.
// AI-related: /etc/mios/theme/theme.json, usr/libexec/mios/mios-sync-theme,
// usr/share/mios/quickshell/Config.qml, usr/share/mios/quickshell/PanelWindow.qml
//
// API note: uses Quickshell.Io's FileView (path / text() / textChanged()),
// per https://quickshell.org/docs/master/types/Quickshell.Io/FileView/ --
// if a future Quickshell release renames these, this is the one file that
// needs updating; Config.qml/PanelWindow.qml only ever bind to Theme's
// properties, never read the bridge file directly.

import QtQuick
import Quickshell.Io

QtObject {
    id: theme

    // Degrade-open fallback = mios.toml [colors] vendor defaults verbatim.
    property string bg:      "#282262"
    property string fg:      "#E7DFD3"
    property string accent:  "#1A407F"
    property string cursor:  "#F35C15"
    property string success: "#3E7765"
    property string warning: "#F35C15"
    property string error:   "#DC271B"
    property string subtle:  "#B7C9D7"
    property string muted:   "#948E8E"
    property string fontFamily: "GeistMono Nerd Font Mono"
    property int    radius:  10   // matches hyprland.conf decoration.rounding
    property real   panelOpacity: 0.85  // frosted-panel alpha; compositor blur does the rest

    property FileView bridge: FileView {
        path: "/etc/mios/theme/theme.json"
        watchChanges: true

        onTextChanged: {
            try {
                const t = JSON.parse(text())
                if (t.bg)          theme.bg = t.bg
                if (t.fg)          theme.fg = t.fg
                if (t.accent)      theme.accent = t.accent
                if (t.cursor)      theme.cursor = t.cursor
                if (t.success)     theme.success = t.success
                if (t.warning)     theme.warning = t.warning
                if (t.error)       theme.error = t.error
                if (t.subtle)      theme.subtle = t.subtle
                if (t.muted)       theme.muted = t.muted
                if (t.font_family) theme.fontFamily = t.font_family
                if (t.radius_px)   theme.radius = t.radius_px
            } catch (e) {
                console.warn("Theme.qml: /etc/mios/theme/theme.json present but unparsable -- staying on vendor fallback palette:", e)
            }
        }
    }

    // Helper: hex "#RRGGBB" + alpha 0..1 -> "#AARRGGBB" for Qt color props.
    function withAlpha(hex, alpha) {
        const a = Math.round(alpha * 255).toString(16).padStart(2, "0")
        return "#" + a + hex.replace("#", "")
    }
}
