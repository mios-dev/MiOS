#!/bin/bash
# AI-hint: Installs Qt6 build-time tools, clones the quickshell repository, compiles it, and deploys the default declarative QML panels in /usr/share/mios/quickshell/.
# AI-related: /usr/bin/quickshell, /usr/share/mios/quickshell/Config.qml
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

echo "[55-bake-quickshell] Installing Qt6 build dependencies..."
install_packages_strict "quickshell-build"

echo "[55-bake-quickshell] Compiling quickshell from upstream..."
BUILD_DIR="/tmp/quickshell-build"
rm -rf "$BUILD_DIR"
git clone --recursive "${MIOS_URL_QUICKSHELL:-https://github.com/quickshell-mirror/quickshell.git}" "$BUILD_DIR"

cd "$BUILD_DIR"
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
make install

echo "[55-bake-quickshell] Writing default quickshell panels..."
mkdir -p /usr/share/mios/quickshell
cat << 'EOF' > /usr/share/mios/quickshell/Config.qml
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
EOF
chmod 0644 /usr/share/mios/quickshell/Config.qml
echo "[55-bake-quickshell] Quickshell successfully compiled and deployed."
