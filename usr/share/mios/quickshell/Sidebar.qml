// AI-hint: MiOS left-anchored vertical launcher rail (Quickshell layer-shell
// surface). This is the "frameless side panel / vertical tabs" element of
// the desktop shell -- workspace pips, an agent-status pill, a one-click
// Cockpit tile (Cockpit is real and already wired: see
// usr/lib/systemd/system/cockpit.socket.d/listen.conf and
// usr/share/containers/systemd/mios-cockpit-link.container), and the clock.
// Colors/typography come from Theme.qml (SSOT, mios.toml [colors]) instead
// of hardcoded hex.
// AI-related: usr/share/mios/quickshell/Theme.qml, usr/share/mios/quickshell/Config.qml,
// usr/share/mios/hyprland/hyprland.conf
//
// Frosted look: real background blur is a compositor feature, not QML --
// Hyprland's decoration.blur is already enabled globally (hyprland.conf).
// For THIS layer-shell surface specifically to blur what's behind it, add
// `layerrule = blur, quickshell` to hyprland.conf (see design spec §12/§7,
// usr/share/doc/mios/concepts/mios-app-browser-portal-dashboard-design-2026-07-03.md).
// This file sets a translucent fill (Theme.withAlpha) so it still reads
// correctly even without that layer rule, per mios.toml [theme]'s standing
// "acrylic / 50% opacity / frameless" directive.

import QtQuick
import Quickshell
import Quickshell.Wayland

PanelWindow {
    id: rail
    anchors { top: true; left: true; bottom: true }
    width: 56
    color: "transparent"
    exclusiveZone: width

    property QtObject theme: Theme {}
    // Native Portal API client (usr/share/mios/quickshell/PortalData.qml) --
    // NOT logged in automatically (no credential is ever hardcoded here).
    // A future settings panel calling portalData.login(password) is what
    // turns this pill from a static placeholder into a live service count;
    // see the design spec's native-unification roadmap, phase 2b.
    property QtObject portalData: PortalData {}

    Rectangle {
        anchors.fill: parent
        color: theme.withAlpha(theme.bg, theme.panelOpacity)
        border.width: 1
        border.color: theme.subtle
        radius: theme.radius

        Column {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 12
            spacing: 14

            // Workspace indicator -- three pips, active one filled with accent.
            Row {
                spacing: 6
                anchors.horizontalCenter: parent.horizontalCenter
                Repeater {
                    model: 3
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: index === 0 ? theme.accent : theme.muted
                    }
                }
            }

            // Agent-status pill (mios-agent-pipe reachability -- idle/busy).
            Rectangle {
                width: 36; height: 20; radius: 10
                color: theme.withAlpha(theme.success, 0.25)
                border.width: 1; border.color: theme.success
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    anchors.centerIn: parent
                    // Live once portalData.login() has been called somewhere
                    // (e.g. a future settings panel); until then this is the
                    // same static placeholder it always was -- no fabricated
                    // data, no auto-login with an embedded password.
                    text: portalData.authed && portalData.stats.services
                          ? portalData.stats.services.filter(function (s) { return s.ok }).length + "/" + portalData.stats.services.length
                          : "AI"
                    color: theme.success
                    font.family: theme.fontFamily
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            // Cockpit quick-launch tile -- one click to the real admin console.
            Rectangle {
                width: 36; height: 36; radius: theme.radius / 2
                color: theme.withAlpha(theme.accent, 0.25)
                border.width: 1; border.color: theme.accent
                anchors.horizontalCenter: parent.horizontalCenter
                Text {
                    anchors.centerIn: parent
                    text: "" // nf-fa-dashboard glyph, Symbols Nerd Font Mono
                    color: theme.fg
                    font.family: "Symbols Nerd Font Mono"
                    font.pixelSize: 16
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Qt.openUrlExternally("http://localhost:9090")
                }
            }
        }

        Text {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: 12
            text: Qt.formatDateTime(new Date(), "hh:mm")
            color: theme.fg
            font.family: theme.fontFamily
            font.pixelSize: 12
        }
    }
}
