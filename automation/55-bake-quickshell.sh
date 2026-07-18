#!/bin/bash
# AI-hint: Installs Qt6 build-time tools, clones the quickshell repository, compiles it, and deploys the default declarative QML panels in /usr/share/mios/quickshell/.
# AI-related: /usr/bin/quickshell, /usr/share/mios/quickshell/Config.qml
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

echo "[55-bake-quickshell] Installing Qt6 build dependencies..."
install_packages_strict "quickshell-build"

echo "[55-bake-quickshell] Compiling quickshell from upstream..."
source "${SCRIPT_DIR}/lib/common.sh" 2>/dev/null || true

PIN_REF="${MIOS_BUILD_BAKE_REFS_QUICKSHELL:-v0.3.0}"
log "[55-bake-quickshell] quickshell pin ref: ${PIN_REF}"

BUILD_DIR="/tmp/quickshell-build"
QUICKSHELL_OK=""

for attempt in 1 2 3; do
    log "[55-bake-quickshell] Compilation attempt $attempt/3..."
    rm -rf "$BUILD_DIR"
    
    if ! git clone "${MIOS_URL_QUICKSHELL:-https://github.com/quickshell-mirror/quickshell.git}" "$BUILD_DIR"; then
        warn "[55-bake-quickshell] git clone failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    cd "$BUILD_DIR"
    if ! git checkout "$PIN_REF"; then
        warn "[55-bake-quickshell] git checkout to $PIN_REF failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    if ! git submodule update --init --recursive; then
        warn "[55-bake-quickshell] git submodule update failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    mkdir -p build && cd build
    if cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release .. && \
       make -j$(nproc) && \
       make install; then
        if [[ -x /usr/bin/quickshell ]]; then
            QUICKSHELL_OK=1
            break
        fi
    fi
    
    warn "[55-bake-quickshell] build failed on attempt $attempt"
    sleep $((attempt * 8))
done

if [[ -z "$QUICKSHELL_OK" ]]; then
    warn "[55-bake-quickshell] quickshell build failed after 3 attempts."
    exit 1
fi

record_version quickshell "$PIN_REF" "https://github.com/quickshell-mirror/quickshell/tree/${PIN_REF}"

echo "[55-bake-quickshell] Writing default panel /usr/share/mios/quickshell/Config.qml..."
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
echo "[55-bake-quickshell] Installed /usr/bin/quickshell and wrote /usr/share/mios/quickshell/Config.qml."
