// AI-hint: MiOS top status bar (Quickshell layer-shell surface, top-anchored).
// Colors/typography come from Theme.qml (SSOT-driven from mios.toml
// [colors]/[theme.font] via /etc/mios/theme/theme.json) instead of the
// previous hardcoded Catppuccin Mocha hex (#1e1e2e/#cdd6f4/#a6e3a1). Kept as
// a small, generic, reusable bar; the left-anchored vertical launcher rail
// (workspace pips, agent-status pill, Cockpit quick-tile, clock) lives in
// the sibling Sidebar.qml so the two surfaces don't collide under QML's
// implicit-directory-import name resolution (both this file and Sidebar.qml
// are loaded, unqualified, by Config.qml).
// AI-related: usr/share/mios/quickshell/Theme.qml, usr/share/mios/quickshell/Sidebar.qml,
// usr/share/mios/quickshell/Config.qml

import QtQuick
import Quickshell
import Quickshell.Wayland

PanelWindow {
    id: topBar
    anchors { top: true; left: true; right: true }
    height: 32
    color: "transparent"
    exclusiveZone: height

    property QtObject theme: Theme {}

    Rectangle {
        anchors.fill: parent
        color: theme.withAlpha(theme.bg, theme.panelOpacity)
        border.width: 1
        border.color: theme.subtle

        Row {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 16

            Text {
                text: "MiOS"
                color: theme.accent
                font.family: theme.fontFamily
                font.bold: true
                font.pixelSize: 14
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Agent: Idle"
                color: theme.success
                font.family: theme.fontFamily
                font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: Qt.formatDateTime(new Date(), "hh:mm:ss")
            color: theme.fg
            font.family: theme.fontFamily
            font.pixelSize: 13
        }
    }
}
