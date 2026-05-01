#!/usr/bin/env bash
# MiOS load-user-env — reads XDG TOML configs and exports MIOS_* variables
# Usage: source ./tools/load-user-env.sh
# Note: must be sourced (not executed) to affect the calling shell.

MIOS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mios"

_mios_toml_get() {
    local file="$1" key="$2"
    grep -E "^${key}\s*=" "$file" 2>/dev/null | head -1 | sed 's/.*=\s*"\?\([^"]*\)"\?.*/\1/' | tr -d '"'
}

if [[ -f "${MIOS_CONFIG_DIR}/env.toml" ]]; then
    f="${MIOS_CONFIG_DIR}/env.toml"
    for key in MIOS_USER MIOS_HOSTNAME MIOS_FLATPAKS MIOS_BASE_IMAGE MIOS_LOCAL_TAG MIOS_BIB_IMAGE MIOS_IMAGE_NAME; do
        val="$(_mios_toml_get "$f" "$key")"
        [[ -n "$val" ]] && export "$key=$val"
    done
fi

if [[ -f "${MIOS_CONFIG_DIR}/images.toml" ]]; then
    f="${MIOS_CONFIG_DIR}/images.toml"
    for key in MIOS_BASE_IMAGE MIOS_BIB_IMAGE MIOS_IMAGE_NAME; do
        val="$(_mios_toml_get "$f" "$key")"
        [[ -n "$val" ]] && export "$key=$val"
    done
fi
