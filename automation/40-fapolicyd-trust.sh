#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures fapolicyd to use file-based trust (fs-verity) to enable secure, immutable application whitelisting on ComposeFS systems without boot delays.
# AI-related: fapolicyd.service
set -euo pipefail

# shellcheck source=/dev/null
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Set fapolicyd trust = file,rpmdb in /usr/lib and /etc fapolicyd.conf"

source "$(dirname "$0")/lib/common.sh"

# Absolute path, never `command -v`: miosd installs to /usr/libexec/mios, which
# nothing puts on PATH at bake time, so the lookup this replaced could never
# succeed and the branch below it was dead on every build (T-1018).
_miosd=""
_here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for _c in "${MIOS_MIOSD_BIN:-}" \
          /usr/libexec/mios/miosd \
          "${_here}/src/mios-rs/target/release/miosd" \
          "${_here}/src/mios-rs/target/debug/miosd"; do
    if [[ -n "$_c" && -x "$_c" ]]; then _miosd="$_c"; break; fi
done

# `miosd harden` is one function serving BOTH this stage and 51: it rewrites
# trust= (this stage's job) and enables usbguard/auditd/fapolicyd (51's). The
# old leg ran it and then `exit 0`, which skipped the `systemctl enable` below.
# That is not the same thing: miosd writes the multi-user.target.wants symlink
# directly, while `systemctl enable` reads [Install] and honours whatever else
# it declares. fapolicyd is not installed on the machine this was converted on,
# so that equivalence could not be measured -- and an unmeasured equivalence is
# not one. The enable stays exactly where it was, after either leg.
if [[ -n "$_miosd" ]]; then
    "$_miosd" harden
    mios_ok "Fapolicyd trust configured via miosd"
else
    for config in /usr/lib/fapolicyd/fapolicyd.conf /etc/fapolicyd/fapolicyd.conf; do
        if [[ -f "$config" ]]; then
            sed -i 's/^trust =.*/trust = file,rpmdb/' "$config" || true
        fi
    done
fi

systemctl enable fapolicyd.service
mios_ok "Trust = file,rpmdb set in fapolicyd.conf, fapolicyd.service enabled"
