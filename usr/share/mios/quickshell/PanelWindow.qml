// AI-hint: MiOS top status bar (Quickshell layer-shell surface, top-anchored).
// Glassmorphic frosted bar with MiOS shield wordmark, live agent-status pill,
// and animated clock. Colors/typography come from Theme.qml
// (SSOT-driven from mios.toml [colors]/[theme.font] via /etc/mios/theme/theme.json).
// AI-related: usr/share/mios/quickshell/Theme.qml, usr/share/mios/quickshell/Sidebar.qml,
// usr/share/mios/quickshell/Config.qml

import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Wayland

PanelWindow {
    id: topBar
    anchors { top: true; left: true; right: true }
    height: 36
    color: "transparent"
    exclusiveZone: height

    property QtObject theme: Theme {}

    // Live 1-second clock ticker
    Timer {
        id: clockTick
        interval: 1000
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: timeLabel.text = Qt.formatDateTime(new Date(), "hh:mm:ss")
    }

    Rectangle {
        anchors.fill: parent
        // Glassmorphic: semi-transparent dark bg + compositor blur (layerrule = blur, quickshell)
        color: theme.withAlpha(theme.bg, theme.panelOpacity)
        border.width: 0

        // Bottom accent line -- the MiOS orange "brand stripe"
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0;  color: "transparent" }
                GradientStop { position: 0.15; color: theme.accent }
                GradientStop { position: 0.85; color: theme.cursor }
                GradientStop { position: 1.0;  color: "transparent" }
            }
        }

        // ── Left cluster: shield + wordmark ─────────────────────────────────
        Row {
            id: leftCluster
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            // MiOS hexagonal shield glyph (Nerd Font  or unicode ⬡)
            Text {
                text: "⬡"
                color: theme.accent
                font.pixelSize: 18
                font.bold: true
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "MiOS"
                color: theme.fg
                font.family: theme.fontFamily
                font.bold: true
                font.pixelSize: 14
                anchors.verticalCenter: parent.verticalCenter
            }

            // Thin separator
            Rectangle {
                width: 1; height: 16
                color: theme.subtle
                opacity: 0.4
                anchors.verticalCenter: parent.verticalCenter
            }

            // Agent status pill
            Rectangle {
                width: agentText.implicitWidth + 16
                height: 20
                radius: 10
                color: theme.withAlpha(theme.success, 0.18)
                border.width: 1
                border.color: theme.withAlpha(theme.success, 0.7)
                anchors.verticalCenter: parent.verticalCenter

                Row {
                    anchors.centerIn: parent
                    spacing: 4

                    // Pulsing dot
                    Rectangle {
                        width: 6; height: 6; radius: 3
                        color: theme.success
                        anchors.verticalCenter: parent.verticalCenter
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.3; duration: 900; easing.type: Easing.InOutSine }
                            NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
                        }
                    }

                    Text {
                        id: agentText
                        text: "AI · Idle"
                        color: theme.success
                        font.family: theme.fontFamily
                        font.pixelSize: 11
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }

        // ── Right cluster: clock ─────────────────────────────────────────────
        Row {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Text {
                id: timeLabel
                text: "00:00:00"
                color: theme.fg
                font.family: theme.fontFamily
                font.pixelSize: 13
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
