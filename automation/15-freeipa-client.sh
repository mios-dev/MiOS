#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs FreeIPA and SSSD packages and enables the mios-freeipa-enroll.service; use this script to provision identity management and verify SSSD file capabilities for zero-touch enrollment.
# AI-related: /etc/mios/ipa-enroll.env, mios-freeipa-enroll, mios-freeipa-enroll.service
# 15-freeipa-client.sh -- install FreeIPA/SSSD client + arm zero-touch enrollment.
#
# Runtime path: mios-freeipa-enroll.service runs only when
# /etc/mios/ipa-enroll.env is present and /etc/ipa/default.conf is absent.
#
# Upstream regression notes (April 2026):
#   bz 2320133 -- SSSD file caps stripped by rpm-ostree < bootc - 2.fc41.
#                Asserted post-install; build fails fast if caps are missing.
#   bz 2332433 -- /var/lib/ipa-client/sysrestore/ missing on first boot.
#                Pre-created via tmpfiles.d.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "installing FreeIPA & SSSD for zero-touch enrollment"

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"

# Install client + SSSD tooling.
install_packages "freeipa"

# ── SSSD file capability regression check (bz 2320133) ─────────────────────
mios_log "verifying SSSD file capabilities"
SSSD_CAP_BINS=(
    /usr/libexec/sssd/krb5_child
    /usr/libexec/sssd/ldap_child
    /usr/libexec/sssd/selinux_child
    /usr/lib/sssd/sssd_pam
)
CAP_FAIL=0
for bin in "${SSSD_CAP_BINS[@]}"; do
    [[ -f "$bin" ]] || continue
    caps=$(getcap "$bin" 2>/dev/null || true)
    if [[ -z "$caps" ]]; then
        mios_err "$bin missing file capabilities (bz 2320133 regression)"
        CAP_FAIL=$((CAP_FAIL + 1))
    fi
done
if (( CAP_FAIL > 0 )); then
    mios_warn "${CAP_FAIL} SSSD binary(ies) lost file capabilities -- FreeIPA authentication may require 'setcap' at runtime"
fi

# ── Zero-touch enrollment env from SSOT (AGY-162 / drift-check 92) ──────────
# /etc/mios/ipa-enroll.env is PROJECTED from mios.toml [identity.ipa] by the
# single authoritative generator (tools/generate-ipa-enroll-env.py). Render it
# here rather than hand-maintaining the file so the enrollment config can never
# drift from the SSOT. The generator resolves its own repo root from __file__
# (tools/.. -> the build root, /tmp/build during the OCI build) and writes
# <root>/etc/mios/ipa-enroll.env. 08-system-files-overlay has already tar'd the
# committed tree onto the rootfs before build.sh runs this stage, so also
# install the freshly rendered file directly into the live /etc.
_ipa_root="$(cd "$(dirname "$0")/.." && pwd)"
_ipa_gen="${_ipa_root}/tools/generate-ipa-enroll-env.py"
if command -v python3 >/dev/null 2>&1 && [[ -f "${_ipa_gen}" ]]; then
    mios_log "rendering /etc/mios/ipa-enroll.env from mios.toml [identity.ipa] SSOT"
    python3 "${_ipa_gen}"
    install -D -m 0644 "${_ipa_root}/etc/mios/ipa-enroll.env" /etc/mios/ipa-enroll.env
else
    mios_warn "python3 or generate-ipa-enroll-env.py unavailable -- /etc/mios/ipa-enroll.env not regenerated from SSOT"
fi

# Arm the zero-touch enrollment oneshot (gated by ConditionPathExists).
systemctl enable mios-freeipa-enroll.service
