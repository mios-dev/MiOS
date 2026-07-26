#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Processes boot arguments from kargs.d/*.toml files into a single string at /usr/lib/kernel/cmdline to prepare the Unified Kernel Image (UKI) during the build or deployment phase.
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "render kernel cmdline from bootc kargs.d/*.toml for the UKI"

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

# [packages.boot] already pulls systemd-ukify; reinstall via the SSOT
# [packages.uki] section as a safety net in case --skip-unavailable dropped
# it on a constrained mirror.
if ! rpm -q systemd-ukify >/dev/null 2>&1; then
    mios_log "systemd-ukify not found; reinstalling via mios.toml [packages.uki]"
    install_packages_strict "uki"
fi

# SINGLE SOURCE OF TRUTH: tools/generate-uki-cmdline.py (AGY-163) is the ONE
# authoritative flattener of usr/lib/bootc/kargs.d/*.toml -> usr/lib/kernel/cmdline.
# The post-build drift-gate (38-drift-checks check 93) validates the tree against
# `generate-uki-cmdline.py --check` (ROOT=/tmp/build), so the build MUST render via
# the SAME generator here -- a divergent `bootc container render-kargs` or a
# hand-rolled TOML flatten would order/dedup/space the kargs differently and fail
# the gate. cmdline must be correct BEFORE the UKI is built, so render it here.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GEN_SCRIPT="${ROOT}/tools/generate-uki-cmdline.py"
KERNEL_CMDLINE_DST="/usr/lib/kernel/cmdline"
install -d -m 0755 /usr/lib/kernel

if [[ ! -f "$GEN_SCRIPT" ]]; then
    mios_err "authoritative UKI cmdline generator not found at $GEN_SCRIPT"
    exit 1
fi

# generate-uki-cmdline.py resolves its output relative to its own location, i.e.
# ${ROOT}/usr/lib/kernel/cmdline -- exactly where the drift-gate --check looks.
mios_log "render UKI cmdline via authoritative generator (${GEN_SCRIPT})"
python3 "$GEN_SCRIPT"

# Install the generated SSOT to the live image path the UKI (`ukify build`)
# consumes. Skip the copy when ROOT already IS the live root (source==dest).
if [[ "${ROOT}/usr/lib/kernel/cmdline" != "${KERNEL_CMDLINE_DST}" ]]; then
    install -D -m 0644 "${ROOT}/usr/lib/kernel/cmdline" "${KERNEL_CMDLINE_DST}"
fi

CMDLINE=$(cat "${KERNEL_CMDLINE_DST}" | xargs)
if [ -z "$CMDLINE" ]; then
    mios_warn "/usr/lib/kernel/cmdline empty -- no kargs rendered; UKI uses defaults"
fi

mios_ok "rendered UKI cmdline: $CMDLINE"
# The actual UKI generation (`ukify build`) occurs in the final CI/CD pipeline
mios_ok "UKI cmdline rendered"
