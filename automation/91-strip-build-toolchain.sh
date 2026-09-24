#!/bin/bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Removes build-toolchain packages (gcc, g++, cmake, etc.) from the final image via dnf to minimize attack surface, ensuring no compilers remain in the PATH after the build phase.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"

mios_log "Resolving and combing all build-time package groups"

# Dynamically discover all *-build package groups from mios.toml alongside build-toolchain
TOML_FILE="$(_resolve_mios_toml 2>/dev/null || true)"
DYNAMIC_BUILD_GROUPS=()
if [[ -n "$TOML_FILE" && -f "$TOML_FILE" ]]; then
    while IFS= read -r grp; do
        [[ -n "$grp" ]] && DYNAMIC_BUILD_GROUPS+=("$grp")
    done < <(grep -E '^\[packages\..*-build\]' "$TOML_FILE" | sed -E 's/^\[packages\.([^]]+)\]/\1/')
fi

declare -A SEEN_GROUPS
BUILD_GROUPS=()
for grp in "build-toolchain" "quickshell-build" "looking-glass-build" "k3s-selinux-build" "cockpit-plugins-build" "${DYNAMIC_BUILD_GROUPS[@]}"; do
    if [[ -z "${SEEN_GROUPS[$grp]:-}" ]]; then
        SEEN_GROUPS["$grp"]=1
        BUILD_GROUPS+=("$grp")
    fi
done

for grp in "${BUILD_GROUPS[@]}"; do
    pkgs="$(get_packages "$grp" || true)"
    if [[ -n "${pkgs// /}" ]]; then
        mios_log "Combing build group '${grp}': ${pkgs}"
        $DNF_BIN "${DNF_SETOPT[@]}" remove -y --noautoremove $pkgs 2>&1 \
            | grep -E '^\s*(Removing|Error|Warning|Nothing)' || true
    fi
done

# Purge standalone bake-only tools
if [[ -f /usr/local/bin/syft ]]; then
    mios_log "Removing standalone build-time tool /usr/local/bin/syft"
    rm -f /usr/local/bin/syft
fi

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
