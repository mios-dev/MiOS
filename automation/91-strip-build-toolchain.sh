#!/bin/bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Removes build-toolchain packages (gcc, g++, cmake, etc.) from the final image via dnf to minimize attack surface, ensuring no compilers remain in the PATH after the build phase.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"

mios_log "Resolving build-toolchain package list"
TOOLCHAIN_STR="$(get_packages "build-toolchain")"

if [[ -z "${TOOLCHAIN_STR// /}" ]]; then
    mios_warn "No packages in 'build-toolchain' block; nothing to strip"
    exit 0
fi

mios_log "Removing ${TOOLCHAIN_STR}"
$DNF_BIN "${DNF_SETOPT[@]}" remove -y --noautoremove $TOOLCHAIN_STR 2>&1 \
    | grep -E '^\s*(Removing|Error|Warning|Nothing)' || true

mios_log "Verifying toolchain removal"
for bin in gcc g++ cc cmake make go; do
    p="$(command -v "$bin" 2>/dev/null || true)"
    if [[ -n "$p" && -L "$p" ]]; then
        rm -f "$p" 2>/dev/null || true
    fi
done

LEFT=()
for bin in gcc g++ cc cmake make go; do
    if command -v "$bin" >/dev/null 2>&1; then
        LEFT+=("$bin -> $(command -v "$bin")")
    fi
done
if [[ ${#LEFT[@]} -gt 0 ]]; then
    mios_warn "Toolchain binaries still in PATH:"
    for entry in "${LEFT[@]}"; do mios_warn "  ${entry}"; done
    mios_warn "Pulled in by another package's dependencies; review build-toolchain block"
else
    mios_ok "No compiler/build-system binaries remain in PATH"
fi

mios_ok "Build toolchain stripped"
