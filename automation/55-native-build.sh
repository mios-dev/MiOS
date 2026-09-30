#!/usr/bin/env bash
# AI-hint: Compiles native Rust workspace crates (tools/native and src/mios-rs) and installs binaries into /usr/libexec/mios during image bake.
# AI-related: tools/native/Cargo.toml, src/mios-rs/Cargo.toml, automation/85-bake-plan.sh, /usr/libexec/mios/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# The image bake copies tools/ but not src/mios-rs: its native artifacts were
# already compiled by the Containerfile's rust-builder stage. Installing Cargo
# must not trigger a partial second build from that incomplete source context.
if [[ ! -f "${ROOT_DIR}/src/mios-rs/Cargo.toml" ]]; then
    for bin in miosd mios-gate mios-probe mios-node mios-resolver mios-unit-gen mios-render-quadlets mios-bake-plan; do
        [[ -x "/usr/libexec/mios/${bin}" ]] || {
            echo "[55-native-build] FATAL: incomplete source context and missing prebuilt /usr/libexec/mios/${bin}" >&2
            exit 1
        }
    done
    echo "[55-native-build] Image bake uses the complete prebuilt native tool set."
    exit 0
fi

DEST_DIR="/usr/libexec/mios"
if [[ "${EUID}" -ne 0 && -n "${DEST_DIR}" ]]; then
    DEST_DIR="${ROOT_DIR}/usr/libexec/mios"
fi

mkdir -p "${DEST_DIR}"

if command -v cargo >/dev/null 2>&1; then
    # A caller's CARGO_TARGET_DIR must not cause installation to read stale
    # workspace artifacts. Build and install from an explicit common output.
    TARGET_DIR="${ROOT_DIR}/tools/native/target"
    for workspace in tools/native src/mios-rs; do
        echo "[55-native-build] Compiling ${workspace} workspace crates..."
        args=(--release --workspace --target-dir "$TARGET_DIR")
        [[ "$workspace" != tools/native ]] || args+=(--exclude mios-wallpaperd)
        (cd "${ROOT_DIR}/${workspace}" && cargo build "${args[@]}")
        # Cargo declares the executable surface. Do not glob sidecar .d files,
        # Windows .exe artifacts or every executable-marked NTFS checkout file.
        binaries="$(cd "${ROOT_DIR}/${workspace}" && cargo metadata --no-deps --format-version 1 \
            | python3 -c 'import json,sys; d=json.load(sys.stdin); members=set(d["workspace_members"]); print("\n".join(t["name"] for p in d["packages"] if p["id"] in members and p["name"] != "mios-wallpaperd" for t in p["targets"] if "bin" in t["kind"]))')"
        [[ -n "$binaries" ]] || { echo "[55-native-build] FATAL: ${workspace} declares no binaries" >&2; exit 1; }
        while IFS= read -r bin; do
            SRC_BIN="${TARGET_DIR}/release/${bin}"
            [[ -f "$SRC_BIN" && -x "$SRC_BIN" ]] || { echo "[55-native-build] FATAL: build did not produce ${SRC_BIN}" >&2; exit 1; }
            magic="$(od -An -tx1 -N4 "$SRC_BIN" | tr -d ' \n')"
            [[ "$magic" == 7f454c46 ]] || { echo "[55-native-build] FATAL: ${SRC_BIN} is not a Linux ELF executable" >&2; exit 1; }
            echo "[55-native-build] Installing ${bin} to ${DEST_DIR}..."
            cp "${SRC_BIN}" "${DEST_DIR}/${bin}"
            chmod +x "${DEST_DIR}/${bin}"
            if [[ "${EUID}" -eq 0 && -d /usr/bin ]]; then
                ln -sf "${DEST_DIR}/${bin}" "/usr/bin/${bin}"
            fi
        done <<< "$binaries"
    done
else
    echo "[55-native-build] FATAL: selected self-build dependency closure did not provide Cargo." >&2
    exit 1
fi
