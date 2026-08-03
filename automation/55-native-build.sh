#!/usr/bin/env bash
# AI-hint: Compiles native Rust workspace crates and installs binaries into /usr/libexec/mios during image bake.
# AI-related: tools/native/Cargo.toml, automation/85-bake-plan.sh, /usr/libexec/mios/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEST_DIR="/usr/libexec/mios"
if [[ "${EUID}" -ne 0 && -n "${DEST_DIR}" ]]; then
    DEST_DIR="${ROOT_DIR}/usr/libexec/mios"
fi

mkdir -p "${DEST_DIR}"

if command -v cargo >/dev/null 2>&1; then
    echo "[58-native-build] Compiling native workspace crates..."
    (cd "${ROOT_DIR}/tools/native" && cargo build --release)
    
    for bin in mios-resolver mios-drift-runner mios-ssot-lint mios-version-check; do
        if [[ -f "${ROOT_DIR}/tools/native/target/release/${bin}" ]]; then
            echo "[58-native-build] Installing ${bin} to ${DEST_DIR}..."
            cp "${ROOT_DIR}/tools/native/target/release/${bin}" "${DEST_DIR}/${bin}"
            chmod +x "${DEST_DIR}/${bin}"
        fi
    done
else
    echo "[58-native-build] WARNING: cargo toolchain not available; skipping native build."
fi
