#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Processes boot arguments from kargs.d/*.toml files into a single string at /usr/lib/kernel/cmdline to prepare the Unified Kernel Image (UKI) during the build or deployment phase.
set -euo pipefail

# shellcheck source=/dev/null
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

if [[ ! -f "$GEN_SCRIPT" ]]; then
    mios_err "authoritative UKI cmdline generator not found at $GEN_SCRIPT"
    exit 1
fi

# Both paths run the same generator: miosd render-uki-cmdline execs
# tools/generate-uki-cmdline.py, which is where the kargs.d parse actually
# lives. The dispatch is about which side owns the invocation, not about two
# implementations -- so there is no output to diff, only a root to get right.
# miosd resolves the script against MIOS_ROOT, so pass it explicitly rather
# than relying on the caller's cwd.
if [[ -n "$_miosd" ]]; then
    mios_log "Render UKI cmdline via miosd"
    MIOS_ROOT="$ROOT" "$_miosd" render-uki-cmdline
else
    mios_log "Render UKI cmdline via authoritative generator"
    python3 "$GEN_SCRIPT"
fi

if [[ "${ROOT}/usr/lib/kernel/cmdline" != "${KERNEL_CMDLINE_DST}" ]]; then
    install -D -m 0644 "${ROOT}/usr/lib/kernel/cmdline" "${KERNEL_CMDLINE_DST}"
fi

CMDLINE=$(cat "${KERNEL_CMDLINE_DST}" | xargs)
if [ -z "$CMDLINE" ]; then
    mios_warn "/usr/lib/kernel/cmdline empty"
fi

mios_ok "Rendered UKI cmdline: $CMDLINE"
mios_ok "UKI cmdline rendered"
