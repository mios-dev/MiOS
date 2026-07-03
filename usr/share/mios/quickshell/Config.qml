import QtQuick
import Quickshell

ShellRoot {
    // Quickshell uses PanelWindow for layer-shell anchoring (zwlr_layer_shell_v1)
    PanelWindow {
        id: statusBar
        anchors.top: true
        anchors.left: true
        anchors.right: true
        height: 36
        color: "#1e1e2e"

        Row {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 15

            // Left Side: Workspaces Indicator
            Text {
                text: "Workspace: 1 | 2 | 3"
                color: "#cdd6f4"
                font.pixelSize: 14
                verticalAlignment: Text.AlignVCenter
            }

            // Spacing
            Item {
                width: 10
                height: 1
            }

            // Active Task
            Text {
                text: "Agent: Idle"
                color: "#a6e3a1"
                font.pixelSize: 14
                verticalAlignment: Text.AlignVCenter
            }
        }

        // Right Side Clock
        Text {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: Qt.formatDateTime(new Date(), "hh:mm:ss")
            color: "#cdd6f4"
            font.pixelSize: 14
        }
    }
}
