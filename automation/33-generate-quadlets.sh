#!/usr/bin/env bash
# AI-hint: bash MIOS_APPLY_CLASS=universal Automatically generates Quadlet configuration files (.pod, .container, .network) from the mios.toml SSOT at im...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_33_generate_quadlets_sh.md
set -euo pipefail
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

if command -v miosd >/dev/null 2>&1; then
    MIOS_ROOT="$ROOT" MIOS_TOML="$TOML_FILE" MIOS_POD_OUT="$OUT_DIR" miosd generate-quadlets
    mios_ok "Quadlets generated into ${OUT_DIR} via miosd"
    exit 0
fi

MIOS_ROOT="$ROOT" MIOS_TOML="$TOML_FILE" MIOS_POD_OUT="$OUT_DIR" python3 "$GEN_SCRIPT"

mios_ok "Quadlets generated into ${OUT_DIR}"
