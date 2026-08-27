#!/usr/bin/env bash
# AI-hint: Compiles native Rust workspace crates (tools/native and src/mios-rs) and installs binaries into /usr/libexec/mios during image bake.
# AI-related: tools/native/Cargo.toml, src/mios-rs/Cargo.toml, automation/85-bake-plan.sh, /usr/libexec/mios/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEST_DIR="/usr/libexec/mios"
if [[ "${EUID}" -ne 0 && -n "${DEST_DIR}" ]]; then
    DEST_DIR="${ROOT_DIR}/usr/libexec/mios"
fi

mkdir -p "${DEST_DIR}"

if command -v cargo >/dev/null 2>&1; then
    echo "[55-native-build] Compiling tools/native workspace crates..."
    (cd "${ROOT_DIR}/tools/native" && cargo build --release)

    if [[ -d "${ROOT_DIR}/src/mios-rs" ]]; then
        echo "[55-native-build] Compiling src/mios-rs workspace crates (mios-node, miosd, mios-build, mios-config)..."
        (cd "${ROOT_DIR}/src/mios-rs" && cargo build --release)
    fi

    for bin in mios-resolver mios-drift-runner mios-ssot-lint mios-version-check mios-node miosd; do
        SRC_BIN=""
        if [[ -f "${ROOT_DIR}/tools/native/target/release/${bin}" ]]; then
            SRC_BIN="${ROOT_DIR}/tools/native/target/release/${bin}"
        elif [[ -f "${ROOT_DIR}/src/mios-rs/target/release/${bin}" ]]; then
            SRC_BIN="${ROOT_DIR}/src/mios-rs/target/release/${bin}"
        fi

        if [[ -n "${SRC_BIN}" ]]; then
            echo "[55-native-build] Installing ${bin} to ${DEST_DIR}..."
            cp "${SRC_BIN}" "${DEST_DIR}/${bin}"
            chmod +x "${DEST_DIR}/${bin}"
            if [[ "${EUID}" -eq 0 && -d /usr/bin ]]; then
                ln -sf "${DEST_DIR}/${bin}" "/usr/bin/${bin}"
            fi
        fi
    done
else
    echo "[55-native-build] WARNING: cargo toolchain not available; skipping native build."
fi
