#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Processes boot arguments from kargs.d/*.toml files into a single string at /usr/lib/kernel/cmdline to prepare the Unified Kernel Image (UKI) during the build or deployment phase.
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Render kernel cmdline from bootc kargs.d/*.toml for the UKI"

source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

if ! rpm -q systemd-ukify >/dev/null 2>&1; then
    mios_log "Systemd-ukify not found; reinstalling via mios.toml [packages.uki]"
    install_packages_strict "uki"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GEN_SCRIPT="${ROOT}/tools/generate-uki-cmdline.py"
KERNEL_CMDLINE_DST="/usr/lib/kernel/cmdline"
install -d -m 0755 /usr/lib/kernel

if command -v miosd >/dev/null 2>&1; then
    miosd render-uki-cmdline
    if [[ "${ROOT}/usr/lib/kernel/cmdline" != "${KERNEL_CMDLINE_DST}" && -f "${ROOT}/usr/lib/kernel/cmdline" ]]; then
        install -D -m 0644 "${ROOT}/usr/lib/kernel/cmdline" "${KERNEL_CMDLINE_DST}"
    fi
    mios_ok "rendered UKI cmdline via miosd"
    exit 0
fi

if [[ ! -f "$GEN_SCRIPT" ]]; then
    mios_err "authoritative UKI cmdline generator not found at $GEN_SCRIPT"
    exit 1
fi

mios_log "Render UKI cmdline via authoritative generator"
python3 "$GEN_SCRIPT"

if [[ "${ROOT}/usr/lib/kernel/cmdline" != "${KERNEL_CMDLINE_DST}" ]]; then
    install -D -m 0644 "${ROOT}/usr/lib/kernel/cmdline" "${KERNEL_CMDLINE_DST}"
fi

CMDLINE=$(cat "${KERNEL_CMDLINE_DST}" | xargs)
if [ -z "$CMDLINE" ]; then
    mios_warn "/usr/lib/kernel/cmdline empty -- no kargs rendered; UKI uses defaults"
fi

mios_ok "rendered UKI cmdline: $CMDLINE"
mios_ok "UKI cmdline rendered"
