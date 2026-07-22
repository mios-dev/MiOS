// AI-hint: MiOS desktop notification toast surface (Quickshell layer-shell,
// top-right anchored, above other layers). GnomeOS/KDE-style: slides in from
// right, auto-dismisses after 5s, supports info/success/warning/error kinds.
// Colors from Theme.qml (SSOT, mios.toml [colors]).
// AI-related: usr/share/mios/quickshell/Theme.qml, usr/share/mios/quickshell/Config.qml,
// usr/share/mios/quickshell/NotifModel.qml

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland

PanelWindow {
    id: notifSurface
    anchors { top: true; right: true }
    width: 320
    height: toastCol.implicitHeight + 24
    color: "transparent"
    // Don't take exclusive zone -- float above content
    exclusiveZone: 0

    property QtObject theme: Theme {}

    // Map kind to accent color
    function kindColor(kind) {
        if (kind === "success") return theme.success
        if (kind === "warning") return theme.warning
        if (kind === "error")   return theme.error
        return theme.accent  // info default
    }
    function kindIcon(kind) {
        if (kind === "success") return "✔"
        if (kind === "warning") return "⚠"
        if (kind === "error")   return "✖"
        return "ℹ"
    }

    Column {
        id: toastCol
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 44   // below top bar (height 36 + gap 8)
        anchors.rightMargin: 10
        spacing: 6
        width: 310

        Repeater {
            model: ListModel { id: notifListModel }

            delegate: Rectangle {
                id: toastRect
                width: 310
                height: toastContent.implicitHeight + 20
                radius: theme.radius
                color: theme.withAlpha(theme.bg, 0.92)
                border.width: 1
                border.color: notifSurface.kindColor(model.kind)
                clip: true

                // Slide-in from right
                x: 320
                Component.onCompleted: slideIn.start()
                NumberAnimation on x {
                    id: slideIn; to: 0; duration: 280; easing.type: Easing.OutCubic
                }

                // Auto-dismiss after 5s
                Timer {
                    interval: 5000; running: true; repeat: false
                    onTriggered: {
                        slideOut.start()
                    }
                }
                NumberAnimation on x {
                    id: slideOut; to: 330; duration: 220; easing.type: Easing.InCubic
                    onStopped: notifListModel.remove(index)
                }

                // Left kind stripe
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 4
                    radius: 2
                    color: notifSurface.kindColor(model.kind)
                }

                ColumnLayout {
                    id: toastContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 12
                    anchors.leftMargin: 16
                    spacing: 4

                    RowLayout {
                        spacing: 6
                        Text {
                            text: notifSurface.kindIcon(model.kind)
                            color: notifSurface.kindColor(model.kind)
                            font.pixelSize: 13
                            font.bold: true
                        }
                        Text {
                            text: model.title
                            color: theme.fg
                            font.family: theme.fontFamily
                            font.pixelSize: 12
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        // Dismiss button
                        Text {
                            text: "✕"
                            color: theme.withAlpha(theme.muted, 0.7)
                            font.pixelSize: 11
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    slideOut.start()
                                }
                            }
                        }
                    }

                    Text {
                        text: model.body
                        color: theme.withAlpha(theme.fg, 0.75)
                        font.family: theme.fontFamily
                        font.pixelSize: 11
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        visible: model.body !== ""
                    }
                }
            }
        }
    }

    // Public API: call notifSurface.notify("Title", "Body", "success")
    function notify(title, body, kind) {
        notifListModel.append({ title: title, body: body || "", kind: kind || "info" })
    }
}
