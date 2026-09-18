#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Automatically generates Quadlet configuration files (.pod, .container, .network) from the mios.toml SSOT at im...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail
# shellcheck source=/dev/null
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

GEN_SCRIPT="${ROOT}/tools/generate-pod-quadlets.py"
TOML_FILE="${ROOT}/usr/share/mios/mios.toml"
OUT_DIR="${ROOT}/usr/share/containers/systemd"

mios_log "Generating Quadlets from ${TOML_FILE} to ${OUT_DIR}"

if [[ ! -f "$GEN_SCRIPT" ]]; then
    mios_err "generate-pod-quadlets.py not found at $GEN_SCRIPT"
    exit 1
fi

TARGET_DIR="/usr/share/containers/systemd"
if [[ -w "$TARGET_DIR" ]]; then
    OUT_DIR="$TARGET_DIR"
fi

# Absolute path, never `command -v`: miosd installs to /usr/libexec/mios, which
# nothing puts on PATH at bake time, so the lookup this replaced could never
# succeed and the branch below it was dead on every build (T-1018).
_miosd=""
for _c in "${MIOS_MIOSD_BIN:-}" \
          /usr/libexec/mios/miosd \
          "${ROOT}/src/mios-rs/target/release/miosd" \
          "${ROOT}/src/mios-rs/target/debug/miosd"; do
    if [[ -n "$_c" && -x "$_c" ]]; then _miosd="$_c"; break; fi
done

# Both legs run the same generator -- miosd generate-quadlets execs
# tools/generate-pod-quadlets.py -- so this dispatch decides who invokes it,
# not which implementation renders. The environment is identical on both sides
# for that reason.
if [[ -n "$_miosd" ]]; then
    MIOS_ROOT="$ROOT" MIOS_TOML="$TOML_FILE" MIOS_POD_OUT="$OUT_DIR" "$_miosd" generate-quadlets
    mios_ok "Quadlets generated into ${OUT_DIR} via miosd"
else
    MIOS_ROOT="$ROOT" MIOS_TOML="$TOML_FILE" MIOS_POD_OUT="$OUT_DIR" python3 "$GEN_SCRIPT"
    mios_ok "Quadlets generated into ${OUT_DIR}"
fi
