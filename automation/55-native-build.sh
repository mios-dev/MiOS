#!/usr/bin/env bash
# AI-hint: Bootstrap the Rust management binary; the SSOT native compile/install engine is miosd native-build.
# AI-related: src/mios-rs/mios-build/src/native_build.rs, usr/share/mios/mios.toml
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -f "$ROOT_DIR/src/mios-rs/Cargo.toml" ]]; then
    exec /usr/libexec/mios/miosd native-runtime-check --root "$ROOT_DIR" \
        --bin-dir "${MIOS_NATIVE_DEST_DIR:-/usr/libexec/mios}"
fi
if [[ -n "${MIOS_NATIVE_DEST_DIR:-}" ]]; then
    echo '[55-native-build] Use MIOS_NATIVE_INSTALL_ROOT for an SSOT FHS installation root.' >&2
    exit 1
fi
target_dir="${CARGO_TARGET_DIR:-$ROOT_DIR/tools/native/target}"
mkdir -p "$target_dir"
target_dir="$(cd "$target_dir" && pwd)"
host="$(rustc -vV | sed -n 's/^host: //p')"
[[ -n "$host" ]] || { echo '[55-native-build] Rust host target unavailable' >&2; exit 1; }
# This temporary compiler-host management binary is not a shipped artifact.
# The native engine builds, lints and verifies every shipped static binary.
(cd "$ROOT_DIR/src/mios-rs" && RUSTFLAGS='' CARGO_ENCODED_RUSTFLAGS='' \
    cargo build --release --locked -p miosd --target "$host" --target-dir "$target_dir")
# Fedora's rustup RPM installs rustup-init, not the rustup proxy. Keep the
# bootstrap compiler on its existing PATH; initialize proxies only after it
# has produced the management binary. That binary selects the SSOT channel.
if ! command -v rustup >/dev/null 2>&1; then
    command -v rustup-init >/dev/null 2>&1 || { echo '[55-native-build] Install the SSOT rustup package (rustup-init is missing).' >&2; exit 1; }
    rustup-init -y --no-modify-path --profile minimal --default-toolchain none
    export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$PATH"
    command -v rustup >/dev/null 2>&1 || { echo '[55-native-build] Rustup initialization did not provide its proxy.' >&2; exit 1; }
fi
prefix="${MIOS_NATIVE_INSTALL_ROOT:-}"
[[ -n "$prefix" ]] || { if [[ "$EUID" -eq 0 ]]; then prefix=/; else prefix="$ROOT_DIR"; fi; }
exec "$target_dir/$host/release/miosd" native-build --root "$ROOT_DIR" \
    --target-dir "$target_dir" --install-root "$prefix"
