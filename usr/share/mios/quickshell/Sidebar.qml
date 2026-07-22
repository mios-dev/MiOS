// AI-hint: MiOS left-anchored vertical launcher rail (Quickshell layer-shell
// surface). Interactive workspace pips, animated agent-status pill, Cockpit
// quick-tile with hover glow, and MiOS branding footer.
// Colors/typography come from Theme.qml (SSOT, mios.toml [colors]).
// AI-related: usr/share/mios/quickshell/Theme.qml, usr/share/mios/quickshell/Config.qml,
// usr/share/mios/hyprland/hyprland.conf

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
    property QtObject portalData: PortalData {}
    property int activeWorkspace: 1

    // Live minute clock for footer
    Timer {
        interval: 30000; repeat: true; running: true; triggeredOnStart: true
        onTriggered: clockFooter.text = Qt.formatDateTime(new Date(), "hh:mm")
    }

    Rectangle {
        anchors.fill: parent
        color: theme.withAlpha(theme.bg, theme.panelOpacity)
        border.width: 0

        // Right edge accent stripe
        Rectangle {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            width: 1
            gradient: Gradient {
                GradientStop { position: 0.0;  color: "transparent" }
                GradientStop { position: 0.3;  color: theme.withAlpha(theme.accent, 0.6) }
                GradientStop { position: 0.7;  color: theme.withAlpha(theme.cursor, 0.6) }
                GradientStop { position: 1.0;  color: "transparent" }
            }
        }

        Column {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 12
            spacing: 10

            // ── MiOS Shield Logo ─────────────────────────────────────────
            Text {
                text: "⬡"
                color: theme.accent
                font.pixelSize: 22
                font.bold: true
                anchors.horizontalCenter: parent.horizontalCenter
                // Subtle entrance animation on load
                opacity: 0
                Component.onCompleted: fadeIn.start()
                NumberAnimation on opacity { id: fadeIn; to: 1.0; duration: 800; easing.type: Easing.OutCubic }
            }

            // Thin divider
            Rectangle {
                width: 28; height: 1
                color: theme.withAlpha(theme.subtle, 0.35)
                anchors.horizontalCenter: parent.horizontalCenter
            }

            // ── Workspace Pips (5 workspaces, interactive) ────────────────
            Column {
                spacing: 6
                anchors.horizontalCenter: parent.horizontalCenter

                Repeater {
                    model: 5
                    delegate: Rectangle {
                        property bool isActive: (index + 1) === rail.activeWorkspace
                        property bool isHovered: false
                        width: isActive ? 32 : 8
                        height: 8
                        radius: 4
                        color: isActive ? theme.accent : (isHovered ? theme.withAlpha(theme.accent, 0.5) : theme.withAlpha(theme.muted, 0.5))
                        anchors.horizontalCenter: parent.horizontalCenter

                        // Smooth width transition for active pip expansion
                        Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                        Behavior on color { ColorAnimation { duration: 150 } }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onEntered: parent.isHovered = true
                            onExited:  parent.isHovered = false
                            onClicked: rail.activeWorkspace = index + 1
                        }
                    }
                }
            }

            // ── Agent Status Pill ─────────────────────────────────────────
            Rectangle {
                width: 36; height: 22; radius: 11
                color: theme.withAlpha(theme.success, 0.18)
                border.width: 1; border.color: theme.withAlpha(theme.success, 0.7)
                anchors.horizontalCenter: parent.horizontalCenter

                // Glow pulse
                SequentialAnimation on border.color {
                    loops: Animation.Infinite
                    ColorAnimation { to: theme.withAlpha(theme.success, 1.0); duration: 1200; easing.type: Easing.InOutSine }
                    ColorAnimation { to: theme.withAlpha(theme.success, 0.4); duration: 1200; easing.type: Easing.InOutSine }
                }

                Text {
                    anchors.centerIn: parent
                    text: portalData.authed && portalData.stats.services
                          ? portalData.stats.services.filter(function(s) { return s.ok }).length + "/" + portalData.stats.services.length
                          : "AI"
                    color: theme.success
                    font.family: theme.fontFamily
                    font.pixelSize: 10
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Qt.openUrlExternally("http://localhost:8080")
                }
            }

            // ── Cockpit Quick-Tile ────────────────────────────────────────
            Rectangle {
                id: cockpitTile
                width: 36; height: 36; radius: theme.radius / 2
                color: theme.withAlpha(theme.accent, 0.18)
                border.width: 1; border.color: theme.withAlpha(theme.accent, 0.5)
                anchors.horizontalCenter: parent.horizontalCenter

                property bool hovered: false

                // Glow on hover
                Behavior on color { ColorAnimation { duration: 150 } }
                Behavior on border.color { ColorAnimation { duration: 150 } }

                Text {
                    anchors.centerIn: parent
                    text: ""   // nf-fa-dashboard (Symbols Nerd Font Mono)
                    color: cockpitTile.hovered ? theme.accent : theme.withAlpha(theme.fg, 0.7)
                    font.family: "Symbols Nerd Font Mono"
                    font.pixelSize: 16
                    Behavior on color { ColorAnimation { duration: 150 } }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: {
                        cockpitTile.hovered = true
                        cockpitTile.color = theme.withAlpha(theme.accent, 0.35)
                        cockpitTile.border.color = theme.accent
                    }
                    onExited: {
                        cockpitTile.hovered = false
                        cockpitTile.color = theme.withAlpha(theme.accent, 0.18)
                        cockpitTile.border.color = theme.withAlpha(theme.accent, 0.5)
                    }
                    onClicked: Qt.openUrlExternally("http://localhost:9090")
                }
            }

            // ── Terminal Quick-Tile ───────────────────────────────────────
            Rectangle {
                id: termTile
                width: 36; height: 36; radius: theme.radius / 2
                color: theme.withAlpha(theme.success, 0.12)
                border.width: 1; border.color: theme.withAlpha(theme.success, 0.4)
                anchors.horizontalCenter: parent.horizontalCenter

                Behavior on color { ColorAnimation { duration: 150 } }

                Text {
                    anchors.centerIn: parent
                    text: ""   // nf-fa-terminal (Symbols Nerd Font Mono)
                    color: theme.withAlpha(theme.success, 0.8)
                    font.family: "Symbols Nerd Font Mono"
                    font.pixelSize: 16
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onEntered: {
                        termTile.color = theme.withAlpha(theme.success, 0.28)
                        termTile.border.color = theme.success
                    }
                    onExited: {
                        termTile.color = theme.withAlpha(theme.success, 0.12)
                        termTile.border.color = theme.withAlpha(theme.success, 0.4)
                    }
                    onClicked: Qt.openUrlExternally("http://localhost:8080/terminal")
                }
            }
        }

        // ── Footer: clock ─────────────────────────────────────────────────
        Text {
            id: clockFooter
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: 12
            text: "00:00"
            color: theme.withAlpha(theme.fg, 0.5)
            font.family: theme.fontFamily
            font.pixelSize: 11
        }
    }
}
